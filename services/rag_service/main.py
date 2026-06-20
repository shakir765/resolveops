from contextlib import asynccontextmanager

from pydantic import BaseModel, Field

from fastapi import FastAPI

from resolveops_core.config import settings
from resolveops_core.logging import configure_logging, get_logger
from resolveops_core.rag.knowledge_base import kb
from resolveops_core.telemetry import instrument_fastapi, setup_tracing, shutdown_tracing

configure_logging(settings.log_level)
setup_tracing("resolveops-rag-service")
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    shutdown_tracing()


app = FastAPI(title="ResolveOps RAG Service", version="0.1.0", lifespan=lifespan)
instrument_fastapi(app)


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 3


class IngestRequest(BaseModel):
    documents: list[dict[str, str]]


@app.get("/health")
async def health():
    return {"status": "ok", "service": "rag-service"}


@app.post("/retrieve")
async def retrieve(request: RetrieveRequest):
    results = kb.retrieve(request.query, top_k=request.top_k)
    return {"results": results}


@app.post("/ingest")
async def ingest(request: IngestRequest):
    count = kb.ingest_documents(request.documents)
    logger.info("rag.ingested", count=count)
    return {"ingested": count}
