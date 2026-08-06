"""Shared constants for the AYON USD Resolver test runner.

This follows the AYON Python API convention of keeping immutable literals in a
dedicated ``constants.py`` module and naming them in uppercase.
"""

# Files and executable names
CREDENTIALS_FILE_NAME = ".credentials.json"
HOUDINI_SETUP_FILE_NAME = "houdini_setup"
USDRESOLVE_EXECUTABLE_NAME = "usdresolve"
RESOLVER_PACKAGE_DIR_NAME = "ayonUsdResolver"
RESOLVER_RESOURCES_DIR_NAME = "resources"
RESOLVER_LIBRARY_DIR_NAME = "lib"
RESOLVER_PLUGIN_INFO_FILE_NAME = "plugInfo.json"
RESOLVER_LIBRARY_FILE_NAME = "ayonUsdResolver.so"
RESOLVER_WINDOWS_LIBRARY_FILE_NAME = "ayonUsdResolver.dll"

# Default values
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FILE_ENABLED = "ON"

# Environment variable
MACHINE_SPECIFIC_REQUIRED_VARS = [
    "AYON_USD_RESOLVER_LOG_FILE",
]
