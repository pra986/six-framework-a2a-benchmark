"""Pytest suite for six-framework-a2a-benchmark."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from framework_bench.engine import FRAMEWORKS, SixFrameworkBenchmarkRunner
from framework_bench.models import A2ARemoteCallReceipt, BoardGoal, WorkerStatus


class _NoWriteAdapter:
    def __init__(self, name: str = "strands") -> None:
        self.name = name

    def execute(
        self,
        goal: BoardGoal,
        source_path: Path,
        target_path: Path,
    ) -> Optional[A2ARemoteCallReceipt]:
        return None


class _EmptyWriteAdapter:
    def __init__(self, name: str = "strands") -> None:
        self.name = name

    def execute(
        self,
        goal: BoardGoal,
        source_path: Path,
        target_path: Path,
    ) -> Optional[A2ARemoteCallReceipt]:
        target_path.write_text("   \n  ", encoding="utf-8")
        return None


def test_done_blocked_when_spanish_txt_missing(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("Hello team\n", encoding="utf-8")
    runner = SixFrameworkBenchmarkRunner(adapters={"strands": _NoWriteAdapter()})
    run = runner.run_framework(
        "strands",
        BoardGoal(goal_id="missing-target", workspace_dir=tmp_path),
    )
    assert run.status == WorkerStatus.BLOCKED
    assert run.failure_reason is not None
    assert "missing" in run.failure_reason.lower()


def test_done_blocked_when_spanish_txt_empty(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("Hello team\n", encoding="utf-8")
    runner = SixFrameworkBenchmarkRunner(adapters={"strands": _EmptyWriteAdapter()})
    run = runner.run_framework(
        "strands",
        BoardGoal(goal_id="empty-target", workspace_dir=tmp_path),
    )
    assert run.status == WorkerStatus.BLOCKED
    assert run.failure_reason is not None
    assert "empty" in run.failure_reason.lower()


def test_missing_notes_reports_explicit_board_failure(tmp_path: Path) -> None:
    runner = SixFrameworkBenchmarkRunner()
    run = runner.run_framework(
        "pydantic_ai",
        BoardGoal(goal_id="missing-source", workspace_dir=tmp_path),
    )
    assert run.status == WorkerStatus.FAILED
    assert run.failure_reason is not None
    assert "notes.txt" in run.failure_reason


def test_workspace_confinement_blocks_traversal(tmp_path: Path) -> None:
    runner = SixFrameworkBenchmarkRunner()
    run = runner.run_framework(
        "agno",
        BoardGoal(
            goal_id="escape",
            workspace_dir=tmp_path,
            source_file="../outside.txt",
        ),
    )
    assert run.status == WorkerStatus.FAILED
    assert run.failure_reason is not None
    assert "escapes" in run.failure_reason.lower()


def test_all_six_frameworks_conform_to_board_contract(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("Launch readiness review.\n", encoding="utf-8")
    runner = SixFrameworkBenchmarkRunner()
    rows = runner.run_all(BoardGoal(goal_id="all-six", workspace_dir=tmp_path))
    assert [row.framework for row in rows] == list(FRAMEWORKS)
    assert len(rows) == 6
    for row in rows:
        assert row.status == WorkerStatus.DONE
        assert row.output_verified is True
        assert row.output_bytes > 0
        out_file = tmp_path / row.framework / "spanish.txt"
        assert out_file.exists() and out_file.read_text(encoding="utf-8").strip()


def test_a2a_remote_agent_timeout_handled_cleanly(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("Translate via A2A.\n", encoding="utf-8")

    def _timeout_caller(text: str, timeout: float) -> A2ARemoteCallReceipt:
        raise TimeoutError(f"Timed out after {timeout}s")

    runner = SixFrameworkBenchmarkRunner(a2a_caller=_timeout_caller)
    run = runner.run_framework(
        "google_adk",
        BoardGoal(goal_id="a2a-timeout", workspace_dir=tmp_path, timeout_seconds=1.5),
    )
    assert run.status == WorkerStatus.FAILED
    assert run.a2a_receipt is not None
    assert run.a2a_receipt.status == "TIMEOUT"
    assert run.failure_reason is not None
    assert "timeout" in run.failure_reason.lower()
