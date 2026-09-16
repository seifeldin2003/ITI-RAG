import json
import glob

files = glob.glob("data/raw/nhtsa/complaints_*.json")
narratives = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    for r in d.get("results", []):
        narratives.append(r["summary"])

print(f"total complaint records so far: {len(narratives)}")
lengths = [len(s.split()) for s in narratives]
print(f"avg word count: {sum(lengths)/len(lengths):.1f}, median-ish max: {max(lengths)}")
long_ones = [l for l in lengths if l > 190]
print(f"complaints likely to exceed 256 tokens (>190 words): {len(long_ones)}/{len(lengths)} ({100*len(long_ones)/len(lengths):.1f}%)")

# Quick histogram buckets
buckets = {"<50": 0, "50-100": 0, "100-190": 0, "190+": 0}
for l in lengths:
    if l < 50: buckets["<50"] += 1
    elif l < 100: buckets["50-100"] += 1
    elif l < 190: buckets["100-190"] += 1
    else: buckets["190+"] += 1
print(buckets)
