import os
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import json
from pathlib import Path

import pandas as pd
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

RAW_NHTSA = Path("data/raw/nhtsa")
RAW_MECHANICDB = Path("data/raw/mechanicdb")
COMPLAINTS_CAP_PER_VEHICLE = 25


def clean_recall_summary(summary: str) -> str:
    """NHTSA recall Summary commonly opens with a boilerplate
    '{Manufacturer} is recalling certain {model list} vehicles[, ...].'
    sentence before the actual defect narrative, separated by a double
    space in most records (verified: 210/238 in a real sample). Strip it
    when present -- pure noise for a symptom-based query -- but guard
    against an unusually short remainder, which suggests the double-space
    wasn't actually the boilerplate/defect boundary."""
    if "  " in summary:
        _, rest = summary.split("  ", 1)
        if len(rest.split()) >= 15:
            return rest.strip()
    return summary.strip()


def load_recall_documents() -> list[Document]:
    docs = []
    for f in RAW_NHTSA.glob("recalls_*.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        for r in data.get("results", []):
            defect = clean_recall_summary(r["Summary"])
            text = (
                f"Vehicle: {r['ModelYear']} {r['Make']} {r['Model']}\n"
                f"Problem: {defect}\n"
                f"Component: {r['Component']}\n"
                f"Consequence: {r['Consequence']}\n"
                f"Fix: {r['Remedy']}"
            )
            docs.append(Document(page_content=text, metadata={
                "source_type": "nhtsa_recall",
                "make": r["Make"], "model": r["Model"], "year": r["ModelYear"],
                "component": r["Component"],
                "record_id": r["NHTSACampaignNumber"],
            }))
    return docs


def load_complaint_documents(cap_per_vehicle: int = COMPLAINTS_CAP_PER_VEHICLE) -> list[Document]:
    docs = []
    total_raw = 0
    for f in RAW_NHTSA.glob("complaints_*.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        results = data.get("results", [])
        total_raw += len(results)
        for r in results[:cap_per_vehicle]:
            products = r.get("products") or [{}]
            p = products[0]
            make = p.get("productMake", "UNKNOWN")
            model = p.get("productModel", "UNKNOWN")
            year = p.get("productYear", "UNKNOWN")
            text = (
                f"Vehicle: {year} {make} {model}\n"
                f"Component: {r.get('components', 'Unknown')}\n"
                f"Owner-reported problem: {r['summary']}"
            )
            docs.append(Document(page_content=text, metadata={
                "source_type": "nhtsa_complaint",
                "make": make, "model": model, "year": year,
                "component": r.get("components", "Unknown"),
                "record_id": r["odiNumber"],
            }))
    return docs, total_raw


def load_mechanicdb_documents() -> list[Document]:
    joined = pd.read_csv(RAW_MECHANICDB / "dtc_fixes_joined.csv", sep="|", encoding="utf-8-sig")
    parts = pd.read_csv(RAW_MECHANICDB / "replacement_parts.csv", sep="|", encoding="utf-8-sig")
    parts_by_fix = parts.groupby("fix_id")["part_name"].apply(list).to_dict()

    docs = []
    for _, row in joined.iterrows():
        part_names = parts_by_fix.get(row["fix_id"], [])
        parts_str = ", ".join(part_names) if part_names else "Not specified"
        text = (
            f"DTC Code: {row['dtc_code']} ({row['system_category']})\n"
            f"Problem: {row['short_description']} -- {row['detailed_technical_explanation']}\n"
            f"Fix: {row['fix_title']} -- {row['step_by_step_instructions']}\n"
            f"Difficulty: {row['difficulty_level']}, "
            f"Est. cost: ${row['est_parts_cost_min_usd']:.0f}-${row['est_parts_cost_max_usd']:.0f}, "
            f"Labor: {row['est_labor_hours']}h\n"
            f"Parts affected: {parts_str}"
        )
        docs.append(Document(page_content=text, metadata={
            "source_type": "mechanicdb_dtc",
            "component": row["dtc_code"],
            "record_id": f"{row['dtc_code']}-fix{row['fix_id']}",
        }))
    return docs


if __name__ == "__main__":
    recall_docs = load_recall_documents()
    complaint_docs, total_raw_complaints = load_complaint_documents()
    mdb_docs = load_mechanicdb_documents()

    print(f"Recall documents:    {len(recall_docs)}")
    print(f"Complaint documents: {len(complaint_docs)} (sampled from {total_raw_complaints} raw)")
    print(f"MechanicDB documents:{len(mdb_docs)}")
    print(f"TOTAL pre-chunk documents: {len(recall_docs) + len(complaint_docs) + len(mdb_docs)}")

    all_docs = recall_docs + complaint_docs + mdb_docs

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=120)
    chunks = splitter.split_documents(all_docs)
    print(f"TOTAL chunks after splitting: {len(chunks)}")
    print(f"  (chunks == documents means most records fit in one chunk, as expected for recalls/mechanicdb)")

    by_source = {}
    for c in chunks:
        by_source[c.metadata["source_type"]] = by_source.get(c.metadata["source_type"], 0) + 1
    print("chunks by source_type:", by_source)

    # Sanity: print one real example of each type
    print("\n--- sample recall doc ---")
    print(recall_docs[0].page_content)
    print(recall_docs[0].metadata)
    print("\n--- sample complaint doc ---")
    print(complaint_docs[0].page_content[:300])
    print(complaint_docs[0].metadata)
    print("\n--- sample mechanicdb doc ---")
    print(mdb_docs[0].page_content)
    print(mdb_docs[0].metadata)

    # Check for any suspiciously empty/short page_content (data quality check)
    empties = [d for d in all_docs if len(d.page_content.strip()) < 20]
    print(f"\nsuspiciously short/empty documents: {len(empties)}")

    # --- how big are the FULL synthesized records, in characters? ---
    import statistics
    for label, doc_list in [("recall", recall_docs), ("complaint", complaint_docs), ("mechanicdb", mdb_docs)]:
        lens = [len(d.page_content) for d in doc_list]
        lens.sort()
        p50 = lens[len(lens)//2]
        p90 = lens[int(len(lens)*0.9)]
        print(f"{label:12s} char-length  avg={sum(lens)/len(lens):.0f}  p50={p50}  p90={p90}  max={max(lens)}")
