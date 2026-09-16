import json

nb = json.load(open("notebooks/rag_pipeline.ipynb", encoding="utf-8"))
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] != "code":
        continue
    outs = c.get("outputs", [])
    if not outs:
        print(f"=== CELL {i}: NO OUTPUT ===")
        continue
    print(f"=== CELL {i} ===")
    for o in outs:
        t = o.get("output_type")
        if t == "stream":
            print("".join(o["text"])[:3000])
        elif t == "error":
            print("!!! ERROR:", o.get("ename"), o.get("evalue"))
            print("\n".join(o.get("traceback", []))[:2000])
        elif t == "execute_result":
            data = o.get("data", {})
            if "text/plain" in data:
                print("".join(data["text/plain"])[:1500])
