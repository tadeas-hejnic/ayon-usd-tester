from __future__ import annotations

import json
import os
import platform
from pathlib import Path

from ayon_api import ServerAPI

from constants import CREDENTIALS_FILE_NAME


def get_ayon_api_key(server_url: str) -> str:
    """
    Retrieve the AYON API key by logging in with credentials stored in a JSON file.

    Args:
        server_url (str): The URL of the AYON server.

    Returns:
        str: The API access token.

    Raises:
        FileNotFoundError: If the credentials file is not found.
        KeyError: If the required credentials are missing in the file.
        ValueError: If the login fails.
    """
    credentials_path = os.path.expanduser(CREDENTIALS_FILE_NAME)
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Credentials file not found at {credentials_path}")

    with open(credentials_path, "r") as f:
        credentials = json.load(f)

    system_platform = platform.system().lower()
    key = f"{system_platform}-{server_url}"
    print(key)

    if key not in credentials:
        raise KeyError(f"Credentials for '{key}' not found in the file")

    username = credentials[key].get("username")
    password = credentials[key].get("password")

    if not username or not password:
        raise KeyError(f"Missing 'username' or 'password' for '{key}'")

    print(username, password, server_url)
    api = ServerAPI(server_url)

    try:
        api.login(username, password)
    except ayon_api.exceptions.AuthenticationError:
        raise ValueError("Incorrect username/password combination...")
    
    return api.access_token


def get_machine_specific_veriables(machine_settings_file: str) -> dict:
    """
    Load machine settings from a JSON file and set them.

    Args:
        machine_settings_file (str): Path to the machine settings JSON file.
    """
    if not os.path.exists(machine_settings_file):
        raise FileNotFoundError(f"Machine settings file not found at {machine_settings_file}")

    with open(machine_settings_file, "r") as f:
        machine_settings = json.load(f)

    return machine_settings


def build_environment(
    server_url: str,
    project_name: str,
    machine_settings_file: str,
    resolver_dir: str,
    dcc_executable: str | None = None,
    pinning: bool = False,
):
    try:
        machine_specific_vars = get_machine_specific_veriables(machine_settings_file)    
    except FileNotFoundError as e:
        machine_specific_vars = {}
        print(f"Warning: {e}. Proceeding without machine-specific variables.")

    # Prepare environment variables in a dictionary
    env_vars = {
        "AYON_SERVER_URL": server_url,
        "AYON_PROJECT_NAME": project_name,
        "AYON_SITE_ID": "little-urban-cow",
        "AYON_API_KEY": get_ayon_api_key(server_url),
    }

    # usdresolve is a Houdini launcher. It invokes ``hython`` through
    # ``/usr/bin/env``, so Houdini's bin directory must be on PATH in the
    # child process. The Houdini root is also needed by Houdini itself.
    if dcc_executable:
        houdini_executable = Path(dcc_executable).expanduser().resolve()
        houdini_bin = houdini_executable.parent
        env_vars["HFS"] = str(houdini_bin.parent)
        env_vars["PATH"] = os.pathsep.join(
            value for value in (str(houdini_bin), os.environ.get("PATH", ""))
            if value
        )

    if not pinning:
        env_vars.pop("AYON_USD_RESOLVER_ENABLE_PINNING", None)
        env_vars.pop("AYON_USD_RESOLVER_PINNING_FILE", None)
        env_vars.pop("AYON_USD_RESOLVER_PINNING_ROOTS", None)
    else:
        env_vars["AYON_USD_RESOLVER_ENABLE_PINNING"] = "1"
        env_vars["AYON_USD_RESOLVER_PINNING_FILE"] = machine_specific_vars["AYON_USD_RESOLVER_PINNING_FILE"]
        env_vars["AYON_USD_RESOLVER_PINNING_ROOTS"] = machine_specific_vars.get("AYON_USD_RESOLVER_PINNING_ROOTS", "")

        if not os.path.exists(env_vars["AYON_USD_RESOLVER_PINNING_FILE"]):
            raise FileNotFoundError(f"Pinning file not found at {env_vars['AYON_USD_RESOLVER_PINNING_FILE']}")
        if not env_vars["AYON_USD_RESOLVER_PINNING_ROOTS"]:
            print("AYON_USD_RESOLVER_PINNING_ROOTS is not set in the machine settings file")

    settings = {
        "usd" : {
            "ayon_usd_resolver": {
                "ayon_log_lvl": "INFO",
                "ayon_file_logger_enabled": "ON",
                "file_logger_file_path": machine_specific_vars.get("AYON_USD_RESOLVER_LOG_FILE", ""),
                "ayon_logger_logging_keys": "AYONUSDRESOLVER_RESOLVER,AYONUSDRESOLVER_RESOLVER_CONTEXT",
            },
            "usd": {
                "usd_tf_debug": "AYON* PLUG* AYONUSDRESOLVER*",
            },
        }
    }

    # copy from ayon-usd to avoid the dependency on the package itself
    # as we want to run this test without installing the package
    def get_resolver_setup_info(
            resolver_dir,
            settings,
            env=None) -> dict:
        """Get the environment variables to load AYON USD setup.

        Arguments:
            resolver_dir (str): Directory of the resolver.
            settings (dict[str, Any]): Studio settings.
            env (dict[str, str]): Source environment to build on.

        Returns:
            dict[str, str]: The environment needed to load AYON USD correctly.
        """

        resolver_root = Path(resolver_dir) / "ayonUsdResolver"
        resolver_plugin_info_path = resolver_root / "resources" / "plugInfo.json"
        resolver_ld_path = resolver_root / "lib"
        resolver_python_path = resolver_root / "lib" / "python"

        if (
            not os.path.exists(resolver_python_path)
            or not os.path.exists(resolver_ld_path)
        ):
            raise RuntimeError(
                f"Cant start Resolver missing path "
                f"resolver_python_path: {resolver_python_path}, "
                f"resolver_ld_path: {resolver_ld_path}"
            )

        def _append(_env: dict, key: str, path: str):
            """Add path to key in env"""
            current: str = _env.get(key)
            if current:
                return os.pathsep.join([current, path])
            return path

        ld_path_key = "LD_LIBRARY_PATH"
        if platform.system().lower() == "windows":
            ld_path_key = "PATH"

        pxr_pluginpath_name = _append(
            env, "PXR_PLUGINPATH_NAME", resolver_plugin_info_path.as_posix()
        )
        ld_library_path = _append(
            env, ld_path_key, resolver_ld_path.as_posix()
        )
        python_path = _append(
            env, "PYTHONPATH", resolver_python_path.as_posix()
        )

        resolver_settings = settings["usd"]["ayon_usd_resolver"]
        return {
            "TF_DEBUG": settings["usd"]["usd"]["usd_tf_debug"],
            "AYON_USD_RESOLVER_LOG_LVL": resolver_settings["ayon_log_lvl"],
            "AYON_USD_RESOLVER_LOG_FILE_ENABLED": resolver_settings["ayon_file_logger_enabled"],  # noqa
            "AYON_USD_RESOLVER_LOG_FILE": resolver_settings["file_logger_file_path"],
            "AYON_USD_RESOLVER_LOGGING_KEYS": resolver_settings["ayon_logger_logging_keys"],  # noqa
            "PXR_PLUGINPATH_NAME": pxr_pluginpath_name,
            "PYTHONPATH": python_path,
            ld_path_key: ld_library_path,
            # Backwards compatibility (deprecated)
            "AYONLOGGERLOGLVL": resolver_settings["ayon_log_lvl"],
            "AYONLOGGERFILELOGGING": resolver_settings["ayon_file_logger_enabled"],
            "AYONLOGGERFILEPOS": resolver_settings["file_logger_file_path"],
            "AYON_LOGGIN_LOGGIN_KEYS": resolver_settings["ayon_logger_logging_keys"],
        }

    resolver_env = get_resolver_setup_info(resolver_dir, settings, {})

    return {**env_vars, **resolver_env}


def get_dcc_config(dcc_config_path: str | None) -> dict:
    """
    Load DCC configuration from a JSON file.

    Args:
        dcc_config_path (str | None): Path to the DCC configuration JSON file.
    """
    if dcc_config_path is None:
        return {}

    if not os.path.exists(dcc_config_path):
        raise FileNotFoundError(f"DCC configuration file not found at {dcc_config_path}")

    with open(dcc_config_path, "r") as f:
        dcc_config = json.load(f)
    
    system_platform = platform.system().lower()
    if system_platform not in dcc_config:
        raise KeyError(f"Platform '{system_platform}' not found in the DCC configuration file `{dcc_config_path}`")

    return dcc_config[system_platform]


def get_usdresolve_path(dcc_executable: str) -> Path:
    houdini_executable = Path(dcc_executable).expanduser().resolve()

    executable_name = "usdresolve.exe" if os.name == "nt" else "usdresolve"
    usdresolve_path = houdini_executable.parent / executable_name

    if not usdresolve_path.is_file():
        raise FileNotFoundError(
            f"usdresolve was not found next to Houdini executable: "
            f"{usdresolve_path}"
        )

    return usdresolve_path


def get_uris(uri_file_path: str | None) -> dict[str, str]:
    """
    Load URIs and their expected resolved paths from a JSON file.

    Args:
        uri_file_path (str | None): Path to the JSON file containing URIs and resolved paths.

    Returns:
        dict[str, str]: A dictionary where keys are URIs and values are the expected resolved paths.
    """
    if uri_file_path is None:
        return {}

    if not os.path.exists(uri_file_path):
        raise FileNotFoundError(f"URI file not found at {uri_file_path}")

    with open(uri_file_path, "r") as f:
        uris = json.load(f)

    if not isinstance(uris, dict):
        raise TypeError(f"Expected a JSON object in the file {uri_file_path}")

    return uris
