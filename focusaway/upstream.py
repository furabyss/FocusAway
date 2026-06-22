from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .config import AppConfig


class UpstreamClient:
    def __init__(self, config: AppConfig):
        self.config = config

    def _normalize_path(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if path.startswith("/"):
            return f"{self.config.upstream_base_url}{path}"
        prefix = self.config.upstream_api_prefix.rstrip("/")
        return f"{self.config.upstream_base_url}{prefix}/{path.lstrip('/')}"

    def _auth_headers(self) -> dict[str, str]:
        mode = self.config.upstream_auth_mode.lower().strip()
        if mode == "none" or not self.config.upstream_api_key:
            return {}
        header_name = self.config.upstream_auth_header.strip() or "Authorization"
        if mode == "bearer":
            scheme = (self.config.upstream_auth_scheme or "Bearer").strip()
            return {header_name: f"{scheme} {self.config.upstream_api_key}".strip()}
        if mode == "header":
            return {header_name: self.config.upstream_api_key}
        if mode == "x-api-key":
            return {header_name: self.config.upstream_api_key}
        return {header_name: self.config.upstream_api_key}

    def _extra_headers(self) -> dict[str, str]:
        raw = (self.config.upstream_extra_headers or "").strip()
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(key): str(value) for key, value in data.items()}

    def _request(self, path: str, method: str = "GET", body: bytes | None = None, content_type: str = "application/json"):
        request = urllib.request.Request(
            self._normalize_path(path),
            method=method,
            data=body,
            headers=self._auth_headers() | self._extra_headers() | {"Content-Type": content_type},
        )
        return urllib.request.urlopen(request, timeout=self.config.upstream_timeout_seconds)

    def fetch_models(self) -> list[dict]:
        with self._request(self.config.upstream_models_path) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("data", [])

    def _proxy_headers(self, headers: dict[str, str], stream: bool) -> dict[str, str]:
        forwarded: dict[str, str] = {}
        forwarded.update(self._auth_headers())
        forwarded.update(self._extra_headers())
        passthrough = {
            "Accept",
            "Content-Type",
            "OpenAI-Beta",
            "X-Requested-With",
            "Anthropic-Version",
            "Anthropic-Beta",
            "X-Stainless-Lang",
            "X-Stainless-Package-Version",
            "X-Stainless-Os",
            "X-Stainless-Arch",
            "X-Stainless-Runtime",
            "X-Stainless-Runtime-Version",
        }
        for key, value in headers.items():
            normalized = "-".join(part.capitalize() for part in key.split("-"))
            if normalized in passthrough and value:
                forwarded[normalized] = value
        if "Content-Type" not in forwarded:
            forwarded["Content-Type"] = "application/json"
        if stream:
            forwarded["Accept"] = "text/event-stream"
        elif "Accept" not in forwarded or forwarded["Accept"] == "text/event-stream":
            forwarded["Accept"] = "application/json"
        return forwarded

    def open_proxy(
        self,
        path: str,
        method: str,
        body: bytes | None,
        headers: dict[str, str],
        stream: bool,
    ) -> tuple[int, dict[str, str], Any]:
        request = urllib.request.Request(
            self._normalize_path(path),
            method=method,
            data=body,
            headers=self._proxy_headers(headers, stream),
        )
        try:
            response = urllib.request.urlopen(request, timeout=self.config.upstream_timeout_seconds)
            return response.status, dict(response.headers.items()), response
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers.items()), exc

    def proxy(
        self,
        path: str,
        method: str,
        body: bytes | None,
        headers: dict[str, str],
        stream: bool,
    ) -> tuple[int, dict[str, str], bytes]:
        status, response_headers, response = self.open_proxy(path, method, body, headers, stream)
        try:
            return status, response_headers, response.read()
        finally:
            response.close()
