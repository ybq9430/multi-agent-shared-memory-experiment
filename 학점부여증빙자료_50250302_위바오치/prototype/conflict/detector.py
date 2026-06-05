"""Conflict detector: identifies visibility, ordering, and semantic conflicts."""

import time
from typing import Optional

from prototype.memory.store import SharedMemoryStore
from prototype.memory.models import (
    MemoryEntry, MemoryType, ConflictType, ConflictRecord, AgentState
)


class ConflictDetector:
    """Detects three types of conflicts in shared memory writes."""

    def __init__(self, store: SharedMemoryStore):
        self.store = store

    def detect(self, agent: AgentState, key: str, new_value: str,
               memory_type: MemoryType = MemoryType.WORKING) -> Optional[ConflictRecord]:
        existing = self.store.read(key, memory_type)
        if existing is None:
            return None

        # Visibility conflict: agent has stale version
        if self._check_visibility(agent, existing):
            return ConflictRecord(
                conflict_type=ConflictType.VISIBILITY,
                key=key, agent_a=agent.agent_id, agent_b=existing.agent_id,
                value_a=new_value, value_b=existing.value
            )

        # Ordering conflict: write based on outdated version
        if self._check_ordering(agent, existing):
            return ConflictRecord(
                conflict_type=ConflictType.ORDERING,
                key=key, agent_a=agent.agent_id, agent_b=existing.agent_id,
                value_a=new_value, value_b=existing.value
            )

        return None

    def check_semantic(self, agent_a: str, value_a: str,
                       agent_b: str, value_b: str,
                       key: str) -> ConflictRecord:
        """Flag a potential semantic conflict for Judge Agent evaluation."""
        return ConflictRecord(
            conflict_type=ConflictType.SEMANTIC,
            key=key, agent_a=agent_a, agent_b=agent_b,
            value_a=value_a, value_b=value_b
        )

    def _check_visibility(self, agent: AgentState, existing: MemoryEntry) -> bool:
        """Agent's last_seen_version is behind the current version."""
        seen = agent.last_seen_version.get(existing.key, 0)
        return seen < existing.version

    def _check_ordering(self, agent: AgentState, existing: MemoryEntry) -> bool:
        """Agent is writing with an outdated base version."""
        seen = agent.last_seen_version.get(existing.key, 0)
        return 0 < seen < existing.version
