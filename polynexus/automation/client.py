"""Small authenticated client for the automation-mode loopback bridge."""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from typing import Any


_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1"})
_MAX_REPLY_BYTES = 256 * 1024


@dataclass(frozen=True)
class AutomationClient:
    """Send one fixed-action request to a loopback-only bridge."""

    host: str
    port: int
    secret: str
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.host not in _LOOPBACK_HOSTS:
            raise ValueError("automation client host must be loopback")
        if not 1 <= self.port <= 65535:
            raise ValueError("automation client port is invalid")
        if not self.secret:
            raise ValueError("automation client secret must not be empty")

    def build_request(self, action: str, **payload: Any) -> dict[str, Any]:
        return {"secret": self.secret, "action": action, **payload}

    def request(self, action: str, **payload: Any) -> dict[str, Any]:
        request = self.build_request(action, **payload)
        encoded = (json.dumps(request, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
        with socket.create_connection((self.host, self.port), timeout=self.timeout_seconds) as client:
            client.settimeout(self.timeout_seconds)
            client.sendall(encoded)
            response = bytearray()
            while b"\n" not in response:
                chunk = client.recv(4096)
                if not chunk:
                    raise RuntimeError("automation bridge closed without a response")
                response.extend(chunk)
                if len(response) > _MAX_REPLY_BYTES:
                    raise RuntimeError("automation bridge response is too large")
        try:
            decoded = json.loads(bytes(response).split(b"\n", 1)[0].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("automation bridge returned invalid JSON") from exc
        if not isinstance(decoded, dict):
            raise RuntimeError("automation bridge response must be an object")
        return decoded
