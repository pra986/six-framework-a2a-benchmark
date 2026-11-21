# six-framework-a2a-benchmark

Side-by-side task-board benchmark across **Google ADK (+A2A)**, **Strands**, **Pydantic AI**, **Microsoft Agent Framework**, **Agno**, and **Mastra** with physical output verification.

## Architecture Overview

`six-framework-a2a-benchmark` evaluates six modern agent frameworks against an identical, deterministic task-board contract (`notes.txt` -> `spanish.txt`). Every framework adapter runs in an isolated workspace and is judged by physical file verification rather than self-reported LLM claims.

```
+-------------------------------------------------------------------+
|                   SixFrameworkBenchmarkRunner                     |
+-------------------------------------------------------------------+
   |            |            |             |           |         |
   v            v            v             v           v         v
Google ADK   Strands    Pydantic AI   MS Agent Fw    Agno     Mastra
(+A2A)                                                         
   |            |            |             |           |         |
   +------------+------------+-------------+-----------+---------+
                                 |
                                 v
                Workspace Sandbox & Output Verifier
                (notes.txt -> spanish.txt != empty)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for component boundaries, A2A protocol flow, and failure modes.

## 6-Stage Workflow

1. **Workspace Initialization**: Create or validate an isolated workspace directory containing `notes.txt`.
2. **Board Goal Dispatch**: Construct a `BoardGoal` specifying source artifact (`notes.txt`), target artifact (`spanish.txt`), and timeout/sandbox policies.
3. **Framework Adapter Execution**: Invoke each framework adapter (`google_adk`, `strands`, `pydantic_ai`, `microsoft_agent_framework`, `agno`, `mastra`). Google ADK optionally delegates translation to a remote A2A agent and records an `A2ARemoteCallReceipt`.
4. **Filesystem Sandbox Enforcement**: Confine all read/write operations to the designated workspace root, rejecting path traversal attempts.
5. **Physical Output Verification**: Inspect the workspace on disk. `DONE` status is **blocked** unless `spanish.txt` exists and is non-empty; missing `notes.txt` reports an explicit board failure.
6. **Comparison & Reporting**: Emit structured `BenchmarkComparisonRow` records summarizing status, latency, A2A receipt metadata, and verification outcome.

## Data Contract

- **Input**: `notes.txt` inside the run workspace (UTF-8 text). Missing `notes.txt` triggers an explicit `FAILED` board state.
- **Output**: `spanish.txt` inside the same workspace (non-empty UTF-8 translation).
- **Models** (`framework_bench/models.py`):
  - `BoardGoal`: Defines `goal_id`, `workspace_dir`, `source_file`, `target_file`, `timeout_seconds`.
  - `A2ARemoteCallReceipt`: Captures `agent_url`, `task_id`, `status`, `latency_ms`, and `error` for remote A2A calls.
  - `FrameworkWorkerRun`: Records per-framework execution `framework`, `status` (`DONE` | `BLOCKED` | `FAILED`), `output_path`, `output_bytes`, `duration_ms`, `a2a_receipt`, and `failure_reason`.
  - `BenchmarkComparisonRow`: Normalized comparison row across all six frameworks.

## Production Controls

- **No Self-Reported Completion**: A framework cannot mark a board goal `DONE` if `spanish.txt` is missing or `0` bytes; the verifier forces `BLOCKED`/`FAILED`.
- **Workspace Confinement**: Path resolution enforces `workspace_root` containment so agents cannot read or write outside their sandbox.
- **A2A Timeout Isolation**: Remote A2A agent timeouts are caught cleanly, recorded in `A2ARemoteCallReceipt`, and surfaced as structured failures without crashing the benchmark suite.
- **Explicit Source Validation**: Missing `notes.txt` fails fast with a clear diagnostic before worker execution.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Run the CLI demo:

```bash
python -m framework_bench.cli
```

Run the test suite:

```bash
pytest -v
```

## Attribution

Inspired by and adapted from the `5_agent_frameworks` module in [ed-donner/agents](https://github.com/ed-donner/agents) (pinned reference: `ed-donner/agents` `5_agent_frameworks`).

## License

MIT License — see [LICENSE](LICENSE).
 AI, Microsoft Agent Framework, Agno, and Mastra with physical output verification.
