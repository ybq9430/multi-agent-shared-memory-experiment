"""Metrics collection and calculation."""

from dataclasses import dataclass, field


@dataclass
class IterationResult:
    """Results for a single experiment iteration."""
    scenario: str
    group: str
    iteration: int
    conflict_detected: bool  # True if a real conflict existed (two writes to same key)
    conflict_resolved: bool  # True if the system actively resolved it (not just last-write-wins)
    conflict_type: str
    resolved_value: str
    ground_truth: str
    correct: bool
    task_success: bool
    latency_ms: float
    llm_call_count: int = 0


@dataclass
class GroupSummary:
    """Aggregated metrics for one comparison group on one scenario."""
    group: str
    scenario: str
    accuracy: float  # percentage
    consistency_rate: float  # percentage
    task_success_rate: float  # percentage
    avg_latency_ms: float
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    std_latency_ms: float = 0.0
    total_llm_calls: int = 0
    iterations: int = 0


class MetricsCollector:
    """Collects and aggregates experiment metrics."""

    def __init__(self):
        self.results: list[IterationResult] = []

    def record(self, result: IterationResult):
        self.results.append(result)

    def summarize(self, group: str, scenario: str) -> GroupSummary:
        """Calculate aggregate metrics for a group+scenario combination."""
        relevant = [r for r in self.results
                    if r.group == group and r.scenario == scenario]

        if not relevant:
            return GroupSummary(
                group=group, scenario=scenario,
                accuracy=0.0, consistency_rate=0.0,
                task_success_rate=0.0, avg_latency_ms=0.0,
                total_llm_calls=0, iterations=0
            )

        n = len(relevant)
        correct = sum(1 for r in relevant if r.correct)
        success = sum(1 for r in relevant if r.task_success)
        lats = [r.latency_ms for r in relevant]
        total_latency = sum(lats)
        total_llm = sum(r.llm_call_count for r in relevant)
        # Latency stats
        lat_avg = total_latency / n
        lat_min = min(lats)
        lat_max = max(lats)
        lat_std = (sum((l - lat_avg)**2 for l in lats) / n) ** 0.5

        # Consistency rate: % of iterations where conflicts were actively resolved
        # (not left to last-write-wins). When no conflict existed, memory is consistent.
        has_conflict = sum(1 for r in relevant if r.conflict_detected)
        resolved = sum(1 for r in relevant if r.conflict_resolved)
        if has_conflict > 0:
            consistency = (resolved / has_conflict) * 100
        else:
            consistency = 100.0  # No conflicts = fully consistent
        success = sum(1 for r in relevant if r.task_success)

        return GroupSummary(
            group=group,
            scenario=scenario,
            accuracy=(correct / n) * 100,
            consistency_rate=consistency,
            task_success_rate=(success / n) * 100,
            avg_latency_ms=lat_avg,
            min_latency_ms=lat_min,
            max_latency_ms=lat_max,
            std_latency_ms=lat_std,
            total_llm_calls=total_llm,
            iterations=n
        )

    def all_summaries(self) -> list[GroupSummary]:
        """Generate summaries for all group × scenario combinations."""
        groups = sorted(set(r.group for r in self.results))
        scenarios = sorted(set(r.scenario for r in self.results))
        summaries = []
        for group in groups:
            for scenario in scenarios:
                summaries.append(self.summarize(group, scenario))
        return summaries

    def clear(self):
        self.results.clear()
