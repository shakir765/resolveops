from resolveops_core.config import settings

_checkpointer = None


def checkpoint_redis_url() -> str:
    """Redis URL for LangGraph checkpoints (requires RedisJSON + RediSearch)."""
    return settings.redis_checkpoint_url or settings.redis_url


def get_checkpointer():
    """Return a singleton RedisSaver for LangGraph state persistence."""
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    from langgraph.checkpoint.redis import RedisSaver

    url = checkpoint_redis_url()
    ttl = None
    if settings.redis_checkpoint_ttl_minutes > 0:
        ttl = {
            "default_ttl": settings.redis_checkpoint_ttl_minutes,
            "refresh_on_read": settings.redis_checkpoint_refresh_on_read,
        }

    # Use constructor directly for a long-lived singleton.
    # from_conn_string() is a context manager that closes Redis on __exit__.
    saver = RedisSaver(redis_url=url, ttl=ttl)
    saver.setup()
    _checkpointer = saver
    return _checkpointer


def reset_checkpointer() -> None:
    """Clear cached checkpointer (useful in tests)."""
    global _checkpointer
    if _checkpointer is not None:
        try:
            if getattr(_checkpointer, "_owns_its_client", False):
                _checkpointer._redis.close()
        except Exception:
            pass
    _checkpointer = None
