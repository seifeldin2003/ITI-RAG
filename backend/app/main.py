from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.query import router as query_router
from app.core.config import settings
from app.services.generation import GenerationService
from app.services.retrieval import RetrievalService
from app.utils.logging_config import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the vector store + LLM connection ONCE at startup, not per
    # request -- required by Phase 3's own instructions, and the whole
    # point of persisting the vector store in the notebook (2.3/2.7).
    configure_logging()
    app.state.retrieval = RetrievalService()
    app.state.generation = GenerationService()
    yield
    # No explicit teardown needed -- Chroma's client and Ollama's HTTP
    # client don't hold resources that need manual closing here.


app = FastAPI(title="Automotive Diagnostic RAG Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router)
