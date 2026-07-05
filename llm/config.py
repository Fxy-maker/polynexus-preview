from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any


DEFAULT_AI_PROVIDER = "deepseek"
AI_PROVIDER_DEEPSEEK = "deepseek"
AI_PROVIDER_OPENAI = "openai"

AI_SETTINGS_KEY_PROVIDER = "ai/provider"
AI_SETTINGS_KEY_API_KEY = "ai/api_key"
AI_SETTINGS_KEY_BASE_URL = "ai/base_url"
AI_SETTINGS_KEY_MODEL = "ai/model"
AI_SETTINGS_KEY_ALLOW_MOCK = "ai/allow_mock"

_PROVIDER_ALIASES = {
    AI_PROVIDER_DEEPSEEK: {"deepseek", "ds"},
    AI_PROVIDER_OPENAI: {"openai", "gpt"},
}

_PROVIDER_DEFAULTS = {
    AI_PROVIDER_DEEPSEEK: {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-reasoner",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    AI_PROVIDER_OPENAI: {
        "label": "OpenAI / GPT",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-5.4-mini",
        "api_key_env": "OPENAI_API_KEY",
    },
}


def normalize_ai_provider(
    provider: str | None = None,
    *,
    base_url: str | None = None,
    model: str | None = None,
) -> str:
    raw = str(provider or "").strip().lower()
    for canonical, aliases in _PROVIDER_ALIASES.items():
        if raw in aliases:
            return canonical

    inferred = infer_ai_provider(base_url=base_url, model=model)
    if inferred:
        return inferred
    return DEFAULT_AI_PROVIDER


def infer_ai_provider(
    *,
    base_url: str | None = None,
    model: str | None = None,
) -> str | None:
    base = str(base_url or "").strip().lower()
    if "deepseek" in base:
        return AI_PROVIDER_DEEPSEEK
    if "openai" in base:
        return AI_PROVIDER_OPENAI

    model_name = str(model or "").strip().lower()
    if model_name.startswith("deepseek"):
        return AI_PROVIDER_DEEPSEEK
    if model_name.startswith("gpt") or model_name.startswith("o1") or model_name.startswith("o3"):
        return AI_PROVIDER_OPENAI
    return None


def provider_label(provider: str | None = None) -> str:
    provider_key = normalize_ai_provider(provider)
    return str(_PROVIDER_DEFAULTS[provider_key]["label"])


def provider_defaults(provider: str | None = None) -> dict[str, str]:
    provider_key = normalize_ai_provider(provider)
    defaults = _PROVIDER_DEFAULTS[provider_key]
    return {
        "provider": provider_key,
        "base_url": str(defaults["base_url"]),
        "model": str(defaults["model"]),
        "api_key_env": str(defaults["api_key_env"]),
        "label": str(defaults["label"]),
    }


def infer_ai_provider_from_env() -> str | None:
    deepseek_key = str(os.environ.get("DEEPSEEK_API_KEY", "") or "").strip()
    openai_key = str(os.environ.get("OPENAI_API_KEY", "") or "").strip()
    if openai_key and not deepseek_key:
        return AI_PROVIDER_OPENAI
    if deepseek_key and not openai_key:
        return AI_PROVIDER_DEEPSEEK
    return None


def default_ai_settings(provider: str | None = None) -> dict[str, Any]:
    provider_key = provider if provider is not None else infer_ai_provider_from_env() or DEFAULT_AI_PROVIDER
    defaults = provider_defaults(provider_key)
    return {
        "provider": defaults["provider"],
        "api_key": "",
        "base_url": defaults["base_url"],
        "model": defaults["model"],
        "allow_mock": True,
    }


def _coerce_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        raw = value.strip().lower()
        if raw in {"1", "true", "yes", "on"}:
            return True
        if raw in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def normalize_ai_settings(
    settings: Mapping[str, Any] | None = None,
    *,
    provider: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    allow_mock: bool | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if settings:
        payload.update(dict(settings))
    if provider is not None:
        payload["provider"] = provider
    if api_key is not None:
        payload["api_key"] = api_key
    if base_url is not None:
        payload["base_url"] = base_url
    if model is not None:
        payload["model"] = model
    if allow_mock is not None:
        payload["allow_mock"] = allow_mock

    provider_key = normalize_ai_provider(
        payload.get("provider"),
        base_url=payload.get("base_url"),
        model=payload.get("model"),
    )
    defaults = provider_defaults(provider_key)

    normalized = {
        "provider": provider_key,
        "api_key": str(payload.get("api_key", "") or "").strip(),
        "base_url": str(payload.get("base_url", defaults["base_url"]) or defaults["base_url"]).strip().rstrip("/"),
        "model": str(payload.get("model", defaults["model"]) or defaults["model"]).strip(),
        "allow_mock": _coerce_bool(payload.get("allow_mock"), True),
    }
    if not normalized["base_url"]:
        normalized["base_url"] = defaults["base_url"]
    if not normalized["model"]:
        normalized["model"] = defaults["model"]
    return normalized


def load_ai_settings(settings: Any) -> dict[str, Any]:
    if settings is None:
        return default_ai_settings()

    provider = settings.value(AI_SETTINGS_KEY_PROVIDER, DEFAULT_AI_PROVIDER)
    base_url = settings.value(AI_SETTINGS_KEY_BASE_URL, "")
    model = settings.value(AI_SETTINGS_KEY_MODEL, "")
    provider_key = (
        str(provider or "").strip()
        or infer_ai_provider(base_url=base_url, model=model)
        or infer_ai_provider_from_env()
        or DEFAULT_AI_PROVIDER
    )
    normalized = normalize_ai_settings(
        provider=provider_key,
        api_key=settings.value(AI_SETTINGS_KEY_API_KEY, ""),
        base_url=base_url,
        model=model,
        allow_mock=settings.value(AI_SETTINGS_KEY_ALLOW_MOCK, True),
    )
    return normalized


def save_ai_settings(settings: Any, ai_settings: Mapping[str, Any]) -> None:
    if settings is None:
        return
    normalized = normalize_ai_settings(ai_settings)
    settings.setValue(AI_SETTINGS_KEY_PROVIDER, normalized["provider"])
    settings.setValue(AI_SETTINGS_KEY_API_KEY, normalized["api_key"])
    settings.setValue(AI_SETTINGS_KEY_BASE_URL, normalized["base_url"])
    settings.setValue(AI_SETTINGS_KEY_MODEL, normalized["model"])
    settings.setValue(AI_SETTINGS_KEY_ALLOW_MOCK, bool(normalized["allow_mock"]))
    sync = getattr(settings, "sync", None)
    if callable(sync):
        sync()


def create_llm_client(
    settings: Mapping[str, Any] | None = None,
    *,
    provider: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    allow_mock: bool | None = None,
    timeout: int = 60,
):
    from .llm_client import LLMClient

    normalized = normalize_ai_settings(
        settings,
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
        allow_mock=allow_mock,
    )
    return LLMClient(
        base_url=normalized["base_url"],
        model=normalized["model"],
        timeout=timeout,
        allow_mock=bool(normalized["allow_mock"]),
        api_key=normalized["api_key"] or None,
    )
