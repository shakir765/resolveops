# ResolveOps

Multi-agent IT ticket resolution platform using **LangGraph**, with split microservices for API, graph execution, RAG, and tool running.

## Scope delivered

### Phase 1
- FastAPI ticket ingest API
- LangGraph workflow with Supervisor, Triage, Knowledge, Resolution, Communication
- Basic RAG over runbooks and past tickets
- IT tools: password reset, account unlock, service health check, VPN profile reset, CMDB lookup
- PostgreSQL for tickets, audit trail, and workflow runs
- Manual/async ticket processing
- Structured logging

### Phase 2
- Full agent team: Classifier, Diagnostic, Tool Executor, Escalation, Validator
- Conditional routing and HITL escalation/resume
- ServiceNow and Jira import integrations
- Prompt versioning (`resolveops_core/prompts/v1`)
- Evaluation framework (resolution rate, escalation rate, SLA, confidence)
- Admin dashboard
- Test suite with fixtures

### Phase 3 (first 4 items)
- Split services: API, Graph Worker, Tool Runner, RAG Service
- RabbitMQ async ticket queue
- Externalized LangGraph checkpointing in Redis
- Redis for locks, cache, session helpers, and graph checkpoints

## Architecture

```text
Client -> API -> RabbitMQ -> Graph Worker -> LangGraph + Redis checkpoints
                |                |
                |                +-> RAG Service (Chroma)
                |                +-> Tool Runner
                +-> PostgreSQL (tickets/audit) / Redis (checkpoints, locks, cache)
```

## Quick start

### One-click start (recommended on Windows)

```powershell
cd C:\Users\shaki\Projects\resolveops
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
.\scripts\start_all.ps1
```

Or in Cursor: **Terminal → Run Task → ResolveOps: Start All (one click)**  
(Shortcut: **Ctrl+Shift+B** if set as default build task)

Stop Docker infra: `.\scripts\stop_all.ps1` (close app terminal windows manually)

### Alternative: everything in Docker (single command)

```powershell
docker compose up -d --build
```

Runs postgres, redis, rabbitmq, API, graph-worker, RAG, and tool-runner in containers.

### Manual start

```bash
cd C:\Users\shaki\Projects\resolveops
copy .env.example .env
docker compose up -d postgres redis rabbitmq
pip install -e ".[dev]"
python scripts/seed_kb.py
```

> **Note:** LangGraph checkpoints require **Redis Stack** (or Redis 8+ with RedisJSON and RediSearch). The `docker-compose.yml` uses `redis/redis-stack-server`.

```bash
# Terminal 1
uvicorn services.rag_service.main:app --port 8002 --reload

# Terminal 2
uvicorn services.tool_runner.main:app --port 8003 --reload

# Terminal 3
uvicorn services.api.main:app --port 8000 --reload

# Terminal 4
python -m services.graph_worker.main

# Terminal 5 — Helpdesk portal (optional)
cd portal
npm install
npm run dev
```

Portal: [http://localhost:5173](http://localhost:5173) (see `portal/README.md`).

## API examples

Create ticket:

```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Cannot connect to VPN\",\"description\":\"Error 619 from home office\",\"user_id\":\"jsmith\"}"
```

Queue processing:

```bash
curl -X POST http://localhost:8000/tickets/INC-xxxx/process \
  -H "Content-Type: application/json" \
  -d "{\"async_mode\": true}"
```

Sync processing (no queue):

```bash
curl -X POST http://localhost:8000/tickets/INC-xxxx/process \
  -H "Content-Type: application/json" \
  -d "{\"async_mode\": false}"
```

Admin dashboard:

```text
http://localhost:8000/admin/dashboard
```

## LangGraph state management

ResolveOps treats LangGraph state as the **runtime working memory** for one ticket run. **Redis** stores LangGraph checkpoints; **PostgreSQL** remains the durable system of record for tickets, runs, and audit events.

| Concern | Implementation |
|---|---|
| Shared state schema | `resolveops_core/graph/state.py` — `TicketState` with reducers for `messages`, `kb_context`, `tool_results`, `actions_taken` |
| Business vs graph position | `status` = ticket lifecycle; `current_step` = active graph node |
| Agent ownership | Each agent may only patch its own keys via `apply_agent_patch()` |
| Per-step audit | `state_before` → `state_patch` → `state_after` events in `workflow_events` (PostgreSQL) |
| Checkpointing | `RedisSaver` in `resolveops_core/graph/checkpoint.py`, keyed by `thread_id` = `{ticket_id}:{run_id}` |
| Redis requirements | Redis Stack or Redis 8+ (RedisJSON + RediSearch modules required) |
| Interrupt / HITL | Graph pauses before `human_review`; resume via `POST /runs/{thread_id}/resume` |
| Idempotent runs | Active runs are reused; worker waits for Redis lock, skips finished runs, requeues on lock timeout |
| Inspect state | `GET /state/threads/{thread_id}` returns checkpoint snapshot + pending steps |

```text
API/Worker -> seed initial_state -> LangGraph invoke (Redis checkpoint each step)
           -> StateStore syncs distilled fields to PostgreSQL (tickets + workflow_runs)
           -> workflow_events stores audit trail per agent step
```

## Observability (OpenTelemetry)

Phase 0 and 1 are implemented: OTLP trace export with Grafana, Tempo, Prometheus, Loki, and the OTel Collector.

```text
Services -> OTLP (4317) -> OTel Collector -> Tempo (traces)
                                         -> Prometheus (collector metrics)
Grafana :3000  (Tempo / Prometheus / Loki datasources pre-provisioned)
```

**Trace coverage:**
- FastAPI auto-instrumentation on API, RAG, and tool-runner
- W3C trace context through RabbitMQ message headers (API -> worker)
- Manual spans: `graph.run`, `graph.node.*`, `worker.process_ticket`, `queue.publish/process`
- httpx auto-instrumentation for RAG and tool-runner calls from graph agents

**Local usage:**

```bash
docker compose up -d --build
# Grafana: http://localhost:3000  -> Explore -> Tempo
# Submit a ticket, then search traces by service or ticket.id attribute
```

Configure via `.env`:

```env
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_TRACES_SAMPLE_RATIO=1.0
```

Set `OTEL_ENABLED=false` to disable export (e.g. unit tests).

## Testing

```bash
pytest tests -v
```

## Notes

- Agents use rule-based logic by default so the project runs without an OpenAI key.
- Set `OPENAI_API_KEY` in `.env` to enable LLM-enhanced communication/diagnostics.
- ServiceNow/Jira integrations run in mock mode unless credentials are configured.
