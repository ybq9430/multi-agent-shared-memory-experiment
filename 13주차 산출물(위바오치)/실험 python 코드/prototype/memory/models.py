"""Data models for the shared memory system."""

from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Optional


class MemoryType(Enum):
    WORKING = "working"
    LONG_TERM = "long_term"


class ConflictType(Enum):
    VISIBILITY = "visibility"
    ORDERING = "ordering"
    SEMANTIC = "semantic"


@dataclass
class MemoryEntry:
    key: str
    value: str
    version: int
    timestamp: float = field(default_factory=time)
    agent_id: str = ""
    memory_type: MemoryType = MemoryType.WORKING


@dataclass
class AgentState:
    agent_id: str
    role: str
    trust_score: float = 0.5
    last_seen_version: dict = field(default_factory=dict)  # key → version
    success_count: int = 0
    total_count: int = 0


@dataclass
class ConflictRecord:
    conflict_type: ConflictType
    key: str
    agent_a: str
    agent_b: str
    value_a: str
    value_b: str
    resolved_value: str = ""
    strategy: str = ""
    latency_ms: float = 0.0
    correct: bool = False


@dataclass
class WriteResult:
    success: bool
    key: str
    version: int
    conflict: Optional[ConflictRecord] = None
    latency_ms: float = 0.0
