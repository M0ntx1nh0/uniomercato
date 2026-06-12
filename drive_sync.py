from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from dotenv import dotenv_values

from project_paths import drive_cache_root, drive_folder_id, service_account_file

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
FOLDER_MIME = "application/vnd.google-apps.folder"

# The Drive folder names used by the user and the local layout expected by the app.
DRIVE_TO_LOCAL = {
    "datos": Path("data"),
    "escudo": Path("assets") / "escudo",
    "logos_competiciones": Path("assets") / "competiciones",
    "mcode": Path("assets") / "mcode",
}


@dataclass(frozen=True)
class DriveConfig:
    key_file: Path
    root_folder_id: str
    cache_root: Path


def _load_config() -> DriveConfig:
    key_file = service_account_file()
    root_id = drive_folder_id()
    values = dotenv_values(".env")
    has_inline_creds = bool(
        (os.getenv("GOOGLE_CLIENT_EMAIL") or values.get("GOOGLE_CLIENT_EMAIL"))
        and (os.getenv("GOOGLE_PRIVATE_KEY") or values.get("GOOGLE_PRIVATE_KEY"))
    )
    if (key_file is None or not key_file.exists()) and not has_inline_creds:
        raise FileNotFoundError(
            "Falta la ruta del JSON del service account. Define "
            "UNIOMERCATO_SERVICE_ACCOUNT_FILE o GOOGLE_APPLICATION_CREDENTIALS, "
            "o bien las variables GOOGLE_* en .env."
        )
    if not root_id:
        raise FileNotFoundError(
            "Falta UNIOMERCATO_DRIVE_FOLDER_ID con el ID de la carpeta raíz de Drive."
        )
    return DriveConfig(key_file=key_file, root_folder_id=root_id, cache_root=drive_cache_root())


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


@lru_cache(maxsize=1)
def _service_account_info() -> dict[str, Any]:
    key_file = service_account_file()
    if key_file and key_file.exists():
        return json.loads(key_file.read_text(encoding="utf-8"))

    env_path = Path(".env")
    values = dotenv_values(env_path) if env_path.exists() else {}
    required = [
        "GOOGLE_PROJECT_ID",
        "GOOGLE_PRIVATE_KEY_ID",
        "GOOGLE_PRIVATE_KEY",
        "GOOGLE_CLIENT_EMAIL",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_AUTH_URI",
        "GOOGLE_TOKEN_URI",
        "GOOGLE_AUTH_PROVIDER_CERT_URL",
        "GOOGLE_CLIENT_X509_CERT_URL",
    ]
    resolved = {key: os.getenv(key) or values.get(key) for key in required}
    if all(resolved.values()):
        private_key = str(resolved["GOOGLE_PRIVATE_KEY"]).replace("\\n", "\n")
        return {
            "type": "service_account",
            "project_id": resolved["GOOGLE_PROJECT_ID"],
            "private_key_id": resolved["GOOGLE_PRIVATE_KEY_ID"],
            "private_key": private_key,
            "client_email": resolved["GOOGLE_CLIENT_EMAIL"],
            "client_id": resolved["GOOGLE_CLIENT_ID"],
            "auth_uri": resolved["GOOGLE_AUTH_URI"],
            "token_uri": resolved["GOOGLE_TOKEN_URI"],
            "auth_provider_x509_cert_url": resolved["GOOGLE_AUTH_PROVIDER_CERT_URL"],
            "client_x509_cert_url": resolved["GOOGLE_CLIENT_X509_CERT_URL"],
        }

    raise FileNotFoundError(
        "No encuentro credenciales de Google Drive. Usa UNIOMERCATO_SERVICE_ACCOUNT_FILE "
        "o define las variables GOOGLE_* del service account en .env."
    )


@lru_cache(maxsize=1)
def _access_token() -> str:
    info = _service_account_info()
    token_uri = info.get("token_uri", "https://oauth2.googleapis.com/token")
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {
        "iss": info["client_email"],
        "scope": DRIVE_SCOPE,
        "aud": token_uri,
        "iat": now,
        "exp": now + 3600,
    }
    signing_input = f"{_b64url(json.dumps(header, separators=(',', ':')).encode())}.{_b64url(json.dumps(payload, separators=(',', ':')).encode())}"
    private_key = serialization.load_pem_private_key(info["private_key"].encode("utf-8"), password=None)
    signature = private_key.sign(signing_input.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    assertion = f"{signing_input}.{_b64url(signature)}"

    response = requests.post(
        token_uri,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        },
        timeout=30,
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("No se pudo obtener access_token para Google Drive.")
    return token


def _drive_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_access_token()}"}


def _drive_api_get(path: str, *, params: dict[str, Any] | None = None, stream: bool = False) -> requests.Response:
    url = f"https://www.googleapis.com/drive/v3{path}"
    response = requests.get(url, headers=_drive_headers(), params=params, stream=stream, timeout=60)
    response.raise_for_status()
    return response


def _list_children(folder_id: str) -> list[dict[str, Any]]:
    children: list[dict[str, Any]] = []
    page_token = None
    while True:
        params = {
            "q": f"'{folder_id}' in parents and trashed = false",
            "fields": "nextPageToken, files(id,name,mimeType,modifiedTime,md5Checksum,size)",
            "pageSize": 1000,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        if page_token:
            params["pageToken"] = page_token
        payload = _drive_api_get("/files", params=params).json()
        children.extend(payload.get("files", []))
        page_token = payload.get("nextPageToken")
        if not page_token:
            break
    return children


def _remote_timestamp(meta: dict[str, Any]) -> float:
    modified = str(meta.get("modifiedTime") or "").replace("Z", "+00:00")
    if not modified:
        return 0.0
    try:
        return datetime.fromisoformat(modified).timestamp()
    except ValueError:
        return 0.0


def _download_binary(file_id: str, destination: Path) -> None:
    with _drive_api_get(f"/files/{file_id}", params={"alt": "media", "supportsAllDrives": "true"}, stream=True) as response:
        destination.parent.mkdir(parents=True, exist_ok=True)
        tmp = destination.with_suffix(destination.suffix + ".tmp")
        with tmp.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    handle.write(chunk)
        tmp.replace(destination)


def _sync_file(meta: dict[str, Any], destination: Path) -> None:
    remote_ts = _remote_timestamp(meta)
    if destination.exists() and destination.stat().st_mtime >= remote_ts - 1:
        return
    _download_binary(str(meta["id"]), destination)
    if remote_ts > 0:
        os.utime(destination, (remote_ts, remote_ts))


def _sync_folder(folder_id: str, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for child in _list_children(folder_id):
        name = str(child.get("name") or "").strip()
        mime_type = str(child.get("mimeType") or "")
        if not name:
            continue
        child_path = destination / name
        if mime_type == FOLDER_MIME:
            _sync_folder(str(child["id"]), child_path)
            continue
        _sync_file(child, child_path)


def sync_drive_root() -> Path:
    """Mirror the configured Drive root to a local cache and return that cache path."""
    cfg = _load_config()
    cfg.cache_root.mkdir(parents=True, exist_ok=True)
    root_children = _list_children(cfg.root_folder_id)
    folder_lookup = {
        str(child.get("name") or "").strip(): child
        for child in root_children
        if child.get("mimeType") == FOLDER_MIME
    }

    missing = [name for name in DRIVE_TO_LOCAL if name not in folder_lookup]
    if missing:
        raise FileNotFoundError(
            "No se encontraron estas carpetas en el Drive raíz: "
            + ", ".join(missing)
            + ". Revisa que la carpeta compartida tenga exactamente esos nombres."
        )

    for drive_name, local_rel in DRIVE_TO_LOCAL.items():
        _sync_folder(str(folder_lookup[drive_name]["id"]), cfg.cache_root / local_rel)

    return cfg.cache_root
