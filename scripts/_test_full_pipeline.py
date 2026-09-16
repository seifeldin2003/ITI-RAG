import os
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import time
import sys
sys.path.insert(0, "scripts")
from _test_synthesis import load_recall_documents, load_complaint_documents, load_mechanicdb_documents

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

print("=== Loading + synthesizing documents ===")
t0 = time.time()
recall_docs = load_recall_documents()
complaint_docs, total_raw = load_complaint_documents()
mdb_docs = load_mechanicdb_documents()
all_docs = recall_docs + complaint_docs + mdb_docs
print(f"{len(all_docs)} documents ({time.time()-t0:.1f}s)")

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=120)
chunks = splitter.split_documents(all_docs)
print(f"{len(chunks)} chunks after splitting")

print("\n=== Loading embedding model ===")
t0 = time.time()
embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
print(f"loaded ({time.time()-t0:.1f}s)")

print("\n=== Embedding + building Chroma vector store (this is the slow part) ===")
t0 = time.time()
persist_dir = "data/vector_store"
vectordb = Chroma.from_documents(
    documents=chunks,
    embedding=embedder,
    collection_name="automotive_diagnostics",
    persist_directory=persist_dir,
)
elapsed = time.time() - t0
print(f"Indexed {vectordb._collection.count()} chunks in {elapsed:.1f}s "
      f"({len(chunks)/elapsed:.1f} chunks/sec)")

print("\n=== Retrieval test: your own BMW X6 example ===")
retriever = vectordb.as_retriever(search_kwargs={"k": 4})
test_questions = [
    "my BMW X6 can't put on drive mode, what's wrong",
    "what does DTC code P0011 mean",
    "Honda Civic engine won't start",
    "how much does it cost to fix a wheel speed sensor",
]
for q in test_questions:
    print(f"\nQ: {q}")
    for d in retriever.invoke(q):
        print(f"   [{d.metadata['source_type']:15s}] {d.metadata.get('record_id','?')}: {d.page_content[:90]}...")

print("\n=== Full RAG chain test (retrieval + Ollama generation) ===")
TEMPLATE = """You are an automotive diagnostic assistant. Answer the question using ONLY the context below, which comes from real NHTSA recall/complaint records and mechanic-authored DTC references.
If the context doesn't contain a relevant answer, say "I don't have information about that in my records."
Cite the source record_id(s) you used.

Context:
{context}

Question: {question}

Answer (with citation):"""
prompt = PromptTemplate.from_template(TEMPLATE)
llm = OllamaLLM(model="llama3.2:3b", temperature=0.1)

def answer(question, k=4):
    docs = vectordb.as_retriever(search_kwargs={"k": k}).invoke(question)
    context = "\n\n".join(f"[{d.metadata.get('record_id','?')}] {d.page_content}" for d in docs)
    chain_input = prompt.format(context=context, question=question)
    t0 = time.time()
    result = llm.invoke(chain_input)
    print(f"  (generated in {time.time()-t0:.1f}s)")
    return result, docs

q = "my BMW X6 can't put on drive mode, what's wrong"
print(f"\nQ: {q}")
ans, docs = answer(q)
print(f"A: {ans}")
print(f"Sources: {[d.metadata.get('record_id') for d in docs]}")

print("\n=== DONE ===")
