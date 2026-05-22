"""Strategy B: Trust score priority resolution."""

import time


def resolve_trust_score(value_a: str, value_b: str,
                        trust_a: float, trust_b: float) -> tuple[str, str, float]:
    """Resolve conflict by picking the value from the agent with higher trust score.

    Returns (resolved_value, chosen_strategy, latency_ms).
    """
    start = time.time()
    if trust_a == trust_b:
        chosen = value_a
        strategy = "trust_tie_a"
    elif trust_a > trust_b:
        chosen = value_a
        strategy = "trust_a"
    else:
        chosen = value_b
        strategy = "trust_b"
    latency_ms = (time.time() - start) * 1000
    return chosen, strategy, latency_ms
