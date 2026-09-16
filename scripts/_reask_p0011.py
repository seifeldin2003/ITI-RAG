import os
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_ollama import OllamaLLM

embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectordb = Chroma(
    collection_name="automotive_diagnostics",
    embedding_function=embedder,
    persist_directory="data/vector_store",
)
print("chunks in store:", vectordb._collection.count())

TEMPLATE = """You are an automotive diagnostic assistant. Answer the question using ONLY the context below, which comes from real NHTSA recall/complaint records and mechanic-authored DTC references.
If the context doesn't contain a relevant answer, say "I don't have information about that in my records."
Cite the source record_id(s) you used in your answer.

Context:
{context}

Question: {question}

Answer (with citation):"""
prompt = PromptTemplate.from_template(TEMPLATE)
llm = OllamaLLM(model="llama3.2:3b", temperature=0.1)

q = "what does DTC code P0011 mean and how do I fix it"
docs = vectordb.as_retriever(search_kwargs={"k": 4}).invoke(q)
print("Retrieved record_ids:", [d.metadata.get("record_id") for d in docs])
context = "\n\n".join(f"[{d.metadata.get('record_id','?')}] {d.page_content}" for d in docs)
print("\n--- CONTEXT GIVEN TO LLM ---")
print(context[:800])
full_answer = llm.invoke(prompt.format(context=context, question=q))
print("\n--- FULL ANSWER ---")
print(full_answer)
