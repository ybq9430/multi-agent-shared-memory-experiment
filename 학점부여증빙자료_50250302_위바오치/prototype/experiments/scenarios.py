"""Three conflict scenarios for experiment evaluation."""

import random
import time
from dataclasses import dataclass
from typing import Optional

from prototype.config import (
    RANDOM_SEED, SIMULTANEOUS_WRITE_WINDOW,
    ORDERING_CONFLICT_DELAY_MIN, ORDERING_CONFLICT_DELAY_MAX
)


@dataclass
class ScenarioWorkload:
    """A single workload instance for an experiment iteration."""
    key: str
    agent_a_id: str
    agent_b_id: str
    value_a: str
    value_b: str
    ground_truth: str  # The correct resolved value
    conflict_type: str  # "simultaneous_write" | "ordering" | "semantic"
    delay_ms: float = 0.0  # Delay for agent_b's write (simulates timing)
    expected_version_a: int = 0  # Version agent_a expects
    expected_version_b: int = 0  # Version agent_b expects
    ts_a: float = 0.0  # Pre-determined timestamp for agent A's write
    ts_b: float = 0.0  # Pre-determined timestamp for agent B's write


class ScenarioGenerator:
    """Generates controlled workloads for the three conflict scenarios."""

    def __init__(self, seed: int = RANDOM_SEED):
        self.rng = random.Random(seed)

    def generate_simultaneous_write(self, iteration: int) -> ScenarioWorkload:
        """Scenario 1: Two agents write to the same key simultaneously."""
        key = f"task_status_{iteration}"
        ts_a = self.rng.uniform(0, SIMULTANEOUS_WRITE_WINDOW)
        ts_b = self.rng.uniform(0, SIMULTANEOUS_WRITE_WINDOW)

        # Use a base timestamp so resolver can distinguish them
        base = 1_000_000.0 + iteration * 1000
        ts_a_abs = base + ts_a
        ts_b_abs = base + ts_b

        if ts_a <= ts_b:
            return ScenarioWorkload(
                key=key,
                agent_a_id="planner_1",
                agent_b_id="executor_1",
                value_a=f"status_planned_v{iteration}",
                value_b=f"status_executed_v{iteration}",
                ground_truth=f"status_executed_v{iteration}",
                conflict_type="simultaneous_write",
                delay_ms=ts_b * 1000,
                ts_a=ts_a_abs,
                ts_b=ts_b_abs,
            )
        else:
            return ScenarioWorkload(
                key=key,
                agent_a_id="planner_1",
                agent_b_id="executor_1",
                value_a=f"status_planned_v{iteration}",
                value_b=f"status_executed_v{iteration}",
                ground_truth=f"status_planned_v{iteration}",
                conflict_type="simultaneous_write",
                delay_ms=ts_a * 1000,
                ts_a=ts_a_abs,
                ts_b=ts_b_abs,
            )

    def generate_ordering_conflict(self, iteration: int) -> ScenarioWorkload:
        """Scenario 2: Agent with old timestamp overwrites newer value."""
        key = f"decision_log_{iteration}"
        delay_s = self.rng.uniform(ORDERING_CONFLICT_DELAY_MIN, ORDERING_CONFLICT_DELAY_MAX)

        base = 2_000_000.0 + iteration * 1000
        return ScenarioWorkload(
            key=key,
            agent_a_id="executor_1",
            agent_b_id="planner_1",
            value_a=f"newer_decision_v{iteration}_x",
            value_b=f"older_decision_v{iteration}_y",
            ground_truth=f"newer_decision_v{iteration}_x",
            conflict_type="ordering",
            delay_ms=delay_s * 1000,
            expected_version_a=1,
            expected_version_b=0,
            ts_a=base + delay_s,
            ts_b=base,
        )

    def generate_semantic_conflict(self, iteration: int) -> ScenarioWorkload:
        """Scenario 3: Two agents produce semantically contradictory conclusions."""
        key = f"feedback_history_{iteration}"

        # 15 contradictory pairs covering diverse domains
        pairs = [
            # Safety/Security
            ("The system is ready for production deployment.",
             "The system has critical bugs and must not be deployed.",
             "The system has critical bugs and must not be deployed."),

            # Storage decision
            ("We should use SQLite for persistent storage.",
             "We should use in-memory dicts for all storage.",
             "We should use SQLite for persistent storage."),

            # Algorithm analysis
            ("The algorithm complexity is O(n log n).",
             "The algorithm complexity is O(n^2) in worst case.",
             "The algorithm complexity is O(n^2) in worst case."),

            # Test results
            ("All tests passed, code is stable.",
             "Integration tests failed, code has regressions.",
             "Integration tests failed, code has regressions."),

            # Trust score design
            ("Trust score should be based on success rate only.",
             "Trust score should incorporate latency and quality metrics.",
             "Trust score should incorporate latency and quality metrics."),

            # Memory consistency
            ("Strong consistency is required for all memory operations.",
             "Eventual consistency is sufficient for most use cases.",
             "Eventual consistency is sufficient for most use cases."),

            # Agent coordination
            ("A single leader agent should make all decisions.",
             "Agents should vote democratically on every decision.",
             "Agents should vote democratically on every decision."),

            # Error handling
            ("Failed tasks should be retried immediately without limit.",
             "Failed tasks should use exponential backoff with max retries.",
             "Failed tasks should use exponential backoff with max retries."),

            # Data format
            ("All agent communication should use JSON format.",
             "Agent communication should use plain text for readability.",
             "All agent communication should use JSON format."),

            # Model selection
            ("We should use the latest model for all tasks regardless of cost.",
             "We should select the cheapest model that meets accuracy thresholds.",
             "We should select the cheapest model that meets accuracy thresholds."),

            # Logging strategy
            ("Debug logs should be enabled in production for troubleshooting.",
             "Only error-level logs should be kept in production environments.",
             "Only error-level logs should be kept in production environments."),

            # Version management
            ("Memory versions should use vector clocks for precise ordering.",
             "Simple integer version counters are sufficient for our scale.",
             "Simple integer version counters are sufficient for our scale."),

            # Conflict resolution timing
            ("Conflicts should be resolved synchronously before any further writes.",
             "Conflicts can be resolved asynchronously to improve throughput.",
             "Conflicts should be resolved synchronously before any further writes."),

            # Agent specialization
            ("Each agent should be highly specialized for a single role.",
             "Agents should be general-purpose to handle any task flexibly.",
             "Each agent should be highly specialized for a single role."),

            # Evaluation metric
            ("System performance should be measured by throughput only.",
             "System performance must balance throughput, latency, and accuracy.",
             "System performance must balance throughput, latency, and accuracy."),
        ]

        chosen = pairs[iteration % len(pairs)]
        base = 3_000_000.0 + iteration * 1000
        return ScenarioWorkload(
            key=key,
            agent_a_id="executor_1",
            agent_b_id="reviewer_1",
            value_a=chosen[0],
            value_b=chosen[1],
            ground_truth=chosen[2],
            conflict_type="semantic",
            ts_a=base + 1.0,  # Agent A writes slightly earlier
            ts_b=base + 0.5,  # Agent B writes slightly later
        )
