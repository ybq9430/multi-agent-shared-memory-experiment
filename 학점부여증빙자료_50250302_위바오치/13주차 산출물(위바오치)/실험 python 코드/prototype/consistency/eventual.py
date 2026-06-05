"""Eventual consistency: write without blocking, reads may be stale."""

import time
from typing import Optional

from prototype.memory.store import SharedMemoryStore
from prototype.memory.models import MemoryEntry, MemoryType, ConflictType, ConflictRecord, WriteResult


class EventualConsistency:
    """Non-blocking writes; system eventually converges to consistent state."""

    def __init__(self, store: SharedMemoryStore):
        self.store = store

    def read(self, key: str, agent_id: str,
             memory_type: MemoryType = MemoryType.LONG_TERM) -> Optional[MemoryEntry]:
        return self.store.read(key, memory_type)

    def write(self, key: str, value: str, agent_id: str,
              memory_type: MemoryType = MemoryType.LONG_TERM) -> WriteResult:
        start = time.time()
        existing = self.store.read(key, memory_type)
        try:
            expected = existing.version if existing else None
            entry = self.store.write(key, value, agent_id, memory_type, expected)
            latency_ms = (time.time() - start) * 1000
            return WriteResult(success=True, key=key, version=entry.version,
                               latency_ms=latency_ms)
        except Exception as e:
            # On conflict, last-writer-wins
            entry = self.store.write(key, value, agent_id, memory_type)
            conflict = None
            if existing and existing.agent_id != agent_id:
                conflict = ConflictRecord(
                    conflict_type=ConflictType.ORDERING,
                    key=key, agent_a=agent_id, agent_b=existing.agent_id,
                    value_a=value, value_b=existing.value,
                    latency_ms=(time.time() - start) * 1000
                )
            latency_ms = (time.time() - start) * 1000
            return WriteResult(success=True, key=key, version=entry.version,
                               conflict=conflict, latency_ms=latency_ms)
