from __future__ import annotations

import json
import locale
import os
from dataclasses import dataclass
from pathlib import Path

from .network import DEFAULT_KOREAN_CARRIER_IP_RANGES
from .secret import decrypt_text, encrypt_text, is_encrypted


DEFAULT_CONFIG_PATH = Path("focusaway-config.json")


@dataclass
class AppConfig:
    host: str = "127.0.0.1"
    port: int = 8787
    timezone: str = "Asia/Seoul"
    database_path: str = "focusaway.db"
    max_request_bytes: int = 10 * 1024 * 1024
    cors_allowed_origins: str = "*"
    upstream_base_url: str = "http://127.0.0.1:11434"
    upstream_api_prefix: str = "/v1"
    upstream_models_path: str = "/v1/models"
    upstream_api_key: str = ""
    upstream_auth_mode: str = "bearer"
    upstream_auth_header: str = "Authorization"
    upstream_auth_scheme: str = "Bearer"
    upstream_extra_headers: str = ""
    upstream_timeout_seconds: int = 300
    session_hours: int = 24 * 7
    signup_cooldown_seconds: int = 60 * 60
    carrier_signup_cooldown_seconds: int = 10 * 60
    carrier_ip_ranges: str = DEFAULT_KOREAN_CARRIER_IP_RANGES
    trusted_proxy_cidrs: str = "127.0.0.1/32,::1/128"
    app_name: str = "FocusAway"
    operator_name: str = "FocusAway 운영자"
    contact_email: str = ""
    contact_address: str = ""
    launcher_language: str = ""


def normalize_language(value: str | None) -> str:
    return "ko" if str(value or "").strip().lower().startswith("ko") else "en"


def default_language_from_os() -> str:
    lang = locale.getlocale()[0] or os.environ.get("LANG", "")
    return normalize_language(lang)


def load_config(config_path: str | None = None) -> AppConfig:
    path = Path(config_path or os.environ.get("FOCUSAWAY_CONFIG", DEFAULT_CONFIG_PATH))
    data = {}
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    stored_upstream_api_key = data.get("upstream_api_key", AppConfig.upstream_api_key)
    upstream_api_key = os.environ.get("FOCUSAWAY_UPSTREAM_API_KEY")
    if upstream_api_key is None:
        upstream_api_key = decrypt_text(stored_upstream_api_key, path)
        if path.exists() and stored_upstream_api_key and not is_encrypted(stored_upstream_api_key):
            data["upstream_api_key"] = encrypt_text(stored_upstream_api_key, path)
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass

    launcher_language = data.get("launcher_language", "")
    if not launcher_language:
        launcher_language = default_language_from_os()

    return AppConfig(
        host=os.environ.get("FOCUSAWAY_HOST", data.get("host", AppConfig.host)),
        port=int(os.environ.get("FOCUSAWAY_PORT", data.get("port", AppConfig.port))),
        timezone=os.environ.get("FOCUSAWAY_TIMEZONE", data.get("timezone", AppConfig.timezone)),
        database_path=os.environ.get("FOCUSAWAY_DATABASE_PATH", data.get("database_path", AppConfig.database_path)),
        max_request_bytes=int(
            os.environ.get("FOCUSAWAY_MAX_REQUEST_BYTES", data.get("max_request_bytes", AppConfig.max_request_bytes))
        ),
        cors_allowed_origins=os.environ.get(
            "FOCUSAWAY_CORS_ALLOWED_ORIGINS",
            data.get("cors_allowed_origins", AppConfig.cors_allowed_origins),
        ),
        upstream_base_url=os.environ.get(
            "FOCUSAWAY_UPSTREAM_BASE_URL",
            data.get("upstream_base_url", AppConfig.upstream_base_url),
        ).rstrip("/"),
        upstream_api_prefix=os.environ.get(
            "FOCUSAWAY_UPSTREAM_API_PREFIX",
            data.get("upstream_api_prefix", AppConfig.upstream_api_prefix),
        ),
        upstream_models_path=os.environ.get(
            "FOCUSAWAY_UPSTREAM_MODELS_PATH",
            data.get("upstream_models_path", AppConfig.upstream_models_path),
        ),
        upstream_api_key=upstream_api_key,
        upstream_auth_mode=os.environ.get(
            "FOCUSAWAY_UPSTREAM_AUTH_MODE",
            data.get("upstream_auth_mode", AppConfig.upstream_auth_mode),
        ),
        upstream_auth_header=os.environ.get(
            "FOCUSAWAY_UPSTREAM_AUTH_HEADER",
            data.get("upstream_auth_header", AppConfig.upstream_auth_header),
        ),
        upstream_auth_scheme=os.environ.get(
            "FOCUSAWAY_UPSTREAM_AUTH_SCHEME",
            data.get("upstream_auth_scheme", AppConfig.upstream_auth_scheme),
        ),
        upstream_extra_headers=os.environ.get(
            "FOCUSAWAY_UPSTREAM_EXTRA_HEADERS",
            data.get("upstream_extra_headers", AppConfig.upstream_extra_headers),
        ),
        upstream_timeout_seconds=int(
            os.environ.get(
                "FOCUSAWAY_UPSTREAM_TIMEOUT_SECONDS",
                data.get("upstream_timeout_seconds", AppConfig.upstream_timeout_seconds),
            )
        ),
        session_hours=int(
            os.environ.get("FOCUSAWAY_SESSION_HOURS", data.get("session_hours", AppConfig.session_hours))
        ),
        signup_cooldown_seconds=max(
            0,
            int(
                os.environ.get(
                    "FOCUSAWAY_SIGNUP_COOLDOWN_SECONDS",
                    data.get("signup_cooldown_seconds", AppConfig.signup_cooldown_seconds),
                )
            ),
        ),
        carrier_signup_cooldown_seconds=max(
            0,
            int(
                os.environ.get(
                    "FOCUSAWAY_CARRIER_SIGNUP_COOLDOWN_SECONDS",
                    data.get("carrier_signup_cooldown_seconds", AppConfig.carrier_signup_cooldown_seconds),
                )
            ),
        ),
        carrier_ip_ranges=os.environ.get(
            "FOCUSAWAY_CARRIER_IP_RANGES",
            data.get("carrier_ip_ranges", AppConfig.carrier_ip_ranges),
        ),
        trusted_proxy_cidrs=os.environ.get(
            "FOCUSAWAY_TRUSTED_PROXY_CIDRS",
            data.get("trusted_proxy_cidrs", AppConfig.trusted_proxy_cidrs),
        ),
        app_name=os.environ.get("FOCUSAWAY_APP_NAME", data.get("app_name", AppConfig.app_name)),
        operator_name=os.environ.get("FOCUSAWAY_OPERATOR_NAME", data.get("operator_name", AppConfig.operator_name)),
        contact_email=os.environ.get("FOCUSAWAY_CONTACT_EMAIL", data.get("contact_email", AppConfig.contact_email)),
        contact_address=os.environ.get(
            "FOCUSAWAY_CONTACT_ADDRESS",
            data.get("contact_address", AppConfig.contact_address),
        ),
        launcher_language=normalize_language(
            os.environ.get("FOCUSAWAY_LAUNCHER_LANGUAGE", launcher_language)
        ),
    )


def save_config(config: AppConfig, config_path: str | None = None) -> Path:
    path = Path(config_path or DEFAULT_CONFIG_PATH)
    upstream_api_key = encrypt_text(config.upstream_api_key, path)
    path.write_text(
        json.dumps(
            {
                "host": config.host,
                "port": config.port,
                "timezone": config.timezone,
                "database_path": config.database_path,
                "max_request_bytes": config.max_request_bytes,
                "cors_allowed_origins": config.cors_allowed_origins,
                "upstream_base_url": config.upstream_base_url,
                "upstream_api_prefix": config.upstream_api_prefix,
                "upstream_models_path": config.upstream_models_path,
                "upstream_api_key": upstream_api_key,
                "upstream_auth_mode": config.upstream_auth_mode,
                "upstream_auth_header": config.upstream_auth_header,
                "upstream_auth_scheme": config.upstream_auth_scheme,
                "upstream_extra_headers": config.upstream_extra_headers,
                "upstream_timeout_seconds": config.upstream_timeout_seconds,
                "session_hours": config.session_hours,
                "signup_cooldown_seconds": config.signup_cooldown_seconds,
                "carrier_signup_cooldown_seconds": config.carrier_signup_cooldown_seconds,
                "carrier_ip_ranges": config.carrier_ip_ranges,
                "trusted_proxy_cidrs": config.trusted_proxy_cidrs,
                "app_name": config.app_name,
                "operator_name": config.operator_name,
                "contact_email": config.contact_email,
                "contact_address": config.contact_address,
                "launcher_language": normalize_language(config.launcher_language),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path
