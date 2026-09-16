import logging

from fastapi import APIRouter, Request

from app.schemas.query import QueryRequest, QueryResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
def health(request: Request):
    retrieval = getattr(request.app.state, "retrieval", None)
    return {
        "status": "ok",
        "chunks_indexed": retrieval.chunk_count if retrieval else None,
    }


@router.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest, request: Request) -> QueryResponse:
    retrieval = request.app.state.retrieval
    generation = request.app.state.generation

    docs = retrieval.retrieve(payload.question)
    answer = generation.generate(payload.question, docs)
    
    sources = []
    for d in docs:
        rec_id = str(d.metadata.get("record_id", "?"))
        if rec_id.isdigit():
            sources.append(f"NHTSA Complaint #{rec_id}")
        elif rec_id.endswith("000"):
            sources.append(f"NHTSA Recall #{rec_id}")
        else:
            sources.append(f"MechanicDB {rec_id}")

    logger.info("query=%r -> %d sources", payload.question, len(sources))
    return QueryResponse(answer=answer, sources=sources)
