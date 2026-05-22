"""Strategy C: Leader agent mediation."""

import time


def resolve_leader(value_a: str, value_b: str,
                   leader_arbitrate_fn) -> tuple[str, str, float]:
    """Resolve conflict by having the leader agent arbitrate.

    The leader_arbitrate_fn is a callable that takes (value_a, value_b) and returns a chosen value.
    Returns (resolved_value, chosen_strategy, latency_ms).
    """
    start = time.time()
    chosen = leader_arbitrate_fn(value_a, value_b)
    latency_ms = (time.time() - start) * 1000
    return chosen, "leader_mediation", latency_ms
