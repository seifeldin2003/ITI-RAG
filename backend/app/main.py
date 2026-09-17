import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.query import router as query_router
from app.core.config import settings
from app.services.generation import GenerationService
from app.services.retrieval import RetrievalService
from app.utils.logging_config import configure_logging

_HERE = os.path.dirname(os.path.abspath(__file__))


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

# Serve static assets (CSS, JS)
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(_HERE, "static")),
    name="static",
)


@app.get("/", response_class=FileResponse, include_in_schema=False)
async def serve_frontend():
    """Serve the AutoDiag web frontend."""
    return FileResponse(os.path.join(_HERE, "templates", "index.html"), media_type="text/html")


app.include_router(query_router)
