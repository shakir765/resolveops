from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://resolveops:resolveops@localhost:5432/resolveops"
    redis_url: str = "redis://localhost:6379/0"
    redis_checkpoint_url: str = ""
    redis_checkpoint_ttl_minutes: int = 0
    redis_checkpoint_refresh_on_read: bool = True
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    chroma_persist_dir: str = "./data/chroma"
    rag_service_url: str = "http://localhost:8002"
    tool_runner_url: str = "http://localhost:8003"

    servicenow_instance: str = ""
    servicenow_username: str = ""
    servicenow_password: str = ""

    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""

    log_level: str = "INFO"
    environment: str = "development"
    default_tenant_id: str = "default"
    prompt_version: str = "v1"

    ticket_queue_name: str = "resolveops.tickets"
    idempotency_ttl_seconds: int = 86400
    lock_ttl_seconds: int = 300
    lock_poll_interval_seconds: int = 5
    lock_wait_timeout_seconds: int = 300

    otel_enabled: bool = True
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_exporter_otlp_insecure: bool = True
    otel_traces_sample_ratio: float = 1.0


settings = Settings()
