import random


def backoff_delay(attempt: int, base: float, cap: float, rng: random.Random | None = None) -> float:
    rng = rng or random
    ceiling = min(cap, base * (2 ** attempt))
    return ceiling / 2 + rng.uniform(0, ceiling / 2)


def should_retry(attempt: int, max_attempts: int) -> bool:
    return attempt + 1 < max_attempts
