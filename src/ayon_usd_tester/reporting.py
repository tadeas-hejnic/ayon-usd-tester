from __future__ import annotations

from collections import defaultdict

from .models import TestResult


def format_report(results_by_installation: dict[tuple[str, str], list[TestResult]]) -> str:
    rows = []
    total = failed = 0
    for (dcc_name, version), results in results_by_installation.items():
        count = len(results)
        failures = sum(not result.passed for result in results)
        total += count
        failed += failures
        rows.append((dcc_name, version, str(count), str(failures)))
    rows.append(("Overall", "-", str(total), str(failed)))

    headers = ("Application", "Version", "Total", "Failed")
    widths = [max(len(header), *(len(row[i]) for row in rows)) for i, header in enumerate(headers)]
    separator = "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    def format_row(row):
        return "| " + " | ".join(value.ljust(width) for value, width in zip(row, widths)) + " |"

    return "\n".join(
        ["Resolver test summary", separator, format_row(headers), separator]
        + [format_row(row) for row in rows]
        + [separator]
    )
