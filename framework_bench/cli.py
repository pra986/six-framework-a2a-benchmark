"""Runnable CLI demo entrypoint for the six-framework A2A benchmark."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import List, Optional

from framework_bench.engine import SixFrameworkBenchmarkRunner
from framework_bench.models import BoardGoal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="framework-bench",
        description="Run the 6-framework A2A notes.txt -> spanish.txt board benchmark.",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Optional workspace directory containing notes.txt (defaults to a temporary demo workspace).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="A2A remote agent timeout in seconds (default: 10.0).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print comparison results as JSON.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    runner = SixFrameworkBenchmarkRunner()

    if args.workspace is not None:
        workspace = args.workspace
        workspace.mkdir(parents=True, exist_ok=True)
        notes_path = workspace / "notes.txt"
        if not notes_path.exists():
            notes_path.write_text(
                "Quarterly benchmark: verify A2A handoff and spanish.txt output.\n",
                encoding="utf-8",
            )
        rows = runner.run_all(
            BoardGoal(
                goal_id="cli-demo",
                workspace_dir=workspace,
                timeout_seconds=args.timeout,
            )
        )
    else:
        with tempfile.TemporaryDirectory(prefix="six-fw-bench-") as tmp_dir:
            workspace = Path(tmp_dir)
            (workspace / "notes.txt").write_text(
                "Quarterly benchmark: verify A2A handoff and spanish.txt output.\n",
                encoding="utf-8",
            )
            rows = runner.run_all(
                BoardGoal(
                    goal_id="cli-demo",
                    workspace_dir=workspace,
                    timeout_seconds=args.timeout,
                )
            )

    if args.json:
        print(json.dumps([row.model_dump() for row in rows], indent=2))
    else:
        print(f"{'Framework':<28} {'Status':<10} {'Bytes':<8} {'A2A':<12} {'Duration(ms)':<12}")
        print("-" * 74)
        for row in rows:
            a2a_info = row.a2a_status or "-"
            print(
                f"{row.framework:<28} {row.status.value:<10} {row.output_bytes:<8} "
                f"{a2a_info:<12} {row.duration_ms:<12.2f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
