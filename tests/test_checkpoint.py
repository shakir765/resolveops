from unittest.mock import MagicMock, patch

from resolveops_core.graph.checkpoint import checkpoint_redis_url, get_checkpointer, reset_checkpointer


def test_checkpoint_redis_url_defaults_to_redis_url():
    reset_checkpointer()
    url = checkpoint_redis_url()
    assert url.startswith("redis://")


@patch("langgraph.checkpoint.redis.RedisSaver")
def test_get_checkpointer_uses_redis_saver(mock_redis_saver):
    reset_checkpointer()
    mock_instance = MagicMock()
    mock_redis_saver.return_value = mock_instance

    saver = get_checkpointer()

    mock_redis_saver.assert_called_once()
    call_kwargs = mock_redis_saver.call_args.kwargs
    assert "redis_url" in call_kwargs
    mock_instance.setup.assert_called_once()
    assert saver is mock_instance

    # Singleton — second call does not re-init
    get_checkpointer()
    assert mock_redis_saver.call_count == 1

    reset_checkpointer()
