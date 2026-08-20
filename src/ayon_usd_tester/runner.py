from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from . import dcc
from .environment import build_environment
from .models import DccInstallation, TestCase, TestResult
from .pinning import cases_from_pinning_file


class TestRunner:
    def __init__(
        self,
        server_url: str,
        project_name: str,
        *,
        machine_settings_file: str | Path | None = None,
        resolver_log_file: str | Path | None = None,
        timeout: int = 300,
    ):
        self.server_url = server_url
        self.project_name = project_name
        self.machine_settings_file = machine_settings_file
        self.resolver_log_file = Path(resolver_log_file).expanduser() if resolver_log_file else None
        self.timeout = timeout

    def run(self, installation: DccInstallation, cases: list[TestCase]) -> list[TestResult]:
        resolve_cases = [case for case in cases if case.test_type == "resolve"]
        pinning_cases = [case for case in cases if case.test_type == "pinning-resolve"]
        results = []
        if resolve_cases:
            results.extend(self._run_resolve(installation, resolve_cases, pinning=False))
        if pinning_cases:
            results.extend(self._run_pinning(installation, pinning_cases))
        if any(case.test_type == "python" for case in cases):
            results.append(self._run_python(installation))
        return results

    def _environment(self, installation: DccInstallation, pinning: bool) -> dict[str, str]:
        return build_environment(
            self.server_url,
            self.project_name,
            installation.resolver_dir,
            dcc_executable=installation.executable,
            usd_root=installation.usd_root,
            machine_settings_file=self.machine_settings_file,
            pinning=pinning,
        )

    def _run_pinning(
        self, installation: DccInstallation, cases: list[TestCase]
    ) -> list[TestResult]:
        environment = self._environment(installation, pinning=True)
        pinning_cases = cases_from_pinning_file(
            environment["AYON_USD_RESOLVER_PINNING_FILE"], cases
        )
        return self._run_resolve(installation, pinning_cases, pinning=True, environment=environment)

    def _run_resolve(
        self,
        installation: DccInstallation,
        cases: list[TestCase],
        *,
        pinning: bool,
        environment: dict[str, str] | None = None,
    ) -> list[TestResult]:
        environment = environment or self._environment(installation, pinning=pinning)
        executable = dcc.usdresolve_path(installation)
        results = []
        for case in cases:
            command = [str(executable), case.uri]
            if installation.name.casefold() == "maya":
                command.insert(0, str(dcc.python_executable(installation)))
            completed = subprocess.run(
                command,
                env={**os.environ, **environment},
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout,
            )
            self._write_log(installation, case, completed)
            actual_path = self._last_output_line(completed.stdout)
            passed = completed.returncode == 0
            error = None
            if completed.returncode != 0:
                error = f"Process exited with status {completed.returncode}"
            elif case.expected_path or pinning:
                passed = self._normalize(actual_path) == self._normalize(case.expected_path)
                if not passed:
                    error = (
                        f"Resolved path does not match expected path: "
                        f"expected={case.expected_path!r}, actual={actual_path!r}"
                    )
            results.append(
                TestResult(
                    case=case,
                    passed=passed,
                    actual_path=actual_path,
                    return_code=completed.returncode,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                    error=error,
                )
            )
        return results

    def _run_python(self, installation: DccInstallation) -> TestResult:
        script = Path(__file__).resolve().parents[2] / "scripts" / "simple_import.py"
        command = [str(dcc.python_executable(installation)), str(script)]
        environment = self._environment(installation, pinning=False)
        completed = subprocess.run(
            command,
            env={**os.environ, **environment},
            check=False,
            timeout=self.timeout,
        )
        case = TestCase(uri="python-smoke-test", test_type="python")
        return TestResult(
            case=case,
            passed=completed.returncode == 0,
            return_code=completed.returncode,
            error=None if completed.returncode == 0 else "Python smoke test failed",
        )

    def _write_log(self, installation: DccInstallation, case: TestCase, completed) -> None:
        if self.resolver_log_file is None:
            if completed.stdout:
                print(completed.stdout, end="")
            if completed.stderr:
                print(completed.stderr, end="", file=sys.stderr)
            return
        self.resolver_log_file.parent.mkdir(parents=True, exist_ok=True)
        with self.resolver_log_file.open("a", encoding="utf-8") as stream:
            stream.write(
                f"\n=== {installation.name} {installation.version} ===\n"
                f"URI: {case.uri}\n{completed.stdout}{completed.stderr}\n"
            )

    @staticmethod
    def _last_output_line(stdout: str) -> str | None:
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        return lines[-1] if lines else None

    @staticmethod
    def _normalize(path: str | None) -> str:
        if not path:
            return ""
        return os.path.normcase(os.path.realpath(os.path.expanduser(path)))
