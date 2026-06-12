from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def drive_mode_enabled() -> bool:
    source = _env("UNIOMERCATO_DATA_SOURCE", "")
    if source:
        return source.lower() == "drive"
    return bool(_env("GOOGLE_DRIVE_FOLDER_ID"))


def drive_folder_id() -> str:
    return _env("UNIOMERCATO_DRIVE_FOLDER_ID") or _env("GOOGLE_DRIVE_FOLDER_ID")


def service_account_file() -> Path | None:
    raw = _env("UNIOMERCATO_SERVICE_ACCOUNT_FILE") or _env("GOOGLE_APPLICATION_CREDENTIALS")
    if not raw:
        return None
    return Path(raw).expanduser()


def drive_cache_root() -> Path:
    raw = _env("UNIOMERCATO_DRIVE_CACHE_DIR")
    if raw:
        return Path(raw).expanduser()
    return REPO_ROOT / ".cache" / "drive_mirror"


@lru_cache(maxsize=1)
def runtime_root() -> Path:
    """Return the active file root. In drive mode, mirror the Drive tree locally."""
    if not drive_mode_enabled():
        return REPO_ROOT

    from drive_sync import sync_drive_root

    return sync_drive_root()


def data_dir() -> Path:
    return runtime_root() / "data"


def assets_dir() -> Path:
    return runtime_root() / "assets"


def asset_path(*parts: str) -> Path:
    return assets_dir().joinpath(*parts)


def data_path(*parts: str) -> Path:
    return data_dir().joinpath(*parts)
