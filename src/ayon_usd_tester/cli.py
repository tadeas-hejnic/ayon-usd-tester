from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import DccConfig
from .io import load_cases
from .models import TestCase
from .reporting import format_report
from .runner import TestRunner


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AYON USD Resolver smoke tests.")
    parser.add_argument("--server", required=True, help="AYON server URL")
    parser.add_argument("--project", required=True, help="AYON project name")
    uri_group = parser.add_mutually_exclusive_group(required=True)
    uri_group.add_argument("--uri", help="AYON URI to test")
    uri_group.add_argument("--uri-file", help="JSON object mapping URIs to expected paths")
    parser.add_argument("--dcc", default="ALL", help="DCC name or ALL")
    parser.add_argument("--version", default="ALL", help="DCC version or ALL")
    parser.add_argument("--dcc-config", default=str(Path(__file__).resolve().parents[2] / "settings" / "dcc_setup.json"))
    parser.add_argument("--machine-settings", help="Optional machine-specific settings JSON")
    parser.add_argument("--test-type", nargs="+", default=["resolve"], choices=("resolve", "pinning-resolve", "python", "all"))
    parser.add_argument("--expected-path", "--expected", dest="expected_path")
    parser.add_argument("--resolver-log-file", help="Append resolver output to this file")
    parser.add_argument("--timeout", type=int, default=300, help="Subprocess timeout in seconds")
    return parser.parse_args(argv)


def _test_cases(args: argparse.Namespace) -> list[TestCase]:
    base_cases = load_cases(args.uri, args.uri_file, args.expected_path)
    test_types = {value.casefold() for value in args.test_type}
    if "all" in test_types:
        test_types = {"resolve", "pinning-resolve", "python"}
    cases = []
    if "resolve" in test_types:
        cases.extend(base_cases)
    if "pinning-resolve" in test_types:
        cases.extend(TestCase(case.uri, test_type="pinning-resolve") for case in base_cases)
    if "python" in test_types:
        cases.append(TestCase(uri="python-smoke-test", test_type="python"))
    return cases


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    config = DccConfig.load(args.dcc_config)
    installations = config.select(args.dcc, args.version)
    cases = _test_cases(args)
    runner = TestRunner(args.server, args.project, machine_settings_file=args.machine_settings, resolver_log_file=args.resolver_log_file, timeout=args.timeout)

    results_by_installation = {}
    failed_results = []
    for installation in installations:
        print(f"Running tests for {installation.name} {installation.version}")
        results = runner.run(installation, cases)
        results_by_installation[(installation.name, installation.version)] = results
        failed_results.extend(result for result in results if not result.passed)
        for result in results:
            message = f"{result.case.test_type}: {result.case.uri}"
            if result.passed:
                print(f"PASS {message}")
            else:
                print(f"FAIL {message} ({result.error})", file=sys.stderr)

    print(format_report(results_by_installation))
    return 1 if failed_results else 0


if __name__ == "__main__":
    raise SystemExit(main())
