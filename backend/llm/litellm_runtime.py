"""Chat completion helpers for OpenAI and Anthropic (RF-65, RF-66).

Uses vendor SDKs directly to avoid LiteLLM import issues with Pydantic 2.10+.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from config.settings import Settings

logger = logging.getLogger(__name__)

LITELLM_CHAT_PROVIDERS = frozenset({"openai", "anthropic"})


def is_litellm_provider(provider: str) -> bool:
    """True when provider is handled by this module (OpenAI or Anthropic)."""
    return provider.strip().lower() in LITELLM_CHAT_PROVIDERS


def is_usable_openai_key(api_key: str) -> bool:
    key = api_key.strip()
    placeholders = {"", "your-openai-api-key", "changeme", "sk-your-key-here"}
    if key in placeholders:
        return False
    return key.startswith(("sk-", "sk-proj-")) and len(key) > 20


def is_usable_anthropic_key(api_key: str) -> bool:
    key = api_key.strip()
    placeholders = {"", "your-anthropic-api-key", "changeme"}
    if key in placeholders:
        return False
    return key.startswith("sk-ant-") and len(key) > 20


def resolve_litellm_model(settings: Settings, provider: str | None = None) -> str:
    """Return display model id for the configured provider."""
    name = (provider or settings.llm_provider).strip().lower()
    if name == "openai":
        return settings.openai_model.strip()
    if name == "anthropic":
        model = settings.anthropic_model.strip()
        if model.startswith("anthropic/"):
            return model
        return f"anthropic/{model}"
    raise RuntimeError(f"Model resolution not supported for provider: {name}")


def _anthropic_model_id(settings: Settings) -> str:
    model = settings.anthropic_model.strip()
    if model.startswith("anthropic/"):
        return model.split("/", 1)[1]
    return model


def resolve_provider_api_key(settings: Settings, provider: str) -> str:
    name = provider.strip().lower()
    if name == "openai":
        return settings.openai_api_key.strip()
    if name == "anthropic":
        return settings.anthropic_api_key.strip()
    raise RuntimeError(f"No API key mapping for provider: {name}")


def _split_messages_for_anthropic(
    messages: list[dict[str, str]],
) -> tuple[str | None, list[dict[str, str]]]:
    system_parts: list[str] = []
    chat: list[dict[str, str]] = []
    for item in messages:
        role = item.get("role", "user")
        content = item.get("content", "")
        if role == "system":
            system_parts.append(content)
        elif role in ("user", "assistant"):
            chat.append({"role": role, "content": content})
        else:
            chat.append({"role": "user", "content": content})
    system = "\n\n".join(system_parts) if system_parts else None
    return system, chat


def resolve_judge_model(settings: Settings) -> tuple[str, str]:
    """Return (provider, model_id) for eval LLM-as-judge (stronger than default analysis model)."""
    provider = (settings.eval_judge_provider or settings.llm_provider).strip().lower()
    if provider == "openai":
        return provider, settings.eval_judge_openai_model.strip()
    if provider == "anthropic":
        model = settings.eval_judge_anthropic_model.strip()
        if model.startswith("anthropic/"):
            return provider, model.split("/", 1)[1]
        return provider, model
    raise RuntimeError(
        f"Eval judge provider must be openai or anthropic, got: {provider}. "
        "Set EVAL_JUDGE_PROVIDER and the corresponding API key."
    )


def _openai_completion(
    *,
    settings: Settings,
    messages: list[dict[str, str]],
    temperature: float,
    json_mode: bool,
    model: str | None = None,
) -> tuple[str, dict[str, int | str | None]]:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key.strip())
    kwargs: dict[str, Any] = {
        "model": (model or settings.openai_model).strip(),
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content or ""
    usage = response.usage
    finish_reason = response.choices[0].finish_reason if response.choices else None
    return content, {
        "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
        "completion_tokens": getattr(usage, "completion_tokens", None) if usage else None,
        "finish_reason": finish_reason,
    }


def _anthropic_completion(
    *,
    settings: Settings,
    messages: list[dict[str, str]],
    temperature: float,
    model: str | None = None,
) -> tuple[str, dict[str, int | str | None]]:
    from anthropic import Anthropic

    system, chat = _split_messages_for_anthropic(messages)
    if not chat:
        raise RuntimeError("Anthropic completion requires at least one user/assistant message")

    client = Anthropic(api_key=settings.anthropic_api_key.strip())
    kwargs: dict[str, Any] = {
        "model": (model or _anthropic_model_id(settings)),
        "messages": chat,
        "max_tokens": 8192,
        "temperature": temperature,
    }
    if system:
        kwargs["system"] = system

    response = client.messages.create(**kwargs)
    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    usage = response.usage
    return "".join(parts), {
        "prompt_tokens": getattr(usage, "input_tokens", None) if usage else None,
        "completion_tokens": getattr(usage, "output_tokens", None) if usage else None,
        "finish_reason": getattr(response, "stop_reason", None),
    }


def _openai_completion_stream(
    *,
    settings: Settings,
    messages: list[dict[str, str]],
    temperature: float,
    json_mode: bool,
    usage_out: dict[str, int | str | None] | None,
) -> Iterator[str]:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key.strip())
    kwargs: dict[str, Any] = {
        "model": settings.openai_model.strip(),
        "messages": messages,
        "temperature": temperature,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    stream = client.chat.completions.create(**kwargs)
    for chunk in stream:
        usage = getattr(chunk, "usage", None)
        if usage_out is not None and usage is not None:
            usage_out["prompt_tokens"] = getattr(usage, "prompt_tokens", None)
            usage_out["completion_tokens"] = getattr(usage, "completion_tokens", None)
        choices = chunk.choices or []
        if not choices:
            continue
        finish_reason = choices[0].finish_reason
        if usage_out is not None and finish_reason:
            usage_out["finish_reason"] = finish_reason
        delta = choices[0].delta
        piece = getattr(delta, "content", None) if delta else None
        if piece:
            yield piece


def _anthropic_completion_stream(
    *,
    settings: Settings,
    messages: list[dict[str, str]],
    temperature: float,
    usage_out: dict[str, int | str | None] | None,
) -> Iterator[str]:
    from anthropic import Anthropic

    system, chat = _split_messages_for_anthropic(messages)
    if not chat:
        raise RuntimeError("Anthropic stream requires at least one user/assistant message")

    client = Anthropic(api_key=settings.anthropic_api_key.strip())
    kwargs: dict[str, Any] = {
        "model": _anthropic_model_id(settings),
        "messages": chat,
        "max_tokens": 8192,
        "temperature": temperature,
    }
    if system:
        kwargs["system"] = system

    with client.messages.stream(**kwargs) as stream:
        for text in stream.text_stream:
            yield text
        if usage_out is not None:
            final = stream.get_final_message()
            usage = final.usage
            usage_out["prompt_tokens"] = getattr(usage, "input_tokens", None)
            usage_out["completion_tokens"] = getattr(usage, "output_tokens", None)
            usage_out["finish_reason"] = getattr(final, "stop_reason", None)


def litellm_completion(
    *,
    settings: Settings,
    messages: list[dict[str, str]],
    temperature: float,
    json_mode: bool = True,
    provider: str | None = None,
) -> tuple[str, dict[str, int | str | None]]:
    """Run a chat completion; returns (content, usage metadata)."""
    provider_name = (provider or settings.llm_provider).strip().lower()
    if not is_litellm_provider(provider_name):
        raise RuntimeError(f"Provider {provider_name} is not configured for chat/analysis SDK")

    try:
        if provider_name == "openai":
            return _openai_completion(
                settings=settings,
                messages=messages,
                temperature=temperature,
                json_mode=json_mode,
            )
        return _anthropic_completion(
            settings=settings,
            messages=messages,
            temperature=temperature,
        )
    except Exception as exc:
        model = resolve_litellm_model(settings, provider_name)
        logger.exception("LLM completion failed (provider=%s, model=%s)", provider_name, model)
        raise RuntimeError(f"LLM completion failed ({provider_name}): {exc}") from exc


def litellm_completion_stream(
    *,
    settings: Settings,
    messages: list[dict[str, str]],
    temperature: float,
    json_mode: bool = True,
    provider: str | None = None,
    usage_out: dict[str, int | str | None] | None = None,
) -> Iterator[str]:
    """Stream text deltas from chat completion."""
    provider_name = (provider or settings.llm_provider).strip().lower()
    if not is_litellm_provider(provider_name):
        raise RuntimeError(f"Provider {provider_name} is not configured for chat/analysis SDK")

    try:
        if provider_name == "openai":
            yield from _openai_completion_stream(
                settings=settings,
                messages=messages,
                temperature=temperature,
                json_mode=json_mode,
                usage_out=usage_out,
            )
            return
        yield from _anthropic_completion_stream(
            settings=settings,
            messages=messages,
            temperature=temperature,
            usage_out=usage_out,
        )
    except Exception as exc:
        model = resolve_litellm_model(settings, provider_name)
        logger.exception("LLM stream failed (provider=%s, model=%s)", provider_name, model)
        raise RuntimeError(f"LLM stream failed ({provider_name}): {exc}") from exc


def judge_completion(
    *,
    settings: Settings,
    messages: list[dict[str, str]],
    temperature: float = 0.0,
) -> tuple[str, dict[str, int | str | None], str]:
    """Chat completion for eval judge using EVAL_JUDGE_* settings (returns content, usage, model)."""
    provider_name, model_id = resolve_judge_model(settings)
    if provider_name == "openai":
        if not is_usable_openai_key(settings.openai_api_key):
            raise RuntimeError("OPENAI_API_KEY is required for eval judge (EVAL_JUDGE_PROVIDER=openai)")
        content, usage = _openai_completion(
            settings=settings,
            messages=messages,
            temperature=temperature,
            json_mode=True,
            model=model_id,
        )
        return content, usage, model_id
    if provider_name == "anthropic":
        if not is_usable_anthropic_key(settings.anthropic_api_key):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is required for eval judge (EVAL_JUDGE_PROVIDER=anthropic)"
            )
        content, usage = _anthropic_completion(
            settings=settings,
            messages=messages,
            temperature=temperature,
            model=model_id,
        )
        return content, usage, model_id
    raise RuntimeError(f"Unsupported eval judge provider: {provider_name}")
