import argparse
import os
import subprocess
import sys
from pathlib import Path

from stats_creator import StatsCreator

import utils


_RESET = "\033[0m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_CYAN = "\033[36m"


def _color(text, color):
    """Color terminal output without adding escape codes to redirected logs."""
    if sys.stdout.isatty() or os.environ.get("FORCE_COLOR"):
        return f"{color}{text}{_RESET}"
    return text


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="A CLI application for testing DCCs.")
    parser.add_argument(
        "--server", 
        type=str, 
        help="Server URL(s) to test against (e.g., http://localhost:5000)",
        required=True
    )
    parser.add_argument(
        "--project", 
        type=str, 
        help="Project name",
        required=True
    )
    parser.add_argument(
        "--uri", 
        type=str, 
        help="AYON URI to test (e.g., ayon://project/asset/scene.usd)",
        default=None
    )
    parser.add_argument(
        "--uri-file",
        type=str,
        help="Path to a file containing AYON URIs to test (one per line)",
        default=None
    )
    parser.add_argument(
        "--dcc", 
        type=str, 
        help="DCC name (e.g., Maya, Houdini, or ALL)", 
        default="ALL"
    )
    parser.add_argument(
        "--version", 
        type=str, 
        help="DCC version (e.g., specific version or ALL)", 
        default="ALL"
    )
    parser.add_argument(
        "--dcc-config",
        type=str,
        help="Path to the DCC configuration file",
        default=None
    )
    parser.add_argument(
        "--test-type", 
        type=str,
        nargs="+", 
        help="Test type(s) to run (e.g., resolve, pinning-resolve, or all)", 
        default=["resolve"]
    )
    parser.add_argument(
        "--expected-path",
        "--expected",
        dest="expected_path",
        help="Expected path printed by usdresolve",
        default=None,
    )
    parser.add_argument(
        "--resolver-log-file",
        help="Write resolver stdout/stderr to this file instead of the terminal",
        default=None,
    )
    return parser.parse_args()


def fetch_ayon_uri():
    """Fetch AYON URI from a file (placeholder implementation)."""
    # Replace this with actual logic to fetch AYON URI from a file
    return "file://path/to/ayon"


def run_resolve_test(
    server,
    project_name,
    uris,
    dcc_executable,
    usdresolve_path,
    resolver_dir,
    dcc_type,
    usd_root=None,
    resolver_log_file=None,
    test_types=None,
):
    if test_types is None:
        test_types = ["resolve"]

    total_tests = 0
    failed_tests = 0

    for test_type in test_types:
        env = utils.build_environment(
            server_url=server,
            project_name=project_name,
            machine_settings_file=str(Path(__file__).parent / "settings" / "machine_settings.json"),
            resolver_dir=resolver_dir,
            dcc_executable=dcc_executable,
            usd_root=usd_root,
            pinning=(test_type == "pinning-resolve"),
        )

        print(_color(f"Using usdresolve: {usdresolve_path}", _CYAN))
        if resolver_log_file:
            log_path = Path(resolver_log_file).expanduser()
            log_path.parent.mkdir(parents=True, exist_ok=True)
            print(_color(f"Resolver output: {log_path}", _CYAN))

        for uri, expected_path in uris.items():
            total_tests += 1
            command = [str(usdresolve_path), uri]
            if dcc_type.lower() == "maya":
                dcc_path = Path(dcc_executable).expanduser().resolve()
                mayapy_path = dcc_path.parent / "mayapy"
                if not mayapy_path.is_file():
                    raise FileNotFoundError(
                        f"Maya Python executable was not found: {mayapy_path}"
                    )
                command.insert(0, str(mayapy_path))
            result = subprocess.run(
                command,
                env={**os.environ, **env},
                capture_output=True,
                text=True,
                check=False,
            )

            if resolver_log_file:
                with log_path.open("a", encoding="utf-8") as log_stream:
                    log_stream.write(
                        f"\n=== {dcc_type} {usdresolve_path} ===\n"
                        f"URI: {uri}\n"
                    )
                    if result.stdout:
                        log_stream.write(result.stdout)
                    if result.stderr:
                        log_stream.write(result.stderr)
                    log_stream.write("\n")
            else:
                # Keep resolver diagnostics visible unless a log file was
                # explicitly requested.
                if result.stdout:
                    print(result.stdout, end="")
                if result.stderr:
                    print(result.stderr, end="", file=sys.stderr)

            if result.returncode != 0:
                failed_tests += 1
                error = subprocess.CalledProcessError(
                    result.returncode,
                    command,
                    output=result.stdout,
                    stderr=result.stderr,
                )
                print(_color(f"Test failed: {error}", _RED), file=sys.stderr)
                continue

            # usdresolve prints the resolved filesystem path after its
            # diagnostics, for example:
            # /home/ynput/ayon_projects/TestProject/.../file.usd
            output_lines = [
                line.strip()
                for line in result.stdout.splitlines()
                if line.strip()
            ]
            if not output_lines:
                if expected_path:
                    failed_tests += 1
                    print(
                        _color(
                            "Test failed: usdresolve returned no resolved path",
                            _RED,
                        ),
                        file=sys.stderr,
                    )
                continue

            actual_path = output_lines[-1]
            print(
                _color(
                    f"Resolved {uri} to {actual_path}",
                    _GREEN,
                )
            )

            if expected_path:
                def normalize_path(path_value):
                    return os.path.normcase(
                    os.path.realpath(os.path.expanduser(path_value))
                    )

                if normalize_path(actual_path) != normalize_path(expected_path):
                    failed_tests += 1
                    message = (
                    "Resolved path does not match expected path:\n"
                    f"  expected: {expected_path}\n"
                    f"  actual:   {actual_path}"
                    )
                    print(_color(message, _RED), file=sys.stderr)
                    continue

                print(
                    _color(
                    f"Resolved path matches expected path: {expected_path}",
                    _GREEN,
                    )
                )

    return total_tests, failed_tests


def main():
    """Main entry point of the application."""
    args = parse_arguments()

    dcc_config = utils.get_dcc_config(args.dcc_config)

    uris = utils.get_uris_from_file(args.uri_file)
    stats = StatsCreator()

    for dcc_name, dcc_versions in dcc_config.items():
        if args.dcc != "ALL" and args.dcc != dcc_name:
            continue
        for version, version_config in dcc_versions.items():
            if args.version != "ALL" and args.version != version:
                continue
            print(f"Running tests for {dcc_name} version {version}")

            usd_root = version_config.get("usd_root")
            if not usd_root and dcc_name.lower() == "maya":
                # Useful for a one-off Maya test; per-version configuration
                # is preferred when several Maya installations are tested.
                usd_root = os.environ.get("USD_ROOT")
            usdresolve_path = utils.get_usdresolve_path(
                version_config["executable"],
                dcc_name,
                usd_root=usd_root,
            )

            total_tests, failed_tests = run_resolve_test(
                server=args.server,
                project_name=args.project,
                uris=uris if uris else {args.uri: args.expected_path},
                dcc_executable=version_config["executable"],
                usdresolve_path=usdresolve_path,
                resolver_dir=version_config["resolver_dir"],
                dcc_type=dcc_name,
                usd_root=usd_root,
                resolver_log_file=args.resolver_log_file,
                test_types=args.test_type
            )
            stats.update(dcc_name, version, total_tests, failed_tests)

    summary_color = _RED if stats.failed_tests else _GREEN
    print(_color(str(stats), summary_color))

    if stats.failed_tests:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
