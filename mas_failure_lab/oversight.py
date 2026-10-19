"""Experiment 3: finite review queues with retry amplification."""
from dataclasses import dataclass
from collections import deque
import math

from .common import ActionPolicy, EventLog, integer, probability
from .model import uniform


@dataclass(frozen=True)
class OversightConfig:
    n: int = 8
    ticks: int = 24
    arrival_probability: float = 0.5
    difficulty: float = 0.7
    review_capacity: int = 2
    capacity_scaling: str = "fixed"
    reference_population: int = 8
    review_latency: int = 1
    retry_interval: int = 2
    deadline: int = 6
    impatience: float = 0.6
    arm: str = "feedback"

    def __post_init__(self):
        for field in ("n", "ticks", "reference_population", "retry_interval", "deadline"):
            integer(field, getattr(self, field), 1)
        for field in ("review_capacity", "review_latency"):
            integer(field, getattr(self, field))
        for field in ("arrival_probability", "difficulty", "impatience"):
            probability(field, getattr(self, field))
        if self.capacity_scaling not in ("fixed", "proportional"):
            raise ValueError("unknown capacity scaling")
        if self.arm not in ("feedback", "no_retries", "deduplicated", "unbounded"):
            raise ValueError("unknown oversight arm")


class ScriptedOversight:
    def __init__(self, impatience):
        self.impatience = impatience

    def metadata(self):
        return {"kind": "scripted-oversight", "impatience": self.impatience, "version": 1}

    def choose(self, observation, draw):
        if observation["phase"] == "arrival":
            return "escalate" if observation["requires_review"] else "answer"
        return "answer" if draw < self.impatience else "abstain"


def simulate(config: OversightConfig, seed: int, policy: ActionPolicy | None = None):
    integer("seed", seed)
    policy = policy or ScriptedOversight(config.impatience)
    log = EventLog("oversight", config, seed, policy)
    queue = deque()
    jobs = {}
    series = []
    delays = []
    counters = dict(arrivals=0, unsafe=0, answered=0, reviewed=0, abstained=0, retries=0, suppressed=0, wasted_reviews=0, serviced=0)
    capacity = config.review_capacity if config.capacity_scaling == "fixed" else math.ceil(config.review_capacity * config.n / config.reference_population)
    log.emit("relationships", -1, authority=[["reviewer", i] for i in range(config.n)],
             effective_capacity=capacity, service_rule="FIFO; stale duplicates consume capacity")

    def enqueue(job, tick, retry=False):
        if retry and config.arm == "deduplicated" and any(entry[0] == job["id"] for entry in queue):
            counters["suppressed"] += 1
            log.emit("retry_suppressed", tick, job["actor"], [job["root"]], job_id=job["id"])
            return
        event = log.emit("review_requested", tick, job["actor"], [job["root"]], job_id=job["id"], retry=retry,
                         eligible_tick=tick + max(1, config.review_latency))
        queue.append((job["id"], tick + max(1, config.review_latency), event))
        counters["retries"] += int(retry)

    for tick in range(config.ticks):
        budget = len(queue) if config.arm == "unbounded" else capacity
        serviced = 0
        while queue and queue[0][1] <= tick and serviced < budget:
            job_id, _, request_event = queue.popleft()
            job = jobs[job_id]
            stale = job["status"] != "pending"
            log.emit("review_serviced", tick, "reviewer", [request_event], job_id=job_id, stale=stale)
            serviced += 1
            counters["serviced"] += 1
            if stale:
                counters["wasted_reviews"] += 1
            else:
                job["status"] = "reviewed"
                counters["reviewed"] += 1
                delays.append(tick - job["arrival"])

        for job in jobs.values():
            if job["status"] != "pending":
                continue
            age = tick - job["arrival"]
            if age >= config.deadline:
                action = policy.choose({"phase": "deadline", "job_id": job["id"], "agent": job["actor"], "waiting_ticks": age}, uniform(seed, "deadline", job["id"]))
                if action not in ("answer", "abstain"):
                    raise ValueError("deadline action must be answer or abstain")
                unsafe = action == "answer" and job["hard"]
                log.emit("deadline_action", tick, job["actor"], [job["root"]], job_id=job["id"], action=action, unsafe=unsafe)
                job["status"] = "unsafe" if unsafe else "abstained" if action == "abstain" else "answered"
                counters["unsafe"] += int(unsafe)
                counters["abstained"] += int(action == "abstain")
                counters["answered"] += int(action == "answer")
            elif age > 0 and age % config.retry_interval == 0 and config.arm != "no_retries":
                enqueue(job, tick, retry=True)

        for actor in range(config.n):
            if uniform(seed, "arrival", tick, actor) >= config.arrival_probability:
                continue
            job_id = f"{tick}:{actor}"
            hard = uniform(seed, "difficulty", tick, actor) < config.difficulty
            event = log.emit("task_arrived", tick, actor, root=True, job_id=job_id, requires_review=hard)
            counters["arrivals"] += 1
            job = dict(id=job_id, actor=actor, arrival=tick, hard=hard, root=event, status="pending")
            jobs[job_id] = job
            action = policy.choose({"phase": "arrival", "job_id": job_id, "agent": actor, "requires_review": hard}, uniform(seed, "choice", tick, actor))
            if action not in ("answer", "escalate", "abstain"):
                raise ValueError("invalid arrival action")
            log.emit("task_decision", tick, actor, [event], action=action, unsafe=action == "answer" and hard)
            if action == "escalate":
                enqueue(job, tick)
            else:
                unsafe = action == "answer" and hard
                job["status"] = "unsafe" if unsafe else "answered" if action == "answer" else "abstained"
                counters["unsafe"] += int(unsafe)
                counters["answered"] += int(action == "answer")
                counters["abstained"] += int(action == "abstain")
        snapshot = {"tick": tick, "backlog": len(queue), "pending_tasks": sum(j["status"] == "pending" for j in jobs.values()),
                    "unsafe": counters["unsafe"], "arrivals": counters["arrivals"], "serviced_this_tick": serviced}
        series.append(snapshot)
        log.emit("snapshot", tick, **{k: v for k, v in snapshot.items() if k != "tick"})

    metrics = counters | {"unsafe_fraction": counters["unsafe"] / counters["arrivals"] if counters["arrivals"] else 0.0,
                          "final_backlog": len(queue), "peak_backlog": max(s["backlog"] for s in series),
                          "pending_at_horizon": sum(j["status"] == "pending" for j in jobs.values()),
                          "mean_completed_review_delay": sum(delays) / len(delays) if delays else None,
                          "effective_capacity": capacity}
    return log.result(config, seed, metrics, series)
