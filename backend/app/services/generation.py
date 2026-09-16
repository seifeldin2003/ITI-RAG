"""Builds the grounded prompt and calls the local Ollama LLM. Same
TEMPLATE as the notebook's Section 2.4 -- kept identical deliberately, so
the backend's behavior matches what was evaluated in Section 2.6."""
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

from app.core.config import settings

TEMPLATE = """You are an automotive diagnostic assistant. Answer the question using ONLY the context below, which comes from real NHTSA recall/complaint records and mechanic-authored DTC references.
Do NOT use outside knowledge. Do NOT guess or suggest causes that are not explicitly in the context. If the context does not contain the answer or any related helpful information, say exactly: "I don't have information about that in my records."
Always cite the source ID(s) you used in your answer.

Context:
{context}

Question: {question}

Answer (with citation):"""

_prompt = PromptTemplate.from_template(TEMPLATE)


class GenerationService:
    def __init__(self):
        self.llm = OllamaLLM(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.1,
        )

    def generate(self, question: str, docs: list[Document]) -> str:
        # Format the source IDs to be more understandable to the user
        formatted_docs = []
        for d in docs:
            rec_id = str(d.metadata.get('record_id', '?'))
            if rec_id.isdigit():
                source_name = f"NHTSA Complaint #{rec_id}"
            elif rec_id.endswith("000"):
                source_name = f"NHTSA Recall #{rec_id}"
            else:
                source_name = f"MechanicDB {rec_id}"
            
            formatted_docs.append(f"[{source_name}] {d.page_content}")

        context = "\n\n".join(formatted_docs)
        return self.llm.invoke(_prompt.format(context=context, question=question))
