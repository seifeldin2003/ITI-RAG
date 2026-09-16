import json

nb = json.load(open("notebooks/rag_pipeline.ipynb", encoding="utf-8"))
c = nb["cells"][17]
for o in c["outputs"]:
    if o.get("output_type") == "execute_result":
        data = o.get("data", {})
        if "text/html" in data:
            html = "".join(data["text/html"])
            print(html[:6000])
