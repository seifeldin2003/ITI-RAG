# -*- coding: utf-8 -*-
"""
Builds and persists the Chroma vector store from data/raw/
(Equivalent to Sections 2.1-2.3 and 2.7 of notebooks/rag_pipeline.ipynb).
"""
import os
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import json
import time
import shutil
from pathlib import Path

import pandas as pd
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_NHTSA = ROOT_DIR / "data" / "raw" / "nhtsa"
RAW_MECHANICDB = ROOT_DIR / "data" / "raw" / "mechanicdb"
VECTOR_STORE_DIR = ROOT_DIR / "data" / "vector_store"
BACKEND_VECTOR_STORE = ROOT_DIR / "backend" / "data" / "vector_store"

def clean_recall_summary(summary: str) -> str:
    if "  " in summary:
        _, rest = summary.split("  ", 1)
        if len(rest.split()) >= 15:
            return rest.strip()
    return summary.strip()

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=120)

def make_chunks(header: str, body: str, metadata: dict) -> list[Document]:
    body_chunks = splitter.split_text(body) or [""]
    return [
        Document(page_content=f"{header}\n{chunk}", metadata=metadata)
        for chunk in body_chunks
    ]

def load_recall_documents() -> list[Document]:
    recall_files = sorted(RAW_NHTSA.glob("recalls_*.json"))
    docs = []
    for f in recall_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        for r in data.get("results", []):
            defect = clean_recall_summary(r.get("Summary", ""))
            header = f"Vehicle: {r.get('ModelYear', '')} {r.get('Make', '')} {r.get('Model', '')}"
            body = (
                f"Problem: {defect}\n"
                f"Component: {r.get('Component', '')}\n"
                f"Consequence: {r.get('Consequence', '')}\n"
                f"Fix: {r.get('Remedy', '')}"
            )
            docs.extend(make_chunks(header, body, {
                "source_type": "nhtsa_recall",
                "make": r.get("Make", ""), "model": r.get("Model", ""), "year": r.get("ModelYear", ""),
                "component": r.get("Component", ""),
                "record_id": r.get("NHTSACampaignNumber", ""),
            }))
    return docs

COMPLAINTS_CAP_PER_VEHICLE = 25

def load_complaint_documents(cap_per_vehicle: int = COMPLAINTS_CAP_PER_VEHICLE):
    complaint_files = sorted(RAW_NHTSA.glob("complaints_*.json"))
    docs = []
    total_raw = 0
    for f in complaint_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        results = data.get("results", [])
        total_raw += len(results)
        for r in results[:cap_per_vehicle]:
            products = r.get("products") or [{}]
            p = products[0]
            make = p.get("productMake", "UNKNOWN")
            model = p.get("productModel", "UNKNOWN")
            year = p.get("productYear", "UNKNOWN")
            header = f"Vehicle: {year} {make} {model}"
            body = (
                f"Component: {r.get('components', 'Unknown')}\n"
                f"Owner-reported problem: {r.get('summary', '')}"
            )
            docs.extend(make_chunks(header, body, {
                "source_type": "nhtsa_complaint",
                "make": make, "model": model, "year": year,
                "component": r.get("components", "Unknown"),
                "record_id": r.get("odiNumber", ""),
            }))
    return docs, total_raw

def load_mechanicdb_documents() -> list[Document]:
    mechanicdb_joined = pd.read_csv(RAW_MECHANICDB / "dtc_fixes_joined.csv", sep="|", encoding="utf-8-sig")
    mechanicdb_parts = pd.read_csv(RAW_MECHANICDB / "replacement_parts.csv", sep="|", encoding="utf-8-sig")
    parts_by_fix = mechanicdb_parts.groupby("fix_id")["part_name"].apply(list).to_dict()
    docs = []
    for _, row in mechanicdb_joined.iterrows():
        part_names = parts_by_fix.get(row["fix_id"], [])
        parts_str = ", ".join(part_names) if part_names else "Not specified"
        header = f"DTC Code: {row['dtc_code']} ({row['system_category']})"
        body = (
            f"Problem: {row['short_description']} -- {row['detailed_technical_explanation']}\n"
            f"Fix: {row['fix_title']} -- {row['step_by_step_instructions']}\n"
            f"Difficulty: {row['difficulty_level']}, "
            f"Est. cost: ${row['est_parts_cost_min_usd']:.0f}-${row['est_parts_cost_max_usd']:.0f}, "
            f"Labor: {row['est_labor_hours']}h\n"
            f"Parts affected: {parts_str}"
        )
        docs.extend(make_chunks(header, body, {
            "source_type": "mechanicdb_dtc",
            "component": str(row["dtc_code"]),
            "record_id": f"{row['dtc_code']}-fix{row['fix_id']}",
        }))
    return docs

def main():
    print("=== Loading documents ===")
    t0 = time.time()
    recall_chunks = load_recall_documents()
    complaint_chunks, total_raw = load_complaint_documents()
    mechanicdb_chunks = load_mechanicdb_documents()
    chunks = recall_chunks + complaint_chunks + mechanicdb_chunks
    print(f"Loaded {len(chunks):,} chunks in {time.time()-t0:.1f}s")
    print(f"  Recalls: {len(recall_chunks)}")
    print(f"  Complaints: {len(complaint_chunks)} (from {total_raw:,} raw)")
    print(f"  MechanicDB: {len(mechanicdb_chunks)}")

    print("\n=== Initializing Embeddings model ===")
    embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    if VECTOR_STORE_DIR.exists():
        print(f"Removing old vector store at {VECTOR_STORE_DIR}")
        shutil.rmtree(VECTOR_STORE_DIR)

    print("\n=== Building Chroma Vector Store ===")
    t0 = time.time()
    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embedder,
        collection_name="automotive_diagnostics",
        persist_directory=str(VECTOR_STORE_DIR),
    )
    elapsed = time.time() - t0
    count = vectordb._collection.count()
    print(f"Indexed {count:,} chunks in {elapsed:.1f}s ({count/elapsed:.1f} chunks/sec)")

    config = {
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "chunk_size": 1000,
        "chunk_overlap": 120,
        "complaints_cap_per_vehicle": COMPLAINTS_CAP_PER_VEHICLE,
        "vector_store_collection": "automotive_diagnostics",
        "ollama_model": "llama3.2:3b",
        "total_chunks_indexed": count,
        "sources": {
            "nhtsa_recall_chunks": len(recall_chunks),
            "nhtsa_complaint_chunks": len(complaint_chunks),
            "nhtsa_complaints_raw_total": total_raw,
            "mechanicdb_dtc_chunks": len(mechanicdb_chunks),
        },
    }
    (VECTOR_STORE_DIR / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"Saved config.json to {VECTOR_STORE_DIR / 'config.json'}")

    # Copy to backend/data/vector_store
    print("\n=== Copying to backend/data/vector_store ===")
    if BACKEND_VECTOR_STORE.exists():
        shutil.rmtree(BACKEND_VECTOR_STORE)
    BACKEND_VECTOR_STORE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(VECTOR_STORE_DIR, BACKEND_VECTOR_STORE)
    print(f"Successfully copied to {BACKEND_VECTOR_STORE}")
    print("\n=== Vector store build complete! ===")

if __name__ == "__main__":
    main()
