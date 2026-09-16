import pandas as pd

joined = pd.read_csv("data/raw/mechanicdb/dtc_fixes_joined.csv", sep="|", encoding="utf-8-sig")
parts = pd.read_csv("data/raw/mechanicdb/replacement_parts.csv", sep="|", encoding="utf-8-sig")
parts_by_fix = parts.groupby("fix_id")["part_name"].apply(list).to_dict()

p1626_rows = joined[joined["dtc_code"] == "P1626"]
print(f"P1626 rows found: {len(p1626_rows)}")

for _, row in p1626_rows.iterrows():
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
    print(f"\n--- fix_id={row['fix_id']} ---")
    print(f"length: {len(text)}")
    print(repr(text[:200]))
