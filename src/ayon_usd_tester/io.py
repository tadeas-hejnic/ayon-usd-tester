from __future__ import annotations

import json
from pathlib import Path

from .models import TestCase


def load_cases(uri: str | None, uri_file: str | Path | None, expected_path: str | None) -> list[TestCase]:
    if uri_file:
        path = Path(uri_file).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"URI file not found: {path}")
        with path.open(encoding="utf-8") as stream:
            values = json.load(stream)
        if not isinstance(values, dict):
            raise TypeError(f"Expected a JSON object in URI file: {path}")
        return [TestCase(uri=key, expected_path=value) for key, value in values.items()]
    if uri:
        return [TestCase(uri=uri, expected_path=expected_path)]
    raise ValueError("Provide either --uri or --uri-file")
