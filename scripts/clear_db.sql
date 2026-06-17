-- ResolveOps application tables (see resolveops_core/db/models.py)
TRUNCATE TABLE
    workflow_events,
    workflow_runs,
    idempotency_keys,
    tickets
RESTART IDENTITY CASCADE;
