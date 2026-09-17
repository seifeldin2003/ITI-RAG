"""Builds the grounded prompt and calls the local Ollama LLM. Same
TEMPLATE as the notebook's Section 2.4 -- kept identical deliberately, so
the backend's behavior matches what was evaluated in Section 2.6."""
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

from app.core.config import settings

TEMPLATE = """You are AutoDiag, an intelligent automotive diagnostic assistant. Your goal is to provide helpful, actionable, and accurate diagnostic analysis using the provided real NHTSA recall/complaint records and mechanic repair references.

Instructions:
1. Ground your response in the provided records. Analyze reported vehicle issues, affected components, recurring defect patterns, and mechanic repair recommendations.
2. Directly cite the source IDs in your explanation (e.g. [NHTSA Complaint #...], [NHTSA Recall #...], or [MechanicDB ...]).
3. Structure your response clearly:
   - Reported Symptoms & Issues: Summarize what owners and records describe for this vehicle or symptom.
   - Probable Mechanical Causes: Detail component failures or system issues identified in the records.
   - Actionable Next Steps: Provide practical recommendations (e.g. OBD-II scan, checking fluid levels/pressure, inspecting specific wiring or parts).
4. Only state that you lack information if the provided context is completely unrelated to the vehicle or issue.

Context:
{context}

Question: {question}

Diagnostic Analysis & Findings:"""

_prompt = PromptTemplate.from_template(TEMPLATE)


class GenerationService:
    def __init__(self):
        self.llm = OllamaLLM(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.2,
        )

    def generate(self, question: str, docs: list[Document]) -> str:
        if not docs:
            return (
                "I don't have matching records for this specific query in the current database. "
                "Please try specifying the vehicle make, model, model year, or OBD-II DTC code (e.g., P0300)."
            )

        # Format the source IDs to be clear and citeable
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
