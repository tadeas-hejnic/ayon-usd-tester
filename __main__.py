import argparse
import os
import subprocess
import sys

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
    resolver_dir,
    expected_path=None,
    test_types=None,
):
    if test_types is None:
        test_types = ["resolve"]

    for test_type in test_types:
        env = utils.build_environment(
            server_url=server,
            project_name=project_name,
            machine_settings_file="path/to/machine_settings.json",
            resolver_dir=resolver_dir,
            dcc_executable=dcc_executable,
            pinning=(test_type == "pinning-resolve"),
        )
        
        usdresolve_path = utils.get_usdresolve_path(dcc_executable)

        print(_color(f"Using usdresolve: {usdresolve_path}", _CYAN))

        total_tests = 0
        failed_tests = 0

        for uri in uris:
            total_tests += 1
            command = [str(usdresolve_path), uri]
            result = subprocess.run(
                command,
                env={**os.environ, **env},
                capture_output=True,
                text=True,
                check=False,
            )

            # Keep the resolver diagnostics visible to the user.
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, end="", file=sys.stderr)

            if result.returncode != 0:
                failed_tests += 1
                raise subprocess.CalledProcessError(
                    result.returncode,
                    command,
                    output=result.stdout,
                    stderr=result.stderr,
                )

            if expected_path:
                # usdresolve prints the resolved filesystem path after its
                # diagnostics, for example:
                # /home/ynput/ayon_projects/TestProject/.../file.usd
                output_lines = [
                    line.strip()
                    for line in result.stdout.splitlines()
                    if line.strip()
                ]
                if not output_lines:
                    failed_tests += 1
                    raise RuntimeError(
                    "usdresolve returned no resolved path to compare"
                    )

                actual_path = output_lines[-1]

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
                    raise AssertionError(message)

                print(
                    _color(
                    f"Resolved path matches expected path: {expected_path}",
                    _GREEN,
                    )
                )

        print(
            _color(
            f"Testing completed. Total tests: {total_tests}, Failed tests: {failed_tests}",
            _CYAN,
            )
        )


def main():
    """Main entry point of the application."""
    args = parse_arguments()

    dcc_config = utils.get_dcc_config(args.dcc_config)

    uris = utils.get_uris(args.uri_file)

    for dcc_name, dcc_versions in dcc_config.items():
        if args.dcc != "ALL" and args.dcc != dcc_name:
            continue
        for version, version_config in dcc_versions.items():
            if args.version != "ALL" and args.version != version:
                continue
            print(f"Running tests for {dcc_name} version {version}")
            run_resolve_test(
                server=args.server,
                project_name=args.project,
                uris=uris if uris else args.uri,
                dcc_executable=version_config["executable"],
                resolver_dir=version_config["resolver_dir"],
                expected_path=args.expected_path,
                test_types=args.test_type
            )

    # # Run tests
    # run_resolve_test(args.server, args.project, args.dcc, args.version)


if __name__ == "__main__":
    main()
