"""Analytical checks with explicit domains of validity; no external dependencies."""
import argparse
import json


def composition_disclosure(retention, relays):
    if not 0 <= retention <= 1 or type(relays) is not int or relays < 0:
        raise ValueError("invalid retention or relay count")
    return 1 - retention ** (relays + 2)


def offered_load(n, arrival_probability, difficulty, capacity):
    demand = n * arrival_probability * difficulty
    if capacity == 0:
        return {"nominal_offered_review_load": demand, "rho_0": None,
                "rho_0_status": "infinite" if demand > 0 else "undefined_zero_over_zero"}
    return {"nominal_offered_review_load": demand, "rho_0": demand / capacity, "rho_0_status": "finite"}


def fifo_backlog(arrivals, capacity):
    """One-tick latency, service before arrivals, no retries/cancellation."""
    if type(capacity) is not int or capacity < 0 or any(type(a) is not int or a < 0 for a in arrivals):
        raise ValueError("nonnegative integer queue inputs required")
    queue, result = 0, []
    for count in arrivals:
        queue = max(0, queue - capacity) + count
        result.append(queue)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicates", type=int, default=1000)
    args = parser.parse_args()
    if args.replicates < 1:
        parser.error("replicates must be positive")
    from .composition import CompositionConfig, simulate
    results = []
    for relays in (0, 2):
        config = CompositionConfig(relays=relays, provenance_retention=0.6, authorization="declared", audit_coalitions=False)
        observed = sum(simulate(config, seed)["metrics"]["global_violation"] for seed in range(args.replicates)) / args.replicates
        results.append({"relays": relays, "expected": composition_disclosure(0.6, relays), "observed": observed})
    print(json.dumps({"composition": results, "queue_backlog_example": fifo_backlog([2] * 5, 1)}, indent=2))


if __name__ == "__main__":
    main()
