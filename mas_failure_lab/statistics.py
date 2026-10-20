"""Run-level bootstrap summaries shared by the experiment runners."""
import random
import statistics


def interval(values, seed=0, repetitions=1000):
    if not values or repetitions < 40:
        raise ValueError("nonempty sample and at least 40 repetitions required")
    rng = random.Random(seed)
    samples = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(repetitions))
    return statistics.mean(values), samples[int(0.025 * repetitions)], samples[int(0.975 * repetitions)]
