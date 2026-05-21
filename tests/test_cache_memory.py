from datetime import UTC, datetime, timedelta
import json

import pytest

from harness_agent.cache.local import LocalJsonCacheStore
from harness_agent.memory.local import LocalJsonlMemoryStore
from harness_agent.memory.policy import MemoryPolicy
from harness_agent.sessions.base import SessionMessage
from harness_agent.sessions.local import LocalJsonSessionStore


@pytest.mark.anyio
async def test_local_json_cache_roundtrip(tmp_path) -> None:
    cache = LocalJsonCacheStore(tmp_path / "cache.json")

    await cache.set("tool:web_search", '{"query":"x"}', "cached result")

    assert await cache.get("tool:web_search", '{"query":"x"}') == "cached result"
    assert await cache.get("tool:web_search", '{"query":"y"}') is None


@pytest.mark.anyio
async def test_local_json_cache_expires_items(tmp_path) -> None:
    path = tmp_path / "cache.json"
    cache = LocalJsonCacheStore(path)
    await cache.set("tool:web_search:v2", '{"query":"x"}', "cached result", ttl_seconds=60)
    assert await cache.get("tool:web_search:v2", '{"query":"x"}') == "cached result"

    expired_at = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    path.write_text(
        json.dumps(
            {
                "tool:web_search:v2": {
                    '{"query":"x"}': {
                        "value": "cached result",
                        "expires_at": expired_at,
                        "created_at": expired_at,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    cache = LocalJsonCacheStore(path)

    assert await cache.get("tool:web_search:v2", '{"query":"x"}') is None


@pytest.mark.anyio
async def test_local_jsonl_memory_search(tmp_path) -> None:
    memory = LocalJsonlMemoryStore(tmp_path / "memory.jsonl")

    await memory.add("LiteLLM routes requests to many model providers")
    await memory.add("Unrelated note")

    results = await memory.search("How does LiteLLM route model requests?", limit=3)

    assert results
    assert "LiteLLM routes" in results[0].content


@pytest.mark.anyio
async def test_local_json_session_store_keeps_recent_messages(tmp_path) -> None:
    sessions = LocalJsonSessionStore(tmp_path / "sessions.json")

    await sessions.append("chat-1", SessionMessage(role="user", content="first"))
    await sessions.append("chat-1", SessionMessage(role="assistant", content="second"))

    recent = await sessions.recent("chat-1", limit=1)

    assert len(recent) == 1
    assert recent[0].content == "second"


def test_memory_policy_redacts_and_truncates() -> None:
    policy = MemoryPolicy(max_chars=120)

    prepared = policy.prepare_dialogue_memory(
        "token sk-abcdefghijklmnopqrstuvwxyz123456",
        "answer " * 20,
    )

    assert prepared is not None
    assert "[REDACTED_SECRET]" in prepared
    assert prepared.endswith("[TRUNCATED]")


def test_memory_policy_skips_tiny_dialogue() -> None:
    policy = MemoryPolicy(max_chars=1_000)

    assert policy.prepare_dialogue_memory("hi", "ok") is None
