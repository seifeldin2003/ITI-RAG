"""Loads the vector store the notebook persisted (Phase 2.7) and exposes a
retrieval function. Loaded ONCE at app startup (see main.py's lifespan),
never rebuilt per-request -- rebuilding at request time is explicitly what
Phase 2.3/2.7 and the "Common Mistakes" list warn against."""
import os

# Must precede any transformers-touching import -- see the notebook's
# Section 1 setup cell for the full explanation of why (protobuf/chromadb
# vs. tensorflow-intel conflict in this environment).
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import json
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import settings


class RetrievalService:
    """Wraps the persisted Chroma store. One instance, created at startup,
    reused for every request."""

    def __init__(self):
        self.embedder = HuggingFaceEmbeddings(model_name=settings.embedding_model)
        self.vectordb = Chroma(
            collection_name=settings.vector_store_collection,
            embedding_function=self.embedder,
            persist_directory=settings.vector_store_dir,
        )
        count = self.vectordb._collection.count()
        if count == 0:
            raise RuntimeError(
                f"Vector store at '{settings.vector_store_dir}' (collection "
                f"'{settings.vector_store_collection}') is empty. Run the "
                f"notebook (notebooks/rag_pipeline.ipynb) through Section 2.7 "
                f"first -- the backend loads what it persisted, it does not "
                f"build the index itself."
            )
        self.chunk_count = count

        config_path = Path(settings.vector_store_dir) / "config.json"
        self.build_config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}

    def retrieve(self, question: str, k: int | None = None) -> list[Document]:
        k = k or settings.retrieval_k
        
        import re
        match = re.search(r'\b([PBUC]\d{4})\b', question, re.IGNORECASE)
        if match:
            dtc = match.group(1).upper()
            try:
                # In Chroma, exact metadata match is {"component": dtc}
                dtc_docs = self.vectordb.as_retriever(
                    search_kwargs={"k": k, "filter": {"component": dtc}}
                ).invoke(question)
                if dtc_docs and len(dtc_docs) > 0:
                    return dtc_docs
            except Exception:
                pass
            
        return self.vectordb.as_retriever(search_kwargs={"k": k}).invoke(question)
