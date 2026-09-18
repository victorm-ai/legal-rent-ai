"""LiteLLM provider registry smoke tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from config.settings import Settings
from llm.litellm_runtime import resolve_litellm_model
from llm.registry import get_llm_provider


def test_openai_factory_uses_litellm_provider():
    settings = Settings(
        llm_provider="openai",
        openai_api_key="sk-proj-test-key-123456789012345678901234",
    )
    provider = get_llm_provider(settings)
    assert provider.provider_name == "openai"
    assert provider.model_name == settings.openai_model


def test_anthropic_model_prefix():
    settings = Settings(anthropic_model="claude-3-5-haiku-20241022")
    assert resolve_litellm_model(settings, "anthropic") == "anthropic/claude-3-5-haiku-20241022"


def test_anthropic_factory_requires_key():
    settings = Settings(llm_provider="anthropic", anthropic_api_key="")
    try:
        get_llm_provider(settings)
        raise AssertionError("Expected RuntimeError for missing Anthropic key")
    except RuntimeError as exc:
        assert "ANTHROPIC_API_KEY" in str(exc)


if __name__ == "__main__":
    test_openai_factory_uses_litellm_provider()
    test_anthropic_model_prefix()
    test_anthropic_factory_requires_key()
    print("LiteLLM registry tests: PASSED")
