"""Strategy A: Timestamp priority resolution."""

import time


def resolve_timestamp(value_a: str, value_b: str,
                      ts_a: float, ts_b: float) -> tuple[str, str, float]:
    """Resolve conflict by picking the value with the latest timestamp.

    Returns (resolved_value, chosen_strategy, latency_ms).
    """
    start = time.time()
    chosen = value_a if ts_a >= ts_b else value_b
    strategy = "timestamp_a" if ts_a >= ts_b else "timestamp_b"
    latency_ms = (time.time() - start) * 1000
    return chosen, strategy, latency_ms
