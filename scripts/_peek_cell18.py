import json

nb = json.load(open("notebooks/rag_pipeline.ipynb", encoding="utf-8"))
print("cell type:", nb["cells"][18]["cell_type"])
print("".join(nb["cells"][18]["source"])[:200])
