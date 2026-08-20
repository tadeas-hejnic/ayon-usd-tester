from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DccInstallation:
    name: str
    version: str
    executable: Path
    resolver_dir: Path
    usd_root: Path | None = None


@dataclass(frozen=True)
class TestCase:
    uri: str
    expected_path: str | None = None
    test_type: str = "resolve"


@dataclass(frozen=True)
class TestResult:
    case: TestCase
    passed: bool
    actual_path: str | None = None
    return_code: int = 0
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
