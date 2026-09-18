"""Chat LLM observability payload tests."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from observability.chat_llm_tracker import ChatLlmCallTracker, ChatObservabilityContext


def test_tracker_emits_three_event_shapes():
    repo = MagicMock()
    tracker = ChatLlmCallTracker(
        ChatObservabilityContext(chat_session_id="00000000-0000-0000-0000-000000000001", stream=True),
        repository=repo,
    )

    started = tracker.started("openai", "gpt-4o-mini")
    assert started["event"] == "llm_call_started"
    assert started["request_id"]
    assert started["latency_ms"] == 0
    assert started["stream"] is True

    completed = tracker.completed(
        provider="openai",
        model="gpt-4o-mini",
        tokens_in=100,
        tokens_out=50,
        cost_usd=0.001,
        finish_reason="stop",
    )
    assert completed["event"] == "llm_call_completed"
    assert completed["tokens_in"] == 100
    assert completed["latency_ms"] is not None
    assert completed["latency_ms"] >= 0

    failed = tracker.failed(provider="openai", model="gpt-4o-mini", error=RuntimeError("boom"))
    assert failed["event"] == "llm_call_failed"
    assert failed["error_type"] == "RuntimeError"
    assert failed["error_message"] == "boom"

    assert repo.insert_event.call_count == 3


if __name__ == "__main__":
    test_tracker_emits_three_event_shapes()
    print("Chat LLM observability tests: PASSED")
