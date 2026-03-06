from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    access_key: str
    secret_key: str
    base_url: str = "https://openapi.liblibai.cloud"
    output_dir: Path = Path("/data/output")
    request_timeout_seconds: float = 120.0
    default_poll_interval_seconds: float = 5.0
    default_poll_timeout_seconds: float = 900.0
    auto_download_results: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    mcp_path: str = "/mcp"

    @classmethod
    def from_env(cls) -> "Settings":
        access_key = os.getenv("LIBLIB_ACCESS_KEY", "").strip()
        secret_key = os.getenv("LIBLIB_SECRET_KEY", "").strip()
        if not access_key or not secret_key:
            raise RuntimeError(
                "Missing credentials. Set LIBLIB_ACCESS_KEY and LIBLIB_SECRET_KEY."
            )

        base_url = os.getenv("LIBLIB_BASE_URL", "https://openapi.liblibai.cloud").rstrip("/")
        output_dir = Path(os.getenv("LIBLIB_OUTPUT_DIR", "/data/output")).expanduser()
        timeout = float(os.getenv("LIBLIB_REQUEST_TIMEOUT_SECONDS", "120"))
        poll_interval = float(os.getenv("LIBLIB_DEFAULT_POLL_INTERVAL_SECONDS", "5"))
        poll_timeout = float(os.getenv("LIBLIB_DEFAULT_POLL_TIMEOUT_SECONDS", "900"))
        auto_download = _env_bool("LIBLIB_AUTO_DOWNLOAD_RESULTS", True)
        host = os.getenv("LIBLIB_HOST", "0.0.0.0")
        port = int(os.getenv("LIBLIB_PORT", "8000"))
        mcp_path = os.getenv("LIBLIB_MCP_PATH", "/mcp")

        output_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            access_key=access_key,
            secret_key=secret_key,
            base_url=base_url,
            output_dir=output_dir,
            request_timeout_seconds=timeout,
            default_poll_interval_seconds=poll_interval,
            default_poll_timeout_seconds=poll_timeout,
            auto_download_results=auto_download,
            host=host,
            port=port,
            mcp_path=mcp_path,
        )
