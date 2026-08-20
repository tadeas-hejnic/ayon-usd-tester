from __future__ import annotations

import os
from pathlib import Path

from .models import DccInstallation


def usdresolve_path(installation: DccInstallation) -> Path:
    executable_name = "usdresolve.exe" if os.name == "nt" else "usdresolve"
    if installation.name.casefold() == "houdini":
        path = installation.executable.parent / executable_name
    elif installation.name.casefold() == "maya":
        if installation.usd_root is None:
            raise ValueError("Maya requires 'usd_root' in the DCC configuration")
        path = installation.usd_root / "bin" / executable_name
    else:
        raise ValueError(f"Unsupported DCC type: {installation.name}")

    if not path.is_file():
        raise FileNotFoundError(f"usdresolve was not found for {installation.name}: {path}")
    return path


def python_executable(installation: DccInstallation) -> Path:
    executable_name = {
        "houdini": "hython.exe" if os.name == "nt" else "hython",
        "maya": "mayapy.exe" if os.name == "nt" else "mayapy",
    }.get(installation.name.casefold())
    if executable_name is None:
        raise ValueError(f"Unsupported DCC type for Python test: {installation.name}")
    path = installation.executable.parent / executable_name
    if not path.is_file():
        raise FileNotFoundError(f"DCC Python executable was not found: {path}")
    return path
