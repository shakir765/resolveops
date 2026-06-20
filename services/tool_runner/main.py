from contextlib import asynccontextmanager

from pydantic import BaseModel, Field

from fastapi import FastAPI

from resolveops_core.config import settings
from resolveops_core.logging import configure_logging, get_logger
from resolveops_core.telemetry import instrument_fastapi, setup_tracing, shutdown_tracing
from resolveops_core.tools.registry import TOOL_REGISTRY, execute_tool

configure_logging(settings.log_level)
setup_tracing("resolveops-tool-runner")
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    shutdown_tracing()


app = FastAPI(title="ResolveOps Tool Runner", version="0.1.0", lifespan=lifespan)
instrument_fastapi(app)


class ToolExecuteRequest(BaseModel):
    tool: str
    params: dict = Field(default_factory=dict)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "tool-runner", "tools": list(TOOL_REGISTRY.keys())}


@app.post("/execute")
async def execute(request: ToolExecuteRequest):
    logger.info("tool.execute", tool=request.tool, params=request.params)
    result = execute_tool(request.tool, request.params)
    return result
