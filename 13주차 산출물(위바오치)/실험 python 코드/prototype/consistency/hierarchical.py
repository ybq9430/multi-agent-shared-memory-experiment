"""Hierarchical consistency: strong for working memory, eventual for long-term."""

from prototype.memory.store import SharedMemoryStore
from prototype.memory.models import MemoryEntry, MemoryType, WriteResult
from prototype.consistency.strong import StrongConsistency
from prototype.consistency.eventual import EventualConsistency


class HierarchicalConsistency:
    """Two-tier consistency: working memory (strong) + long-term memory (eventual)."""

    def __init__(self, store: SharedMemoryStore):
        self.store = store
        self.strong = StrongConsistency(store)
        self.eventual = EventualConsistency(store)

    def read(self, key: str, agent_id: str,
             memory_type: MemoryType = MemoryType.WORKING) -> MemoryEntry | None:
        if memory_type == MemoryType.WORKING:
            return self.strong.read(key, agent_id, memory_type)
        return self.eventual.read(key, agent_id, memory_type)

    def write(self, key: str, value: str, agent_id: str,
              memory_type: MemoryType = MemoryType.WORKING) -> WriteResult:
        if memory_type == MemoryType.WORKING:
            return self.strong.write(key, value, agent_id, memory_type)
        return self.eventual.write(key, value, agent_id, memory_type)

    def upgrade_to_long_term(self, key: str, agent_id: str):
        """Promote a working memory entry to long-term memory."""
        entry = self.store.read(key, MemoryType.WORKING)
        if entry is None:
            return None
        return self.store.write(key, entry.value, agent_id, MemoryType.LONG_TERM)
