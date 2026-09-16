import pandas as pd

joined = pd.read_csv("data/raw/mechanicdb/dtc_fixes_joined.csv", sep="|", encoding="utf-8-sig")
parts = pd.read_csv("data/raw/mechanicdb/replacement_parts.csv", sep="|", encoding="utf-8-sig")

print("joined shape:", joined.shape)
print("joined columns:", list(joined.columns))
print("joined dtypes:\n", joined.dtypes)
print()
print("parts shape:", parts.shape)
print("parts columns:", list(parts.columns))
print()
print("unique dtc_code count:", joined["dtc_code"].nunique())
print("rows per dtc_code (max fixes for one code):", joined.groupby("dtc_code").size().max())
print()
print("fix_id dtype match? joined:", joined["fix_id"].dtype, "| parts:", parts["fix_id"].dtype)
merged_test = joined.merge(parts, on="fix_id", how="left")
print("merge test shape:", merged_test.shape, "(should be >= joined.shape[0] if some fixes have multiple parts)")
print("fixes with zero matched parts:", merged_test["part_name"].isna().sum())
print()
print("--- one real full example row ---")
row = joined.iloc[0]
for col in joined.columns:
    print(f"{col}: {row[col]!r}")
