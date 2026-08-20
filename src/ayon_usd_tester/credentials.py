from __future__ import annotations

import json
import platform
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=None)
def get_api_key(server_url: str, credentials_path: str = ".credentials.json") -> str:
    import ayon_api
    from ayon_api import ServerAPI

    path = Path(credentials_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Credentials file not found: {path}")

    with path.open(encoding="utf-8") as stream:
        credentials = json.load(stream)

    key = f"{platform.system().lower()}-{server_url}"
    values = credentials.get(key)
    if not values:
        raise KeyError(f"Credentials for '{key}' not found in {path}")

    username = values.get("username")
    password = values.get("password")
    if not username or not password:
        raise KeyError(f"Missing username or password for '{key}'")

    api = ServerAPI(server_url)
    try:
        api.login(username, password)
    except ayon_api.exceptions.AuthenticationError as exc:
        raise ValueError("Incorrect AYON username/password combination") from exc
    return api.access_token
