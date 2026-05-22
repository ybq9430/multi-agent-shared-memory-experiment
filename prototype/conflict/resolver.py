"""Conflict resolver: integrates detector, strategies, and Judge Agent."""

import time
from dataclasses import dataclass
from typing import Optional

from prototype.memory.store import SharedMemoryStore
from prototype.memory.models import (
    MemoryEntry, MemoryType, ConflictType, ConflictRecord, AgentState
)
from prototype.conflict.detector import ConflictDetector
from prototype.agents.judge import JudgeAgent
from prototype.strategies.timestamp import resolve_timestamp
from prototype.strategies.trust_score import resolve_trust_score
from prototype.strategies.leader import resolve_leader


@dataclass
class ResolverConfig:
    """Configuration for which components are active in this comparison group."""
    name: str
    use_detection: bool = False
    use_timestamp: bool = False
    use_trust_score: bool = False
    use_leader: bool = False
    use_judge: bool = False
    use_pre_filter: bool = False
    consistency_mode: str = "none"


class ConflictResolver:
    """Orchestrates conflict detection and resolution for a given configuration."""

    def __init__(self, store: SharedMemoryStore, config: ResolverConfig):
        self.store = store
        self.config = config
        self.detector = ConflictDetector(store) if config.use_detection else None
        self.judge = JudgeAgent() if config.use_judge else None
        self._leader_fn = None

    def set_leader_fn(self, fn):
        self._leader_fn = fn

    def resolve(self, agent_state: AgentState, key: str, new_value: str,
                other_agent_state: Optional[AgentState] = None,
                other_value: Optional[str] = None,
                timestamps: Optional[tuple[float, float]] = None,
                memory_type: MemoryType = MemoryType.WORKING) -> ConflictRecord:
        start = time.time()

        existing = self.store.read(key, memory_type)
        ts_existing = timestamps[0] if timestamps else (existing.timestamp if existing else time.time())
        ts_new = timestamps[1] if timestamps else time.time()

        value_existing = other_value if other_value else (existing.value if existing else new_value)
        agent_a_id = other_agent_state.agent_id if other_agent_state else "unknown"

        # Phase 1: Detect structural conflicts
        conflict_type = ConflictType.ORDERING
        if self.config.use_detection and self.detector:
            detected = self.detector.detect(agent_state, key, new_value, memory_type)
            if detected:
                conflict_type = detected.conflict_type

        # Track whether structural resolution was applied
        structural_resolved = None
        structural_strategy = ""
        structural_latency = 0.0

        # Phase 2: Apply structural pre-filter if enabled
        if self.config.use_pre_filter and self.config.use_detection:
            structural_resolved, structural_strategy, structural_latency = \
                self._apply_structural_strategy(
                    value_existing, new_value,
                    trust_a=other_agent_state.trust_score if other_agent_state else 0.5,
                    trust_b=agent_state.trust_score,
                    ts_a=ts_existing,
                    ts_b=ts_new
                )

        # Phase 3: Optionally invoke Judge Agent for semantic check.
        # Only invoke Judge for semantically meaningful values (natural language),
        # not for simple version strings or structural-only conflicts.
        judge_resolved = None
        judge_strategy = ""
        judge_latency = 0.0

        if self.config.use_judge and self.judge and other_value:
            # When pre_filter is disabled (Ablation2), Judge must handle everything.
            # When pre_filter is enabled (FullProposed), Judge only checks natural-language values.
            needs_judge = not self.config.use_pre_filter or \
                          self._needs_semantic_check(value_existing, new_value)
            if needs_judge:
                judge_result = self.judge.judge(key, agent_a_id, value_existing,
                                                agent_state.agent_id, new_value)
                judge_latency = judge_result.get("latency_ms", 0.0)
                if judge_result.get("conflict", False):
                    judge_resolved = self._apply_judge_result(judge_result, value_existing, new_value)
                    judge_strategy = f"judge_{judge_result.get('resolution', 'unknown')}"
                elif not structural_resolved:
                    judge_resolved = self._apply_judge_result(judge_result, value_existing, new_value)
                    judge_strategy = f"judge_noconflict_{judge_result.get('resolution', 'unknown')}"

        # Phase 4: Determine final resolution
        if judge_resolved:
            # Judge Agent has the final say for semantic conflicts
            final_value = judge_resolved
            final_strategy = judge_strategy
            final_type = ConflictType.SEMANTIC
        elif structural_resolved:
            final_value = structural_resolved
            final_strategy = structural_strategy
            final_type = conflict_type
        else:
            # Fallback: last-write-wins
            final_db = self.store.read(key, memory_type)
            final_value = final_db.value if final_db else new_value
            final_strategy = "last_write_wins"
            final_type = conflict_type

        record = ConflictRecord(
            conflict_type=final_type,
            key=key, agent_a=agent_a_id, agent_b=agent_state.agent_id,
            value_a=value_existing, value_b=new_value,
            resolved_value=final_value, strategy=final_strategy,
            latency_ms=(time.time() - start) * 1000 + structural_latency + judge_latency
        )

        self._write_resolved(key, final_value, agent_state.agent_id, memory_type)
        self._log_conflict(record, final_value)
        return record

    def _apply_structural_strategy(self, value_a: str, value_b: str,
                                   trust_a: float, trust_b: float,
                                   ts_a: float, ts_b: float) -> tuple[str, str, float]:
        """Apply the configured structural resolution strategy."""
        if self.config.use_timestamp:
            return resolve_timestamp(value_a, value_b, ts_a, ts_b)
        elif self.config.use_trust_score:
            return resolve_trust_score(value_a, value_b, trust_a, trust_b)
        elif self.config.use_leader and self._leader_fn:
            return resolve_leader(value_a, value_b, self._leader_fn)
        else:
            return value_b, "last_write_wins", 0.0

    def _apply_judge_result(self, judge_result: dict, value_a: str, value_b: str) -> str:
        resolution = judge_result.get("resolution", "value_a")
        return value_b if resolution == "value_b" else value_a

    def _write_resolved(self, key: str, value: str, agent_id: str, memory_type: MemoryType):
        """Write the final resolved value to the store."""
        try:
            self.store.write(key, value, agent_id, memory_type)
        except Exception:
            pass  # Best-effort write

    def _log_conflict(self, record: ConflictRecord, resolved_value: str):
        self.store.log_conflict(
            conflict_type=record.conflict_type.value,
            key=record.key,
            agent_a=record.agent_a,
            agent_b=record.agent_b,
            value_a=record.value_a,
            value_b=record.value_b,
            resolved_value=resolved_value,
            strategy=record.strategy,
            latency_ms=record.latency_ms,
            correct=record.correct
        )

    def _needs_semantic_check(self, value_a: str, value_b: str) -> bool:
        """Determine if two values warrant a semantic (LLM) check.

        Returns True for natural language sentences; False for simple version strings
        or structural identifiers that don't need LLM evaluation.
        """
        # If either value looks like natural language (has spaces, periods, > 30 chars)
        def is_natural_lang(v: str) -> bool:
            return len(v) > 40 or (" " in v and "." in v) or ("?" in v or "!" in v)

        return is_natural_lang(value_a) or is_natural_lang(value_b)

    @property
    def judge_call_count(self) -> int:
        return self.judge.call_count if self.judge else 0

    @property
    def judge_total_latency_ms(self) -> float:
        return self.judge.total_latency_ms if self.judge else 0.0

    def reset_stats(self):
        if self.judge:
            self.judge.reset_stats()
