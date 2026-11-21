"""Data models for the six-framework A2A task-board benchmark."""

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class WorkerStatus(str, Enum):
    """Execution status of a framework worker run."""

    DONE = "DONE"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class BoardGoal(BaseModel):
    """Task-board contract specifying source and target artifacts within a workspace."""

    goal_id: str = Field(..., description="Unique identifier for the board goal.")
    workspace_dir: Path = Field(..., description="Root directory confining filesystem access.")
    source_file: str = Field(default="notes.txt", description="Input artifact filename.")
    target_file: str = Field(default="spanish.txt", description="Output artifact filename.")
    timeout_seconds: float = Field(default=10.0, gt=0.0, description="Timeout for remote A2A calls.")


class A2ARemoteCallReceipt(BaseModel):
    """Receipt capturing telemetry and status of a remote A2A agent invocation."""

    agent_url: str = Field(..., description="Target A2A remote agent endpoint.")
    task_id: str = Field(..., description="Remote A2A task identifier.")
    status: str = Field(..., description="Outcome status (e.g. COMPLETED, TIMEOUT, ERROR).")
    latency_ms: float = Field(default=0.0, ge=0.0)
    error: Optional[str] = Field(default=None, description="Error details if the A2A call failed.")


class FrameworkWorkerRun(BaseModel):
    """Result of executing a single framework adapter against a BoardGoal."""

    framework: str = Field(..., description="Framework identifier.")
    status: WorkerStatus = Field(..., description="Verified board status.")
    output_path: Optional[Path] = Field(default=None, description="Resolved path to target_file.")
    output_bytes: int = Field(default=0, ge=0, description="Byte size of verified target_file.")
    duration_ms: float = Field(default=0.0, ge=0.0)
    a2a_receipt: Optional[A2ARemoteCallReceipt] = Field(default=None)
    failure_reason: Optional[str] = Field(default=None)


class BenchmarkComparisonRow(BaseModel):
    """Normalized comparison row across all six framework runs."""

    framework: str
    status: WorkerStatus
    output_verified: bool
    output_bytes: int
    duration_ms: float
    a2a_used: bool = False
    a2a_status: Optional[str] = None
    failure_reason: Optional[str] = None
