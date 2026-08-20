from __future__ import annotations

import json
import platform
from pathlib import Path

from .models import DccInstallation


class ConfigurationError(ValueError):
    """Raised when the DCC configuration is invalid or cannot be selected."""


class DccConfig:
    def __init__(self, installations: list[DccInstallation]):
        self.installations = installations

    @classmethod
    def load(cls, path: str | Path) -> "DccConfig":
        config_path = Path(path).expanduser()
        if not config_path.is_file():
            raise FileNotFoundError(f"DCC configuration file not found: {config_path}")

        with config_path.open(encoding="utf-8") as stream:
            data = json.load(stream)

        platform_name = platform.system().lower()
        try:
            platform_config = data[platform_name]
        except (KeyError, TypeError) as exc:
            raise ConfigurationError(
                f"Platform '{platform_name}' is missing from {config_path}"
            ) from exc

        installations = []
        for dcc_name, versions in platform_config.items():
            for version, values in versions.items():
                try:
                    executable = Path(values["executable"]).expanduser()
                    resolver_dir = Path(values["resolver_dir"]).expanduser()
                except (KeyError, TypeError) as exc:
                    raise ConfigurationError(
                        f"Invalid configuration for {dcc_name} {version}"
                    ) from exc

                usd_root = values.get("usd_root")
                installations.append(
                    DccInstallation(
                        name=dcc_name,
                        version=str(version),
                        executable=executable,
                        resolver_dir=resolver_dir,
                        usd_root=Path(usd_root).expanduser() if usd_root else None,
                    )
                )

        return cls(installations)

    def select(self, dcc: str = "ALL", version: str = "ALL") -> list[DccInstallation]:
        dcc_filter = dcc.casefold()
        version_filter = version.casefold()
        selected = [
            installation
            for installation in self.installations
            if (dcc_filter == "all" or installation.name.casefold() == dcc_filter)
            and (version_filter == "all" or installation.version.casefold() == version_filter)
        ]
        if not selected:
            raise ConfigurationError(
                f"No DCC installations match dcc={dcc!r}, version={version!r}"
            )
        return selected
