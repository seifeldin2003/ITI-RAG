import json

nb = json.load(open("notebooks/rag_pipeline.ipynb", encoding="utf-8"))
c = nb["cells"][13]
for o in c["outputs"]:
    if o.get("output_type") == "stream":
        print("".join(o["text"]))
