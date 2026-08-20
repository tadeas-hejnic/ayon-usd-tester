from __future__ import annotations

import json
import os
import platform
from pathlib import Path

from . import credentials


def _prepend_path(environment: dict[str, str], key: str, value: Path) -> None:
    current = environment.get(key) or os.environ.get(key, "")
    environment[key] = os.pathsep.join(part for part in (str(value), current) if part)


def _load_machine_settings(path: str | Path | None) -> dict[str, str]:
    if path is None:
        return {}
    settings_path = Path(path).expanduser()
    if not settings_path.is_file():
        print(f"Warning: machine settings file not found: {settings_path}")
        return {}
    with settings_path.open(encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise TypeError(f"Expected an object in machine settings file: {settings_path}")
    return data


def build_environment(
    server_url: str,
    project_name: str,
    resolver_dir: str | Path,
    *,
    dcc_executable: str | Path | None = None,
    usd_root: str | Path | None = None,
    machine_settings_file: str | Path | None = None,
    pinning: bool = False,
) -> dict[str, str]:
    machine = _load_machine_settings(machine_settings_file)
    api_key = os.environ.get("AYON_API_KEY") or credentials.get_api_key(server_url)
    environment = {
        "AYON_SERVER_URL": server_url,
        "AYON_PROJECT_NAME": project_name,
        "AYON_SITE_ID": "little-urban-cow",
        "AYON_API_KEY": api_key,
    }

    if dcc_executable:
        executable = Path(dcc_executable).expanduser().resolve()
        houdini_bin = executable.parent
        environment["HFS"] = str(houdini_bin.parent)
        _prepend_path(environment, "PATH", houdini_bin)

    if usd_root:
        root = Path(usd_root).expanduser().resolve()
        python_root = root / "lib" / "python"
        library_root = root / "lib"
        if not python_root.is_dir() or not library_root.is_dir():
            raise FileNotFoundError(f"Invalid USD_ROOT: expected lib and lib/python under {root}")
        environment["USD_ROOT"] = str(root)
        _prepend_path(environment, "PYTHONPATH", python_root)
        _prepend_path(environment, "LD_LIBRARY_PATH", library_root)

    if pinning:
        pinning_file = machine.get("AYON_USD_RESOLVER_PINNING_FILE")
        if not pinning_file:
            raise KeyError("AYON_USD_RESOLVER_PINNING_FILE is required for pinning tests")
        if not Path(pinning_file).expanduser().is_file():
            raise FileNotFoundError(f"Pinning file not found: {pinning_file}")
        environment.update(
            AYON_USD_RESOLVER_ENABLE_PINNING="1",
            AYON_USD_RESOLVER_PINNING_FILE=pinning_file,
            AYON_USD_RESOLVER_PINNING_ROOTS=machine.get(
                "AYON_USD_RESOLVER_PINNING_ROOTS", ""
            ),
        )

    resolver_root = Path(resolver_dir).expanduser() / "ayonUsdResolver"
    resolver_lib = resolver_root / "lib"
    resolver_python = resolver_lib / "python"
    plugin_info = resolver_root / "resources" / "plugInfo.json"
    if not resolver_lib.is_dir() or not resolver_python.is_dir():
        raise RuntimeError(f"Resolver installation is missing lib paths: {resolver_root}")

    resolver_settings = {
        "AYON_USD_RESOLVER_LOG_LVL": "ERROR",
        "AYON_USD_RESOLVER_LOG_FILE_ENABLED": "ON",
        "AYON_USD_RESOLVER_LOG_FILE": machine.get("AYON_USD_RESOLVER_LOG_FILE", ""),
        "AYON_USD_RESOLVER_LOGGING_KEYS": (
            "AYONUSDRESOLVER_RESOLVER,AYONUSDRESOLVER_RESOLVER_CONTEXT"
        ),
        "TF_DEBUG": "",
    }
    environment.update(resolver_settings)
    _prepend_path(environment, "PXR_PLUGINPATH_NAME", plugin_info)
    path_key = "PATH" if platform.system().lower() == "windows" else "LD_LIBRARY_PATH"
    _prepend_path(environment, path_key, resolver_lib)
    _prepend_path(environment, "PYTHONPATH", resolver_python)

    # Resolver compatibility variables used by older builds.
    environment.update(
        AYONLOGGERLOGLVL="ERROR",
        AYONLOGGERFILELOGGING="ON",
        AYONLOGGERFILEPOS=resolver_settings["AYON_USD_RESOLVER_LOG_FILE"],
        AYON_LOGGIN_LOGGIN_KEYS=resolver_settings["AYON_USD_RESOLVER_LOGGING_KEYS"],
    )
    return environment
