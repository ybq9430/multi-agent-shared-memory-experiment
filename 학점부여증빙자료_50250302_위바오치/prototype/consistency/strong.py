"""Strong consistency: lock-based linearizable writes."""

import threading
import time

from prototype.memory.store import SharedMemoryStore, VersionConflictError
from prototype.memory.models import MemoryEntry, MemoryType, ConflictType, ConflictRecord, WriteResult


class StrongConsistency:
    """Ensures all agents see the latest value before any read/write."""

    def __init__(self, store: SharedMemoryStore):
        self.store = store
        self._lock = threading.Lock()

    def read(self, key: str, agent_id: str,
             memory_type: MemoryType = MemoryType.WORKING) -> MemoryEntry | None:
        with self._lock:
            return self.store.read(key, memory_type)

    def write(self, key: str, value: str, agent_id: str,
              memory_type: MemoryType = MemoryType.WORKING) -> WriteResult:
        start = time.time()
        with self._lock:
            existing = self.store.read(key, memory_type)
            if existing is not None and existing.agent_id != agent_id:
                # Another agent wrote recently - detect ordering conflict
                conflict = ConflictRecord(
                    conflict_type=ConflictType.ORDERING,
                    key=key,
                    agent_a=agent_id,
                    agent_b=existing.agent_id,
                    value_a=value,
                    value_b=existing.value,
                    latency_ms=(time.time() - start) * 1000
                )
                # Strong consistency: latest write wins, but we log the conflict
                entry = self.store.write(key, value, agent_id, memory_type)
                return WriteResult(
                    success=True, key=key, version=entry.version,
                    conflict=conflict, latency_ms=(time.time() - start) * 1000
                )

            entry = self.store.write(key, value, agent_id, memory_type)
            latency_ms = (time.time() - start) * 1000
            return WriteResult(success=True, key=key, version=entry.version,
                               latency_ms=latency_ms)
