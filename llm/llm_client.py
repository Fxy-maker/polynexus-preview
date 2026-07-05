from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

from .config import normalize_ai_provider, provider_defaults


env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


class LLMConnectionError(RuntimeError):
    """Raised when the configured LLM endpoint cannot be reached."""


class LLMCancelledError(RuntimeError):
    """Raised when the request is cancelled via a threading.Event."""


class LLMClient:
    def __init__(
        self,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-reasoner",
        timeout: int = 60,
        allow_mock: bool = True,
        api_key: str | None = None,
        provider: str | None = None,
        api_key_env: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.allow_mock = allow_mock
        self.provider = normalize_ai_provider(provider, base_url=self.base_url, model=self.model)
        provider_info = provider_defaults(self.provider)
        self.provider_label = provider_info["label"]
        self.api_key_env = api_key_env or provider_info["api_key_env"]
        self.api_key = (
            str(api_key).strip()
            if api_key is not None
            else str(os.environ.get(self.api_key_env, "")).strip()
        )
        self.last_used_mock = False

    def chat(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_mode: bool = False,
        cancel_event: threading.Event | None = None,
    ) -> str:
        """Send a chat completion request.

        Parameters
        ----------
        prompt: User message content.
        system: Optional system prompt (sent as a ``system`` role message).
        json_mode: When True, request ``response_format={"type": "json_object"}``.
        cancel_event: When set, cancels the request between retries by
                      raising :exc:`LLMCancelledError`.
        """
        self.last_used_mock = False
        if not self.is_available():
            if self.allow_mock:
                return self._mock_response()
            raise LLMConnectionError(f"{self.provider_label} API key is not set")
        if cancel_event and cancel_event.is_set():
            raise LLMCancelledError("Request cancelled before first attempt")

        last_error: Exception | None = None
        use_json_mode = json_mode
        for attempt in range(3):
            if cancel_event and cancel_event.is_set():
                raise LLMCancelledError(f"Request cancelled before attempt {attempt + 1}")
            try:
                from openai import OpenAI

                client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=self.timeout)
                messages: list[dict[str, str]] = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                kwargs: dict = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.1,
                }
                if use_json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                response = client.chat.completions.create(**kwargs)
                return response.choices[0].message.content or ""
            except Exception as exc:
                last_error = exc
                # If JSON mode was rejected by the model, retry without it
                err_text = str(exc).lower()
                if use_json_mode and (
                    "response_format" in err_text
                    or "json_object" in err_text
                    or "not supported" in err_text
                ):
                    use_json_mode = False
                    continue
                if attempt < 2:
                    time.sleep(0.25 * (attempt + 1))

        print(f"[LLMClient] API call failed: {last_error}")
        if self.allow_mock:
            return self._mock_response()
        raise LLMConnectionError(str(last_error)) from last_error

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _mock_response(self) -> str:
        self.last_used_mock = True
        return json.dumps(
            {
                "assessment": "WARN",
                "confidence": 0.0,
                "reasoning": f"{self.provider_label} API 不可用或未配置 API Key，已返回离线 mock 调参建议。",
                "suggestions": ["在设置中填写 API Key 后可获得真实建议。"],
                "reference_cases": [],
            },
            ensure_ascii=False,
        )
