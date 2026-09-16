import os
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vdb = Chroma(collection_name="automotive_diagnostics", embedding_function=embedder, persist_directory="data/vector_store")

res = vdb.get(where={"record_id": 11743329})
print("chunks with record_id=11743329:", len(res["ids"]))
for doc in res["documents"]:
    print(repr(doc[:200]))
    print()

# Now the "no memory" follow-up test: issue the highway question ALONE,
# exactly as the backend would see it with zero prior context.
print("\n=== Isolated retrieval test: the 'highway heat ampere' follow-up, alone ===")
docs = vdb.as_retriever(search_kwargs={"k": 4}).invoke(
    "but i'm now on the highway and the heat ampear is across over the baseline what should I do"
)
for d in docs:
    print(f"[{d.metadata['source_type']}] {d.metadata.get('record_id')}: {d.page_content[:100]}")
