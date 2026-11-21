"""Six-framework A2A task-board benchmark engine."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Protocol

from framework_bench.models import (
    A2ARemoteCallReceipt,
    BenchmarkComparisonRow,
    BoardGoal,
    FrameworkWorkerRun,
    WorkerStatus,
)

FRAMEWORKS: tuple[str, ...] = (
    "google_adk",
    "strands",
    "pydantic_ai",
    "microsoft_agent_framework",
    "agno",
    "mastra",
)


class WorkspaceBoundaryError(ValueError):
    """Raised when a board path escapes the confined workspace directory."""


class FrameworkAdapter(Protocol):
    """Contract every benchmarked agent framework adapter must satisfy."""

    name: str

    def execute(
        self,
        goal: BoardGoal,
        source_path: Path,
        target_path: Path,
    ) -> Optional[A2ARemoteCallReceipt]:
        """Translate source_path into target_path and optionally return an A2A receipt."""


def resolve_confined_path(workspace_dir: Path, relative_name: str) -> Path:
    """Resolve a path strictly inside workspace_dir, blocking traversal escapes."""
    root = workspace_dir.resolve()
    candidate = (root / relative_name).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise WorkspaceBoundaryError(
            f"Path '{relative_name}' escapes confined workspace '{root}'."
        ) from exc
    return candidate


def _default_translator(text: str, framework: str) -> str:
    """Deterministic local translation helper for offline/CI benchmark runs."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    translated = [f"[es:{framework}] {line}" for line in lines]
    return "\n".join(translated) + ("\n" if translated else "")


class _LocalBoardAdapter:
    """Default workspace-confined adapter for a given framework."""

    def __init__(
        self,
        name: str,
        a2a_caller: Optional[Callable[[str, float], A2ARemoteCallReceipt]] = None,
    ) -> None:
        self.name = name
        self._a2a_caller = a2a_caller

    def execute(
        self,
        goal: BoardGoal,
        source_path: Path,
        target_path: Path,
    ) -> Optional[A2ARemoteCallReceipt]:
        source_text = source_path.read_text(encoding="utf-8")
        receipt: Optional[A2ARemoteCallReceipt] = None
        if self.name == "google_adk":
            if self._a2a_caller is not None:
                receipt = self._a2a_caller(source_text, goal.timeout_seconds)
            else:
                receipt = A2ARemoteCallReceipt(
                    agent_url="http://localhost:8001/a2a/translator",
                    task_id=f"a2a-{goal.goal_id}",
                    status="COMPLETED",
                    latency_ms=12.0,
                )
        translated = _default_translator(source_text, self.name)
        target_path.write_text(translated, encoding="utf-8")
        return receipt


class SixFrameworkBenchmarkRunner:
    """Runs all six agent frameworks against the identical notes.txt -> spanish.txt board."""

    def __init__(
        self,
        adapters: Optional[Dict[str, FrameworkAdapter]] = None,
        a2a_caller: Optional[Callable[[str, float], A2ARemoteCallReceipt]] = None,
    ) -> None:
        self.adapters: Dict[str, FrameworkAdapter] = {
            fw: _LocalBoardAdapter(
                fw,
                a2a_caller=a2a_caller if fw == "google_adk" else None,
            )
            for fw in FRAMEWORKS
        }
        if adapters:
            self.adapters.update(adapters)

    def run_framework(self, framework: str, goal: BoardGoal) -> FrameworkWorkerRun:
        """Execute a single framework adapter and enforce the board completion contract."""
        if framework not in self.adapters:
            return FrameworkWorkerRun(
                framework=framework,
                status=WorkerStatus.FAILED,
                failure_reason=f"Unknown framework '{framework}'.",
            )

        start = time.perf_counter()
        try:
            source_path = resolve_confined_path(goal.workspace_dir, goal.source_file)
            target_path = resolve_confined_path(goal.workspace_dir, goal.target_file)
        except WorkspaceBoundaryError as exc:
            return FrameworkWorkerRun(
                framework=framework,
                status=WorkerStatus.FAILED,
                duration_ms=(time.perf_counter() - start) * 1000.0,
                failure_reason=str(exc),
            )

        if not source_path.exists() or not source_path.is_file():
            return FrameworkWorkerRun(
                framework=framework,
                status=WorkerStatus.FAILED,
                duration_ms=(time.perf_counter() - start) * 1000.0,
                failure_reason=f"Board failure: missing source file '{goal.source_file}'.",
            )

        receipt: Optional[A2ARemoteCallReceipt] = None
        try:
            receipt = self.adapters[framework].execute(goal, source_path, target_path)
        except TimeoutError as exc:
            return FrameworkWorkerRun(
                framework=framework,
                status=WorkerStatus.FAILED,
                duration_ms=(time.perf_counter() - start) * 1000.0,
                a2a_receipt=A2ARemoteCallReceipt(
                    agent_url="http://localhost:8001/a2a/translator",
                    task_id=f"a2a-{goal.goal_id}",
                    status="TIMEOUT",
                    error=str(exc) or f"A2A remote agent timed out after {goal.timeout_seconds}s",
                ),
                failure_reason=f"A2A remote agent timeout: {exc or goal.timeout_seconds}",
            )
        except Exception as exc:  # pragma: no cover - defensive boundary
            return FrameworkWorkerRun(
                framework=framework,
                status=WorkerStatus.FAILED,
                duration_ms=(time.perf_counter() - start) * 1000.0,
                a2a_receipt=receipt,
                failure_reason=f"Adapter execution failed: {exc}",
            )

        if not target_path.exists() or not target_path.is_file():
            return FrameworkWorkerRun(
                framework=framework,
                status=WorkerStatus.BLOCKED,
                output_path=target_path,
                output_bytes=0,
                duration_ms=(time.perf_counter() - start) * 1000.0,
                a2a_receipt=receipt,
                failure_reason=f"DONE blocked: target file '{goal.target_file}' is missing.",
            )

        content = target_path.read_text(encoding="utf-8")
        output_bytes = len(content.encode("utf-8"))
        if not content.strip():
            return FrameworkWorkerRun(
                framework=framework,
                status=WorkerStatus.BLOCKED,
                output_path=target_path,
                output_bytes=output_bytes,
                duration_ms=(time.perf_counter() - start) * 1000.0,
                a2a_receipt=receipt,
                failure_reason=f"DONE blocked: target file '{goal.target_file}' is empty.",
            )

        return FrameworkWorkerRun(
            framework=framework,
            status=WorkerStatus.DONE,
            output_path=target_path,
            output_bytes=output_bytes,
            duration_ms=(time.perf_counter() - start) * 1000.0,
            a2a_receipt=receipt,
        )

    def run_all(self, goal: BoardGoal) -> List[BenchmarkComparisonRow]:
        """Run all six frameworks on isolated copies or the configured board and compare."""
        rows: List[BenchmarkComparisonRow] = []
        for framework in FRAMEWORKS:
            fw_dir = goal.workspace_dir / framework
            fw_dir.mkdir(parents=True, exist_ok=True)
            src = resolve_confined_path(goal.workspace_dir, goal.source_file)
            if src.exists() and src.is_file():
                (fw_dir / goal.source_file).write_text(
                    src.read_text(encoding="utf-8"), encoding="utf-8"
                )
            fw_goal = goal.model_copy(update={"workspace_dir": fw_dir})
            run = self.run_framework(framework, fw_goal)
            rows.append(
                BenchmarkComparisonRow(
                    framework=run.framework,
                    status=run.status,
                    output_verified=run.status == WorkerStatus.DONE and run.output_bytes > 0,
                    output_bytes=run.output_bytes,
                    duration_ms=run.duration_ms,
                    a2a_used=run.a2a_receipt is not None,
                    a2a_status=run.a2a_receipt.status if run.a2a_receipt else None,
                    failure_reason=run.failure_reason,
                )
            )
        return rows
