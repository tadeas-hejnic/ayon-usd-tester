import argparse
import os
import subprocess

import utils


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="A CLI application for testing DCCs.")
    parser.add_argument(
        "--server", 
        type=str, 
        nargs="+", 
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
        required=True
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
    return parser.parse_args()


def fetch_ayon_uri():
    """Fetch AYON URI from a file (placeholder implementation)."""
    # Replace this with actual logic to fetch AYON URI from a file
    return "file://path/to/ayon"


def run_resolve_test(
    server,
    project_name,
    uri,
    dcc_executable,
    test_types=None,
):
    if test_types is None:
        test_types = ["resolve"]

    for test_type in test_types:
        env = utils.build_environment(
            server_url=server,
            project_name=project_name,
            machine_settings_file="path/to/machine_settings.json",
            resolver_dir="path/to/resolver_dir",
            pinning=(test_type == "pinning-resolve"),
        )

        usdresolve_path = utils.get_usdresolve_path(dcc_executable)

        print(f"Using usdresolve: {usdresolve_path}")

        subprocess.run(
            [str(usdresolve_path), uri],
            env={**os.environ, **env},
            check=True,
        )


def main():
    """Main entry point of the application."""
    args = parse_arguments()

    dcc_config = utils.get_dcc_config(args.dcc_config)

    for dcc_name, dcc_versions in dcc_config.items():
        if args.dcc != "ALL" and args.dcc != dcc_name:
            continue
        for version in dcc_versions:
            if args.version != "ALL" and args.version != version:
                continue
            print(f"Running tests for {dcc_name} version {version}")
            run_resolve_test(
                server=args.server,
                project=args.project,
                uri=args.uri,
                dcc_executable=version["executable"],
                test_types=args.test_type
            )

    # Run tests
    run_resolve_test(args.server, args.project, args.dcc, args.version)


if __name__ == "__main__":
    main()
