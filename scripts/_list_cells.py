import json
nb = json.load(open("notebooks/rag_pipeline.ipynb", encoding="utf-8"))
for i, c in enumerate(nb["cells"]):
    first_line = "".join(c["source"]).split("\n")[0][:80]
    print(f"{i:2d} [{c['cell_type']:8s}] {first_line}")
