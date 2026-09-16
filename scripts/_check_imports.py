import importlib

mods = ["chromadb", "langchain_core", "langchain_text_splitters", "langchain_huggingface",
        "langchain_chroma", "langchain_classic", "langchain_community", "langchain_ollama",
        "streamlit", "fastapi", "pytest"]
for m in mods:
    try:
        mod = importlib.import_module(m)
        print("OK  ", m, getattr(mod, "__version__", "?"))
    except Exception as e:
        print("FAIL", m, type(e).__name__, str(e)[:200])
