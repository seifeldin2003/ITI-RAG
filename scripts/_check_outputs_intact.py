import json
nb = json.load(open("notebooks/rag_pipeline.ipynb", encoding="utf-8"))
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] == "code":
        has_output = len(c.get("outputs", [])) > 0
        print(i, "has_output:", has_output, "exec_count:", c.get("execution_count"))
