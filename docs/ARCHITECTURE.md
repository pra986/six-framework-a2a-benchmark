# Architecture Overview

## 1. Benchmark Contract (`notes.txt` -> `spanish.txt`)

`six-framework-a2a-benchmark` evaluates six agent frameworks against an identical, deterministic task-board contract:

1. **Google ADK (+ A2A remote agent)** (`google_adk`)
2. **Strands** (`strands`)
3. **Pydantic AI** (`pydantic_ai`)
4. **Microsoft Agent Framework** (`microsoft_agent_framework`)
5. **Agno** (`agno`)
6. **Mastra** (`mastra`)

Every framework adapter receives a `BoardGoal` specifying `goal_id`, `workspace_dir`, `source_file` (`notes.txt`), `target_file` (`spanish.txt`), and `timeout_seconds`.

## 2. Physical Output Verification & Guardrails

- **Workspace Confinement**: `resolve_confined_path()` resolves all source and target paths relative to `workspace_dir.resolve()` and raises `WorkspaceBoundaryError` if any path attempts directory traversal (`..`) outside the workspace.
- **Explicit Source Failure**: If `notes.txt` is missing, `SixFrameworkBenchmarkRunner.run_framework()` returns `WorkerStatus.FAILED` with an explicit board failure reason before invoking any adapter.
- **Physical Output Gate (`DONE` Blocking)**: An adapter cannot self-report `DONE`. The runner inspects the physical `spanish.txt` file on disk after execution:
  - Missing `spanish.txt` -> `WorkerStatus.BLOCKED` (`DONE` blocked).
  - Empty or whitespace-only `spanish.txt` -> `WorkerStatus.BLOCKED` (`DONE` blocked).
  - Non-empty `spanish.txt` -> `WorkerStatus.DONE` with verified `output_bytes`.

## 3. A2A Remote Agent & Timeout Handling

For `google_adk`, the runner invokes the configured A2A remote agent caller and records an `A2ARemoteCallReceipt` (`agent_url`, `task_id`, `status`, `latency_ms`, `error`). If the remote A2A call raises `TimeoutError`, the runner catches it cleanly, records `status="TIMEOUT"` in `a2a_receipt`, and returns `WorkerStatus.FAILED` without crashing the comparison suite.

## 4. Data Flow

```
BoardGoal(notes.txt -> spanish.txt)
   │
   ├─► resolve_confined_path() ──[escape]──► WorkerStatus.FAILED
   ├─► source exists check     ──[missing]─► WorkerStatus.FAILED
   ├─► FrameworkAdapter.execute()
   │      └─► (google_adk) A2A Remote Call ──[TimeoutError]──► WorkerStatus.FAILED + TIMEOUT receipt
   └─► Physical target check   ──[missing/empty]──► WorkerStatus.BLOCKED
                               ──[non-empty]──────► WorkerStatus.DONE
```
