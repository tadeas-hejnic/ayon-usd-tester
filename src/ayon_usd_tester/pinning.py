from __future__ import annotations

import json
from pathlib import Path

from .models import TestCase


def cases_from_pinning_file(path: str | Path, cases: list[TestCase]) -> list[TestCase]:
    pinning_path = Path(path).expanduser()
    if not pinning_path.is_file():
        raise FileNotFoundError(f"Pinning file not found: {pinning_path}")

    with pinning_path.open(encoding="utf-8") as stream:
        data = json.load(stream)

    try:
        pinning_data = data["ayon_resolver_pinning_data"]
    except (KeyError, TypeError) as exc:
        raise ValueError(
            f"Pinning file has no 'ayon_resolver_pinning_data': {pinning_path}"
        ) from exc

    if not isinstance(pinning_data, dict):
        raise TypeError(f"Expected an object in pinning file: {pinning_path}")

    return [
        TestCase(
            uri=case.uri,
            expected_path=pinning_data.get(case.uri, ""),
            test_type="pinning-resolve",
        )
        for case in cases
    ]
