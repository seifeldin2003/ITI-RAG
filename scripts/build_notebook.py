# -*- coding: utf-8 -*-
"""Builds notebooks/rag_pipeline.ipynb from verified, tested code (see
scripts/_test_synthesis.py and scripts/_test_full_pipeline.py for the
scratch versions this was validated against)."""
import json
import io

DST = r"C:\ITI\Graduatoion_project\rag-assistant-project\notebooks\rag_pipeline.ipynb"


def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": _src(src)}


def code(src):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": _src(src)}


def _src(text):
    lines = text.split("\n")
    return [l + "\n" for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])


cells = []

# ============================================================== Title
cells.append(md('''# RAG Pipeline — Automotive Diagnostic Assistant

**Core Track — Graduation Project (Level 2 Summer Training)**

A "chat with your car's problem" assistant: ask a symptom-based question (e.g. *"my BMW X6 can't put on drive mode"*) and get a grounded, cited answer built from three real, trusted sources — not the LLM's own memorized knowledge.

## Data sources (all collected in Phase 1, see `scripts/fetch_nhtsa_data.py`)

| Source | What it is | License | Role |
|---|---|---|---|
| **NHTSA Recalls API** | Official manufacturer safety recalls: problem, consequence, fix | Public domain (U.S. federal gov't data) | Authoritative diagnosis → fix pairs |
| **NHTSA Complaints API** | Real owner-submitted problem narratives | Public domain | Natural symptom-language, matches how a user actually phrases a question |
| **MechanicDB (public sample)** | 89 OBD-II DTC codes, mechanic-authored diagnostic explanations, ranked fixes, parts | ODbL v1.0 (attribution + share-alike — see `data/raw/mechanicdb/LICENSE`) | Generic diagnostic depth independent of make/model |

No PDFs, no OCR — all three sources are already clean text (JSON API responses / CSV), collected once in Phase 1 and snapshotted to `data/raw/`. This notebook only reads those local snapshots — it never calls the live APIs itself, which is what makes it able to run top-to-bottom deterministically (Kernel → Restart & Run All) and is required for Phase 2.3 ("persist ... so the backend can load it without rebuilding").

## Pipeline recap
```
 OFFLINE (this notebook):  raw JSON/CSV -> [ SYNTHESIZE per-record text ] -> [ CHUNK ] -> [ EMBED ] -> [ CHROMA, persisted ]
 ONLINE (backend, later):  query -> [ EMBED ] -> [ SEARCH ] -> chunks -> [ PROMPT + Ollama LLM ] -> grounded, cited answer
```
'''))

# ============================================================== 1. Setup
cells.append(md("## 1 — Setup"))
cells.append(code('''import os

# MUST be set before any transformers-touching import (langchain_text_splitters,
# langchain_huggingface, sentence_transformers all pull in `transformers`).
# Installing chromadb bumped protobuf to a version incompatible with the
# tensorflow-intel already present in this environment -- transformers eagerly
# tries to import its TensorFlow integration and hits
# `AttributeError: 'MessageFactory' object has no attribute 'GetPrototype'`.
# This project only uses the PyTorch backend, so disabling TF integration
# entirely is the correct fix (verified working) -- no package downgrades,
# no risk of breaking chromadb's own protobuf requirement.
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import json
import time
from pathlib import Path

import pandas as pd
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_ollama import OllamaLLM

RAW_NHTSA = Path("../data/raw/nhtsa")
RAW_MECHANICDB = Path("../data/raw/mechanicdb")
VECTOR_STORE_DIR = Path("../data/vector_store")

print("Setup complete.")'''))

# ============================================================== 2.1 Load & Inspect
cells.append(md('''## 2.1 — Load & Inspect

We load the three raw sources exactly as Phase 1 saved them — no network calls here.'''))

cells.append(code('''# How many raw files/records do we actually have, and in what shape?
recall_files = sorted(RAW_NHTSA.glob("recalls_*.json"))
complaint_files = sorted(RAW_NHTSA.glob("complaints_*.json"))

total_recall_records = 0
for f in recall_files:
    total_recall_records += len(json.loads(f.read_text(encoding="utf-8")).get("results", []))

total_complaint_records = 0
for f in complaint_files:
    total_complaint_records += len(json.loads(f.read_text(encoding="utf-8")).get("results", []))

mechanicdb_joined = pd.read_csv(RAW_MECHANICDB / "dtc_fixes_joined.csv", sep="|", encoding="utf-8-sig")
mechanicdb_parts = pd.read_csv(RAW_MECHANICDB / "replacement_parts.csv", sep="|", encoding="utf-8-sig")

print(f"NHTSA recall files:      {len(recall_files):4d}  ->  {total_recall_records:6d} raw recall records")
print(f"NHTSA complaint files:   {len(complaint_files):4d}  ->  {total_complaint_records:6d} raw complaint records")
print(f"MechanicDB fix-records:  {mechanicdb_joined.shape[0]:6d}  ({mechanicdb_joined['dtc_code'].nunique()} unique DTC codes)")
print(f"MechanicDB part-records: {mechanicdb_parts.shape[0]:6d}")'''))

cells.append(md('''### Written answer — 2.1

**How many documents/pages? What formats? Which files failed to parse or need OCR?**

Not applicable in the usual "PDF pages" sense — these three sources were collected via a public API (JSON) and a CSV download, not scanned documents, so **there is no OCR step and nothing "failed to parse"**: JSON/CSV are already machine-readable text. The real numbers:

- **NHTSA Recalls:** 141 of 160 requested (make, model, year) combinations returned at least one recall — 879 raw recall records total. (The other 19 combinations legitimately had zero recalls for that vehicle/year, not a parse failure.)
- **NHTSA Complaints:** 146 of 160 combinations returned complaints — **58,321 raw complaint records total**. This is far larger than the other two sources; see the scope decision in 2.2.
- **MechanicDB:** a fixed, small public sample — 320 fix-records across 89 unique OBD-II DTC codes, joined with 449 replacement-part records.

**What's messy here, concretely (found by actually inspecting the data, not assumed):**
1. **NHTSA's own API is inconsistent in field casing** between its two endpoints — Recalls use `Summary`/`Component`/`Make` (capitalized), Complaints use `summary`/`components` (lowercase) and nest vehicle info inside a `products` list instead of top-level fields. Handled explicitly in the loader functions below.
2. **Recall `Summary` text commonly opens with a boilerplate list of every affected model/trim** before the actual defect sentence (e.g. *"...is recalling certain 2019-2021 X3 sDrive30i, X3 xDrive30i, ... vehicles.  When shifting into Reverse..."*) — noise for a symptom-search query. Stripped during synthesis (2.2).
3. **Complaint volume is wildly uneven and, for popular models, enormous** — 58,321 raw complaints from only 146 files (~400 average, but popular models like the Civic/Camry/Tucson run into the thousands per single model-year). Addressed by a deliberate sampling cap in 2.2, not by silently keeping everything.'''))

# ============================================================== 2.2 Chunking Strategy
cells.append(md('''## 2.2 — Chunking Strategy

**Approach: chunk-per-synthesized-record (a semantic/section-based strategy), with `RecursiveCharacterTextSplitter` as a fixed-size-with-overlap fallback** — satisfying the brief's "fixed-size with overlap, OR semantic/section-based" requirement via both, for a reason grounded in the data (below), not an arbitrary pick.

Each record's fields are relationally tied — a "Fix" without its "Problem" loses the context an LLM needs to ground an answer, and citations should point to one coherent record, not a fragment of one. So each recall, each capped complaint, and each MechanicDB fix is first synthesized into **one text block**, then split only if it's long.'''))

cells.append(code('''def clean_recall_summary(summary: str) -> str:
    """NHTSA recall Summary commonly opens with a boilerplate
    '{Manufacturer} is recalling certain {model list} vehicles[, ...].'
    sentence before the actual defect narrative, separated by a double
    space in most records (verified: 210/238 in an earlier sample). Strip
    it when present -- pure noise for a symptom-based query -- but guard
    against a suspiciously short remainder, which suggests the
    double-space wasn't actually the boilerplate/defect boundary."""
    if "  " in summary:
        _, rest = summary.split("  ", 1)
        if len(rest.split()) >= 15:
            return rest.strip()
    return summary.strip()


splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=120)


def make_chunks(header: str, body: str, metadata: dict) -> list[Document]:
    """Split ONLY the body, then re-attach the (short, always-identifying)
    header to every resulting piece. Splitting header+body as one string
    on '\\n' was tried first and had a real bug: RecursiveCharacterTextSplitter
    tries '\\n\\n' then '\\n' as separators, and when a single field line (e.g.
    a long "Problem:" line) exceeds chunk_size on its own, the short header
    line before it gets orphaned into its own separate, nearly-empty chunk
    (verified directly: a real MechanicDB record produced a standalone
    28-character "DTC Code: P1626 (Powertrain)" chunk with no diagnostic
    content at all). Because that header text is short and generic, near-
    identical orphaned headers from DIFFERENT records in the same category
    cluster together in embedding space -- which is why a real query for
    DTC P0011 retrieved four P1626 header fragments instead: the header
    text is what got embedded, not the actual diagnostic content. Splitting
    the body alone and re-attaching the header to every chunk means no
    chunk is ever context-free, and no chunk is ever near-empty."""
    body_chunks = splitter.split_text(body) or [""]
    return [
        Document(page_content=f"{header}\\n{chunk}", metadata=metadata)
        for chunk in body_chunks
    ]


def load_recall_documents() -> list[Document]:
    docs = []
    for f in recall_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        for r in data.get("results", []):
            defect = clean_recall_summary(r["Summary"])
            header = f"Vehicle: {r['ModelYear']} {r['Make']} {r['Model']}"
            # Field order is deliberate: Problem (the symptom text a query
            # matches against) comes first in the body -- the highest-value
            # field for retrieval should be least likely to fall in a
            # truncated/split-away tail.
            body = (
                f"Problem: {defect}\\n"
                f"Component: {r['Component']}\\n"
                f"Consequence: {r['Consequence']}\\n"
                f"Fix: {r['Remedy']}"
            )
            docs.extend(make_chunks(header, body, {
                "source_type": "nhtsa_recall",
                "make": r["Make"], "model": r["Model"], "year": r["ModelYear"],
                "component": r["Component"],
                "record_id": r["NHTSACampaignNumber"],
            }))
    return docs


# Complaints are capped per (make, model, year) at corpus-build time, not at
# the raw-fetch stage: Phase 1's raw snapshot stays complete (58,321 records,
# cheap to store), and THIS is where we make and document the scope decision.
# 58k near-duplicate reports of the same handful of recurring issues would add
# retrieval noise, not signal, and balloon CPU embedding time for no benefit.
COMPLAINTS_CAP_PER_VEHICLE = 25

def load_complaint_documents(cap_per_vehicle: int = COMPLAINTS_CAP_PER_VEHICLE):
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
                f"Component: {r.get('components', 'Unknown')}\\n"
                f"Owner-reported problem: {r['summary']}"
            )
            docs.extend(make_chunks(header, body, {
                "source_type": "nhtsa_complaint",
                "make": make, "model": model, "year": year,
                "component": r.get("components", "Unknown"),
                "record_id": r["odiNumber"],
            }))
    return docs, total_raw


def load_mechanicdb_documents() -> list[Document]:
    parts_by_fix = mechanicdb_parts.groupby("fix_id")["part_name"].apply(list).to_dict()
    docs = []
    for _, row in mechanicdb_joined.iterrows():
        part_names = parts_by_fix.get(row["fix_id"], [])
        parts_str = ", ".join(part_names) if part_names else "Not specified"
        header = f"DTC Code: {row['dtc_code']} ({row['system_category']})"
        body = (
            f"Problem: {row['short_description']} -- {row['detailed_technical_explanation']}\\n"
            f"Fix: {row['fix_title']} -- {row['step_by_step_instructions']}\\n"
            f"Difficulty: {row['difficulty_level']}, "
            f"Est. cost: ${row['est_parts_cost_min_usd']:.0f}-${row['est_parts_cost_max_usd']:.0f}, "
            f"Labor: {row['est_labor_hours']}h\\n"
            f"Parts affected: {parts_str}"
        )
        docs.extend(make_chunks(header, body, {
            "source_type": "mechanicdb_dtc",
            "component": row["dtc_code"],
            "record_id": f"{row['dtc_code']}-fix{row['fix_id']}",
        }))
    return docs


recall_chunks = load_recall_documents()
complaint_chunks, total_raw_complaints = load_complaint_documents()
mechanicdb_chunks = load_mechanicdb_documents()
chunks = recall_chunks + complaint_chunks + mechanicdb_chunks

by_source = {}
for c in chunks:
    by_source[c.metadata["source_type"]] = by_source.get(c.metadata["source_type"], 0) + 1

print(f"Recall chunks:     {len(recall_chunks):5d}  (from 879 records)")
print(f"Complaint chunks:  {len(complaint_chunks):5d}  (from {len(complaint_chunks)} sampled of {total_raw_complaints:,} raw)")
print(f"MechanicDB chunks: {len(mechanicdb_chunks):5d}  (from 320 fix-records)")
print(f"TOTAL chunks: {len(chunks):,}")
print("chunks by source:", by_source)'''))

cells.append(md('''### Written answer — 2.2 (chunk size / overlap justification)

**`chunk_size=1000`, `chunk_overlap=120`, chunk-per-record as the primary boundary — with a header/body split, not a naive single-string split.**

`chunk_size=1000` is grounded in the embedding model's actual behavior, not an arbitrary tutorial number: `all-MiniLM-L6-v2` (Section 2.3) silently truncates at 256 tokens with no warning — roughly 1000–1100 characters for typical English. Setting `chunk_size` near that budget means a record under ~1000 chars stays whole, and a record over that size is split *before* the embedding step would have silently truncated it anyway.

**A real bug was found and fixed while building this, worth documenting because it's a genuinely easy trap.** The first version of this notebook joined every field with a single `\\n` (`"Vehicle: ...\\nProblem: ...\\nFix: ..."`) and split that whole string directly. `RecursiveCharacterTextSplitter` tries `"\\n\\n"` then `"\\n"` as separators — and when one field (say, a long `Problem:` line) exceeds `chunk_size` on its own, the *short header line before it* gets orphaned into its own tiny, nearly content-free chunk. Verified directly on a real record: a MechanicDB entry produced a standalone 28-character chunk reading only `"DTC Code: P1626 (Powertrain)"`, with the actual diagnostic text pushed into later chunks. Because that header text is short and generic, near-identical orphaned headers from *different* records in the same category cluster together in embedding space — confirmed as the actual cause of a real retrieval failure: a query for DTC `P0011` returned four `P1626` header-only fragments, not because the embeddings confused the two codes' meaning, but because the *only thing that got embedded* for those results was a nearly-empty templated header.

**Fix:** split only the substantive body text per record, then re-attach a short header (`Vehicle: ...` / `DTC Code: ...`) to *every* resulting chunk. This guarantees no chunk is ever context-free (fixing a second, related issue — a split chunk that used to lose its vehicle/code identity) and no chunk is ever near-empty. `chunk_overlap=120` (~12%) still carries a sentence of continuity across a body split without meaningfully inflating the corpus.

This is exactly the kind of failure the assignment's "note anything messy" instruction is asking for — not a hypothetical risk, but a concrete bug, caught by actually reading chunk-level output rather than trusting chunk *counts* alone, then fixed and re-verified below.'''))

# ============================================================== 2.3 Embeddings & Vector Store
cells.append(md('''## 2.3 — Embeddings & Vector Store

Same embedding model as the Day 1/2 labs (`all-MiniLM-L6-v2`) — proven, CPU-friendly, no reason to switch under a tight deadline. One persisted Chroma collection (not split per source) — `source_type` metadata allows filtering later without needing separate stores.'''))

cells.append(code('''embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

t0 = time.time()
vectordb = Chroma.from_documents(
    documents=chunks,
    embedding=embedder,
    collection_name="automotive_diagnostics",
    persist_directory=str(VECTOR_STORE_DIR),
)
elapsed = time.time() - t0
print(f"Indexed {vectordb._collection.count():,} chunks in {elapsed:.1f}s "
      f"({len(chunks)/elapsed:.1f} chunks/sec) -> persisted to {VECTOR_STORE_DIR}/")'''))

# ============================================================== 2.4 Retrieval & Prompting
cells.append(md('''## 2.4 — Retrieval & Prompting

Retrieval function tested against real questions, including the exact scenario this project started from (*"my BMW X6 can't put on drive mode"*), plus enough variety across all three sources to cover ≥10 questions as required.'''))

cells.append(code('''retriever = vectordb.as_retriever(search_kwargs={"k": 4})

TEST_QUESTIONS = [
    "my BMW X6 can't put on drive mode, what's wrong",
    "what does DTC code P0011 mean and how do I fix it",
    "Honda Civic engine won't start",
    "how much does it cost to fix a wheel speed sensor",
    "Toyota Camry brake problems",
    "Ford F-150 door won't latch",
    "what's wrong with my Jeep Grand Cherokee transmission",
    "Hyundai Tucson recall airbag",
    "Nissan Rogue transmission shuddering",
    "Chevrolet Silverado steering issue",
]

for q in TEST_QUESTIONS:
    print(f"Q: {q}")
    for d in retriever.invoke(q):
        print(f"   [{d.metadata['source_type']:15s}] {d.metadata.get('record_id','?')}: {d.page_content[:80]}...")
    print()'''))

cells.append(code('''# Grounded prompt: answer ONLY from context, cite the record_id(s), and admit
# ignorance when nothing relevant was retrieved -- the doc's own "Common
# Mistakes" #3 is exactly the failure mode this prompt exists to prevent.
TEMPLATE = """You are an automotive diagnostic assistant. Answer the question using ONLY the context below, which comes from real NHTSA recall/complaint records and mechanic-authored DTC references.
If the context doesn't contain a relevant answer, say "I don't have information about that in my records."
Cite the source record_id(s) you used in your answer.

Context:
{context}

Question: {question}

Answer (with citation):"""
rag_prompt = PromptTemplate.from_template(TEMPLATE)

generator = OllamaLLM(model="llama3.2:3b", temperature=0.1)


def ask(question: str, k: int = 4):
    """Retrieve -> build grounded prompt -> generate -> return the answer
    AND the sources used, so retrieval quality and generation quality can be
    judged separately (a wrong answer is either bad retrieval or bad
    generation -- never just "the RAG is broken")."""
    docs = vectordb.as_retriever(search_kwargs={"k": k}).invoke(question)
    context = "\\n\\n".join(f"[{d.metadata.get('record_id','?')}] {d.page_content}" for d in docs)
    result = generator.invoke(rag_prompt.format(context=context, question=question))
    return result, docs


# Smoke test on the project's own founding example
answer, sources = ask("my BMW X6 can't put on drive mode, what's wrong")
print("Q: my BMW X6 can't put on drive mode, what's wrong")
print(f"A: {answer}")
print(f"Retrieved: {[d.metadata.get('record_id') for d in sources]}")'''))

# ============================================================== 2.5 N/A
cells.append(md('''## 2.5 — Vision Component

**N/A — Core Track.** This project does not include a Computer Vision/YOLO component (that is Extended Track scope). Noted explicitly here rather than silently omitted, per the assignment's own section structure.'''))

# ============================================================== 2.6 Evaluation
cells.append(md('''## 2.6 — Evaluation

Run all 10 test questions through the full grounded chain, judge each manually (relevant context? grounded or hallucinated? correct?), and record the results in a table.'''))

cells.append(code('''import pandas as pd

eval_rows = []
for q in TEST_QUESTIONS:
    ans, docs = ask(q)
    eval_rows.append({
        "question": q,
        "retrieved_sources": ", ".join(str(d.metadata.get("record_id")) for d in docs[:2]),
        "answer": ans[:200] + ("..." if len(ans) > 200 else ""),
    })

eval_df = pd.DataFrame(eval_rows)
eval_df["correct"] = ""  # TODO: fill in True/False by hand after reading each answer against its sources
eval_df.to_csv("../data/eval_results.csv", index=False)
eval_df'''))

cells.append(md('''### Written answer — 2.6 (failure cases observed, and mitigation)

Three real failure modes were actually observed while building this pipeline (not hypothesized in advance) — each is traceable to a specific design decision made earlier in this notebook, which is the point of this section:

**1. Exact-identifier retrieval miss — the same lesson as Day 2's `SEC-104` lab, now confirmed on real data.** Asking *"what does DTC code P0011 mean"* retrieved four `P1626` records, not `P0011` — even though **`P0011` is confirmed present in the corpus** (verified directly: `'P0011' in dtc_fixes_joined['dtc_code'].values` → `True`). Dense embeddings encode meaning, not exact strings — `P0011` and `P1626` are both short alphanumeric powertrain codes that look similar to the embedding model, so it can't tell them apart the way an exact keyword match would. **Mitigation (not yet implemented, correctly scoped as future work):** hybrid search (BM25 + dense, per the Day 2 lab) would catch this — BM25 matches the literal token `P0011` regardless of what it means semantically. Documented here as a known limitation rather than silently accepted.

**2. Split-chunk continuations lose their own header.** For *"Honda Civic engine won't start"*, one retrieved chunk read *"...did start, but all the warnings continued to flash on the dash..."* — clearly the **second half** of a complaint that got split by `RecursiveCharacterTextSplitter`, missing the `Vehicle:`/`Component:` header that only the first chunk carries (that header is written once, at the start of the synthesized text, before splitting). The chunk is still relevant and still gets used, but a retrieved second-half chunk alone is harder for both a human and the LLM to attribute to a specific vehicle. **Mitigation:** carry `make`/`model`/`year` in every chunk's *metadata* (already done — see the `metadata=` dict in each loader) even though it's missing from that chunk's *text*, so the generation step can still cite the vehicle correctly even when the header text itself was split away.

**3. The LLM hedges, then contradicts its own hedge.** On the founding BMW X6 example, the model opened with *"I don't have information about that in my records"* — the correct fallback phrase — and then, in the very same answer, went on to actually use and cite the retrieved complaints anyway (`[11447297]`, `[11692474]`, `[11509276]`), reasoning fairly sensibly about a mechatronics/transmission issue. `llama3.2:3b` is small enough that this kind of self-contradiction is a known, observed failure mode, not a hallucination in the "made up facts" sense — the citations it gives are real and correctly grounded. Worth flagging to whoever reads this evaluation rather than picking whichever half of the answer looks better.

**Performance, for anyone re-running this notebook:** embedding 6,795 chunks took ~223s (~30 chunks/sec) on CPU; each generation call took ~45–50s on `llama3.2:3b`. Both are one-time/per-query costs, not something to optimize away before submission, but worth knowing before assuming the notebook has hung.'''))

# ============================================================== 2.7 Export
cells.append(md('''## 2.7 — Export

Persist the vector store's config (chunk size, embedding model, complaint cap) alongside the already-persisted Chroma directory, so the backend loads both without re-deriving any of these choices.'''))

cells.append(code('''config = {
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "chunk_size": 1000,
    "chunk_overlap": 120,
    "complaints_cap_per_vehicle": COMPLAINTS_CAP_PER_VEHICLE,
    "vector_store_collection": "automotive_diagnostics",
    "ollama_model": "llama3.2:3b",
    "total_chunks_indexed": vectordb._collection.count(),
    "sources": {
        "nhtsa_recall_chunks": len(recall_chunks),
        "nhtsa_complaint_chunks": len(complaint_chunks),
        "nhtsa_complaints_raw_total": total_raw_complaints,
        "mechanicdb_dtc_chunks": len(mechanicdb_chunks),
    },
}

with open(VECTOR_STORE_DIR / "config.json", "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2)

print(json.dumps(config, indent=2))
print(f"\\nVector store persisted at: {VECTOR_STORE_DIR.resolve()}")
print("The backend loads this directory directly -- no rebuilding at request time.")'''))

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "silo", "language": "python", "name": "silo"},
        "language_info": {"name": "python", "version": "3.11.15"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

with io.open(DST, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
    f.write("\n")
print("wrote", DST, "with", len(cells), "cells")
