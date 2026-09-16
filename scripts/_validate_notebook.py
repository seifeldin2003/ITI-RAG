import json
import ast

nb = json.load(open("notebooks/rag_pipeline.ipynb", encoding="utf-8"))
print("cells:", len(nb["cells"]), "| code:", sum(c["cell_type"] == "code" for c in nb["cells"]))
for i, c in enumerate(nb["cells"]):
    need = {"cell_type", "metadata", "source"} | ({"outputs", "execution_count"} if c["cell_type"] == "code" else set())
    missing = need - set(c)
    if missing:
        print(f"STRUCTURE PROBLEM cell {i}: missing {missing}")
    if c["cell_type"] == "code":
        src = "".join(c["source"])
        try:
            ast.parse(src)
        except SyntaxError as e:
            print(f"SYNTAX ERROR in cell {i}:", e)
print("validation done")
