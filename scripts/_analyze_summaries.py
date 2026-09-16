import json
import glob

files = glob.glob("data/raw/nhtsa/recalls_*.json")
summaries = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    for r in d.get("results", []):
        summaries.append(r["Summary"])

print(f"total recall records so far: {len(summaries)}")

double_space_count = 0
lengths = []
first_sentence_word_counts = []
for s in summaries:
    lengths.append(len(s.split()))
    if "  " in s:
        first, rest = s.split("  ", 1)
        double_space_count += 1
        first_sentence_word_counts.append(len(first.split()))

print(f"records containing a double-space at all: {double_space_count}/{len(summaries)}")
print(f"avg word count of full Summary: {sum(lengths)/len(lengths):.1f}, max: {max(lengths)}")
if first_sentence_word_counts:
    print(f"avg word count BEFORE first double-space: {sum(first_sentence_word_counts)/len(first_sentence_word_counts):.1f}")

long_ones = [l for l in lengths if l > 190]
print(f"Summaries likely to exceed 256 tokens (>190 words): {len(long_ones)}/{len(lengths)} ({100*len(long_ones)/len(lengths):.1f}%)")

# Show 3 concrete examples of the split, so we can eyeball whether it's sane
shown = 0
for s in summaries:
    if "  " in s and len(s.split()) > 60:
        first, rest = s.split("  ", 1)
        print("\n--- EXAMPLE ---")
        print("BEFORE:", repr(first[:150]))
        print("AFTER: ", repr(rest[:150]))
        shown += 1
        if shown >= 3:
            break
