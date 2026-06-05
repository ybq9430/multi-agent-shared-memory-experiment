"""Experiment runner: orchestrates all groups × scenarios × iterations."""

import time
from typing import Optional

from prototype.config import ITERATIONS, RANDOM_SEED
from prototype.memory.store import SharedMemoryStore
from prototype.memory.models import MemoryType, AgentState
from prototype.agents.base import BaseAgent
from prototype.agents.roles import PlannerAgent, ExecutorAgent, ReviewerAgent
from prototype.agents.judge import JudgeAgent
from prototype.consistency.hierarchical import HierarchicalConsistency
from prototype.conflict.resolver import ConflictResolver, ResolverConfig
from prototype.experiments.scenarios import ScenarioGenerator
from prototype.experiments.groups import build_groups
from prototype.experiments.metrics import MetricsCollector, IterationResult


class ExperimentRunner:
    """Runs all experiment configurations and collects results."""

    def __init__(self):
        self.store = SharedMemoryStore()
        self.scenarios = ScenarioGenerator(seed=RANDOM_SEED)
        self.groups = build_groups()
        self.metrics = MetricsCollector()

    def run_all(self):
        """Run all 8 groups × 3 scenarios × 30 iterations."""
        print("=" * 60)
        print("Multi-Agent Shared Memory Experiment Runner")
        print(f"Groups: {len(self.groups)} | Scenarios: 3 | Iterations: {ITERATIONS}")
        print(f"Total runs: {len(self.groups) * 3 * ITERATIONS}")
        print("=" * 60)

        total = len(self.groups) * 3 * ITERATIONS
        current = 0

        for group in self.groups:
            # Reset scenario generator per group so all groups face identical workloads
            self.scenarios = ScenarioGenerator(seed=RANDOM_SEED)
            scenario_methods = [
                ("simultaneous_write", self.scenarios.generate_simultaneous_write),
                ("ordering", self.scenarios.generate_ordering_conflict),
                ("semantic", self.scenarios.generate_semantic_conflict),
            ]

            print(f"\n{'='*60}")
            print(f"Group: {group.name}")
            print(f"  Detection={group.use_detection} Timestamp={group.use_timestamp} "
                  f"Trust={group.use_trust_score} Leader={group.use_leader} "
                  f"Judge={group.use_judge} PreFilter={group.use_pre_filter} "
                  f"Consistency={group.consistency_mode}")
            print(f"{'='*60}")

            for scenario_name, scenario_fn in scenario_methods:
                print(f"  Scenario: {scenario_name} ", end="", flush=True)

                for i in range(ITERATIONS):
                    self._run_single_iteration(group, scenario_name, scenario_fn, i)
                    current += 1
                    if current % 30 == 0:
                        print(".", end="", flush=True)

                print(f" done ({ITERATIONS} runs)")

        print(f"\nAll {current} experiment runs complete.\n")

    def _run_single_iteration(self, config: ResolverConfig, scenario_name: str,
                              scenario_fn, iteration: int):
        """Execute one iteration: generate workload → run agents → detect & resolve → record."""
        self.store.reset()

        # Create agents
        planner = PlannerAgent(self.store, trust_score=0.6)
        executor = ExecutorAgent(self.store, trust_score=0.7)
        reviewer = ReviewerAgent(self.store, trust_score=0.8)

        agents = {
            "planner_1": planner,
            "executor_1": executor,
            "reviewer_1": reviewer,
        }

        # Create resolver for this group
        resolver = ConflictResolver(self.store, config)
        if config.use_leader:
            resolver.set_leader_fn(reviewer.arbitrate)

        # Generate workload
        workload = scenario_fn(iteration)

        # Simulate agent writes with timing
        agent_a = agents.get(workload.agent_a_id)
        agent_b = agents.get(workload.agent_b_id)

        if agent_a is None or agent_b is None:
            return

        # Write initial state (Agent A first)
        init_latency = 0.0
        result_a = agent_a.write_memory(workload.key, workload.value_a)
        # Capture A's entry timestamp before B may overwrite it
        entry_a = self.store.read(workload.key, MemoryType.WORKING)
        ts_a = entry_a.timestamp if entry_a else time.time()

        # Snapshot Agent B's state BEFORE write for conflict detection
        pre_write_state_b = AgentState(
            agent_id=agent_b.agent_id,
            role=agent_b.role,
            trust_score=agent_b.state.trust_score,
            last_seen_version=dict(agent_b.state.last_seen_version),
            success_count=agent_b.state.success_count,
            total_count=agent_b.state.total_count,
        )

        # Simulate timing: agent B writes after delay (scenario 1) or with stale version (scenario 2)
        conflict_detected = False
        if scenario_name == "simultaneous_write":
            if workload.delay_ms > 0:
                time.sleep(min(workload.delay_ms / 1000, 0.01))
            result_b = agent_b.write_memory(workload.key, workload.value_b)
            init_latency = agent_b.last_latency_ms
            conflict_detected = True

        elif scenario_name == "ordering":
            result_b = agent_b.write_memory_checked(
                workload.key, workload.value_b,
                expected_version=workload.expected_version_b
            )
            init_latency = agent_b.last_latency_ms
            conflict_detected = not result_b.success

        elif scenario_name == "semantic":
            agent_a.write_memory(workload.key, workload.value_a)
            result_b = agent_b.write_memory(workload.key, workload.value_b)
            init_latency = agent_b.last_latency_ms
            conflict_detected = True

        # Use scenario's pre-determined timestamps for controlled experiments
        ts_a = workload.ts_a if workload.ts_a > 0 else entry_a.timestamp if entry_a else time.time()
        ts_b = workload.ts_b if workload.ts_b > 0 else time.time()

        # Resolve conflicts using pre-write state
        start = time.time()
        conflict_record = resolver.resolve(
            agent_state=pre_write_state_b,
            key=workload.key,
            new_value=workload.value_b,
            other_agent_state=agent_a.state,
            other_value=workload.value_a,
            timestamps=(ts_a, ts_b),
            memory_type=MemoryType.WORKING
        )

        total_latency = init_latency + ((time.time() - start) * 1000)

        # Determine correctness
        resolved = conflict_record.resolved_value if conflict_record else workload.value_a
        correct = (resolved == workload.ground_truth)

        # Record result
        self.metrics.record(IterationResult(
            scenario=scenario_name,
            group=config.name,
            iteration=iteration,
            conflict_detected=True,  # Two writes to same key = conflict exists
            conflict_resolved=(conflict_record.strategy not in ("last_write_wins", "no_conflict")),
            conflict_type=conflict_record.conflict_type.value if conflict_record else "none",
            resolved_value=resolved,
            ground_truth=workload.ground_truth,
            correct=correct,
            task_success=resolved is not None and len(resolved) > 0,
            latency_ms=total_latency,
            llm_call_count=resolver.judge_call_count
        ))

    def get_results(self):
        return self.metrics.all_summaries()

    def close(self):
        self.store.close()
