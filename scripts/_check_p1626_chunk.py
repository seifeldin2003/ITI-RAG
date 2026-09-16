import os
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectordb = Chroma(
    collection_name="automotive_diagnostics",
    embedding_function=embedder,
    persist_directory="data/vector_store",
)

docs = vectordb.as_retriever(search_kwargs={"k": 4}).invoke(
    "what does DTC code P0011 mean and how do I fix it"
)
for d in docs:
    print("record_id:", d.metadata.get("record_id"))
    print("page_content length:", len(d.page_content))
    print("page_content repr:", repr(d.page_content))
    print()

# Also check the RAW mechanicdb row for P1626 directly, and P0011 for comparison
import pandas as pd
joined = pd.read_csv("data/raw/mechanicdb/dtc_fixes_joined.csv", sep="|", encoding="utf-8-sig")
print("--- raw P1626 rows ---")
print(joined[joined["dtc_code"] == "P1626"].to_string())
print("\n--- raw P0011 rows ---")
print(joined[joined["dtc_code"] == "P0011"].to_string())
