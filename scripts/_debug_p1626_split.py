import os
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"

import pandas as pd
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

joined = pd.read_csv("data/raw/mechanicdb/dtc_fixes_joined.csv", sep="|", encoding="utf-8-sig")
parts = pd.read_csv("data/raw/mechanicdb/replacement_parts.csv", sep="|", encoding="utf-8-sig")
parts_by_fix = parts.groupby("fix_id")["part_name"].apply(list).to_dict()

row = joined[joined["dtc_code"] == "P1626"].iloc[0]
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
print("original doc length:", len(text))

doc = Document(page_content=text, metadata={"record_id": f"{row['dtc_code']}-fix{row['fix_id']}"})
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=120)
chunks = splitter.split_documents([doc])
print(f"number of chunks: {len(chunks)}")
for i, c in enumerate(chunks):
    print(f"\n--- chunk {i}, length={len(c.page_content)} ---")
    print(repr(c.page_content))

print("\n\n=== DOES THE TAIL SURVIVE ANYWHERE? ===")
tail = text[-120:]
print("original tail:", repr(tail))
found_in_any_chunk = any(tail in c.page_content for c in chunks)
print("tail found verbatim in any chunk:", found_in_any_chunk)

combined = "".join(c.page_content for c in chunks)
print("\n'Difficulty:' appears in any chunk:", any("Difficulty:" in c.page_content for c in chunks))
print("'Parts affected:' appears in any chunk:", any("Parts affected:" in c.page_content for c in chunks))
