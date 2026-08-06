from __future__ import annotations

import json
import os
from pathlib import Path

from ayon_api import ServerAPI
from ayon_usd import utils as ayon_usd_utils


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
    credentials_path = os.path.expanduser("~/.credentials.json")
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Credentials file not found at {credentials_path}")

    with open(credentials_path, "r") as f:
        credentials = json.load(f)

    platform = os.name
    key = f"{platform}-{server_url}"

    if key not in credentials:
        raise KeyError(f"Credentials for '{key}' not found in the file")

    username = credentials[key].get("username")
    password = credentials[key].get("password")

    if not username or not password:
        raise KeyError(f"Missing 'username' or 'password' for '{key}'")

    api = ServerAPI(server_url)
    if not api.login(username, password):
        raise ValueError("Login failed. Please check your credentials.")

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
    pinning: bool = False,
):
    machine_specific_vars = get_machine_specific_veriables(machine_settings_file)    
    
    # Prepare environment variables in a dictionary
    env_vars = {
        "AYON_SERVER_URL": server_url,
        "AYON_PROJECT_NAME": project_name,
        "AYON_SITE_ID": "little-urban-cow",
        "AYON_API_KEY": get_ayon_api_key(server_url),
    }

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

    resolver_env = ayon_usd_utils.get_resolver_setup_info(resolver_dir, settings)

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
    
    platform = os.name
    if platform not in dcc_config:
        raise KeyError(f"Platform '{platform}' not found in the DCC configuration file")

    return dcc_config[platform]


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
