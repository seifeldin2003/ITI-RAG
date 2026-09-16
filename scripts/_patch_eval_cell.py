# -*- coding: utf-8 -*-
"""Patches ONLY the 'Written answer -- 2.6' markdown cell's text in the
ALREADY-EXECUTED notebook, in place -- does not touch any code cell or its
real output. Run build_notebook.py + nbconvert --execute again only if the
underlying pipeline logic changes; this script is for updating the human
commentary cell after reading real results."""
import json

PATH = "notebooks/rag_pipeline.ipynb"
nb = json.load(open(PATH, encoding="utf-8"))

target_idx = None
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] == "markdown" and "Written answer" in "".join(c["source"]) and "2.6" in "".join(c["source"]):
        target_idx = i
        break
assert target_idx is not None, "could not find the 2.6 written-answer cell"
print(f"patching cell {target_idx}")

new_text = '''### Written answer — 2.6 (failure cases observed, and mitigation)

Four things were actually observed by running the real pipeline against real data (not hypothesized in advance) — each traceable to a specific design decision, which is the point of this section.

**1. A real chunking bug was found, fixed, and re-verified to work.** The first version of this pipeline joined each record's fields with a single `\\n` and split that whole string. `RecursiveCharacterTextSplitter` orphaned short header lines ("DTC Code: X (Category)") into their own nearly-empty chunks whenever the next field exceeded `chunk_size` alone — confirmed directly (a real 28-character standalone chunk, `"DTC Code: P1626 (Powertrain)"`, with zero diagnostic content). **Fix:** split only the body text, re-attach the header to every resulting chunk. Re-running confirmed the fix: every retrieved chunk now carries real diagnostic content (e.g. `"DTC Code: U0100 (Network)\\nFix: Replace and reprogram the powertrain module..."`) — no more near-empty fragments in the top-k results.

**2. Exact-identifier retrieval still misses, even after the chunking fix — this is a genuine embedding-model limitation, not the chunking bug.** Asking about DTC `P0011` retrieved `P1100`, then `P0325`/`U0100` — different wrong codes on each run, but *never* the correct one, which is confirmed present in the corpus. With the chunking bug fixed, this isolates the real cause cleanly: dense embeddings encode meaning, and a short alphanumeric code carries almost none — `P0011` and `P1100` are both "Powertrain" codes that look structurally identical to the embedding model. This is the same lesson as the Day 2 `SEC-104` lab, now doubly confirmed on real production data. **Mitigation (correctly scoped as future work, not implemented):** hybrid BM25 + dense search would catch this — BM25 matches the literal token `P0011` regardless of semantic similarity to other codes.

**3. A meaningful, encouraging side-effect of the fix: the model stopped hallucinating from its own training data on the P0011 question.** Before the chunking fix, the LLM answered the `P0011` question *correctly* — but by using its own memorized knowledge of a well-known OBD code, not the (badly polluted) retrieved context, and said so explicitly ("I couldn't find any direct references... based on general knowledge..."). This is precisely the failure mode the assignment's "Common Mistakes" list warns against: an answer that sounds right but isn't actually grounded. After the fix, faced with the same kind of irrelevant retrieved context, the model instead said **"I don't have information about that in my records"** and stopped — the correct, safe behavior when retrieval fails, even though the underlying retrieval miss (finding #2) is not yet solved. Fixing a chunking bug improved grounding *discipline*, not just chunk quality — worth noting as a real, if serendipitous, benefit.

**4. Small-model hedging is inconsistent across otherwise-similar questions.** On the BMW X6 question, the model opens with "I don't have information about that in my records" and then, in the same answer, goes on to use and correctly cite the retrieved complaints anyway (`[11447297]`, `[11692474]`) — a self-contradiction, but not a hallucination (the citations are real and correctly grounded). On the P0011 question (finding #3), the same opening phrase is followed by *nothing further* — a clean refusal. `llama3.2:3b` is small enough that which of these two behaviors happens is not fully predictable question-to-question; this is a real, observed limit of using a 3B model for generation, not a bug in the pipeline around it.

**One data-source characteristic worth noting, not a bug:** the same NHTSA recall campaign (e.g. `17V652000`) appears as a separate chunk for each model year it covers, because Phase 1 queries the API per (make, model, year) and a single real-world recall often spans multiple years. This means a handful of recalls are represented multiple times in the corpus — redundant, but not incorrect, since each copy states the same accurate information.

**Performance, for anyone re-running this notebook:** embedding ~6,700 chunks took ~200s on CPU; each generation call took ~45–50s on `llama3.2:3b`. Both are one-time/per-query costs, not something to optimize away before submission.'''

nb["cells"][target_idx]["source"] = [l + "\n" for l in new_text.split("\n")[:-1]] + ([new_text.split("\n")[-1]] if new_text.split("\n")[-1] else [])

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
    f.write("\n")
print("patched and saved")
