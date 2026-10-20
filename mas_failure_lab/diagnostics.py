"""Derived measurements for new reports without changing legacy replay records."""
from .benchmarks import offered_load


def composition_metrics(result):
    publications = [e for e in result["events"] if e["kind"] == "publication"]
    return {"task_completed": bool(publications), "authorized_task_completion": any(not e["global_violation"] for e in publications)}


def oversight_metrics(config, result):
    events = result["events"]
    requests = {e["event_id"]: e for e in events if e["kind"] == "review_requested"}
    serviced = {e["parents"][0] for e in events if e["kind"] == "review_serviced"}
    resolved = {e.get("job_id", events[e["parents"][0]].get("job_id")) for e in events if (e["kind"] == "review_serviced" and not e["stale"]) or e["kind"] == "deadline_action" or (e["kind"] == "task_decision" and e["action"] != "escalate")}
    pending_requests = [e for eid, e in requests.items() if eid not in serviced]
    nominal = offered_load(config.n, config.arrival_probability, config.difficulty, result["metrics"]["effective_capacity"])
    if config.arm == "unbounded":
        nominal.update(rho_0=0.0, rho_0_status="unbounded_service")
    return nominal | {"original_review_demand": sum(not e["retry"] for e in requests.values()),
                      "effective_review_capacity": result["metrics"]["effective_capacity"] if config.arm != "unbounded" else None,
                      "review_capacity_status": "finite" if config.arm != "unbounded" else "unbounded",
                      "retry_demand": sum(e["retry"] for e in requests.values()),
                      "retry_attempts": sum(e["retry"] for e in requests.values()) + sum(e["kind"] == "retry_suppressed" for e in events),
                      "stale_requests": sum(e["job_id"] in resolved for e in pending_requests),
                      "live_requests": sum(e["job_id"] not in resolved for e in pending_requests)}
