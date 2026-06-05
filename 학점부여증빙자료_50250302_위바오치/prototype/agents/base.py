"""Base agent class for multi-agent collaboration."""

import time
from typing import Optional

from prototype.memory.store import SharedMemoryStore
from prototype.memory.models import MemoryEntry, MemoryType, AgentState, WriteResult


class BaseAgent:
    def __init__(self, agent_id: str, role: str, store: SharedMemoryStore,
                 trust_score: float = 0.5):
        self.agent_id = agent_id
        self.role = role
        self.store = store
        self.state = AgentState(
            agent_id=agent_id,
            role=role,
            trust_score=trust_score
        )
        self._last_write_latency_ms: float = 0.0

    def read_memory(self, key: str, memory_type: MemoryType = MemoryType.WORKING) -> Optional[MemoryEntry]:
        entry = self.store.read(key, memory_type)
        if entry:
            self.state.last_seen_version[key] = entry.version
        return entry

    def write_memory(self, key: str, value: str,
                     memory_type: MemoryType = MemoryType.WORKING) -> WriteResult:
        start = time.time()
        entry = self.store.write(key, value, self.agent_id, memory_type)
        self._last_write_latency_ms = (time.time() - start) * 1000
        self.state.total_count += 1
        self.state.success_count += 1
        self._update_trust_score()
        self.state.last_seen_version[key] = entry.version
        return WriteResult(success=True, key=key, version=entry.version,
                           latency_ms=self._last_write_latency_ms)

    def write_memory_checked(self, key: str, value: str, expected_version: int,
                             memory_type: MemoryType = MemoryType.WORKING) -> WriteResult:
        start = time.time()
        try:
            entry = self.store.write(key, value, self.agent_id, memory_type, expected_version)
            self._last_write_latency_ms = (time.time() - start) * 1000
            self.state.total_count += 1
            self.state.success_count += 1
            self._update_trust_score()
            return WriteResult(success=True, key=key, version=entry.version,
                               latency_ms=self._last_write_latency_ms)
        except Exception:
            self.state.total_count += 1
            self._update_trust_score()
            self._last_write_latency_ms = (time.time() - start) * 1000
            return WriteResult(success=False, key=key, version=0,
                               latency_ms=self._last_write_latency_ms)

    def record_failure(self):
        self.state.total_count += 1
        self._update_trust_score()

    def _update_trust_score(self):
        if self.state.total_count > 0:
            self.state.trust_score = self.state.success_count / self.state.total_count

    @property
    def last_latency_ms(self) -> float:
        return self._last_write_latency_ms
