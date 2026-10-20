"""Experiment 3: finite review queues with retry amplification."""
from typing import ClassVar
from .randomness import RandomConfig, draw, validate_random, seed_plan
from .serialization import record_config
from dataclasses import dataclass
from collections import deque
import math

from .common import ActionPolicy, EventLog, integer, probability
from .model import uniform
from .benchmarks import offered_load


@dataclass(frozen=True)
class OversightConfig(RandomConfig):
    legacy_fields: ClassVar[tuple] = ('n', 'ticks', 'arrival_probability', 'difficulty', 'review_capacity', 'capacity_scaling', 'reference_population', 'review_latency', 'retry_interval', 'deadline', 'impatience', 'arm')
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
    baseline: str = "oracle"
    review_sensitivity: float = 1.0
    review_specificity: float = 1.0
    review_accuracy: float = 1.0
    retry_mode: str = "environment"
    retry_probability: float = 0.5

    def __post_init__(self):
        validate_random(self)
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
        for name in ("review_sensitivity", "review_specificity", "review_accuracy", "retry_probability"):
            probability(name, getattr(self, name))
        if self.baseline not in ("oracle", "extended") or self.retry_mode not in ("environment", "agent"):
            raise ValueError("invalid oversight extension")
        if self.baseline == "oracle" and (self.review_sensitivity != 1 or self.review_specificity != 1 or self.review_accuracy != 1 or self.retry_mode != "environment"):
            raise ValueError("select baseline=extended for uncertain estimates, imperfect review or agent retries")


class ScriptedOversight:
    def __init__(self, impatience, retry_probability=None):
        self.impatience = impatience
        self.retry_probability = retry_probability

    def metadata(self):
        result = {"kind": "scripted-oversight", "impatience": self.impatience, "version": 1}
        if self.retry_probability is not None:
            result["retry_probability"] = self.retry_probability
        return result

    def choose(self, observation, draw):
        if observation["phase"] == "arrival":
            return "escalate" if observation["requires_review"] else "answer"
        if observation["phase"] == "retry":
            return "retry" if draw < self.retry_probability else "wait"
        return "answer" if draw < self.impatience else "abstain"


def simulate(config: OversightConfig, seed: int, policy: ActionPolicy | None = None):
    integer("seed", seed)
    policy = policy or ScriptedOversight(config.impatience, config.retry_probability if config.retry_mode == "agent" else None)
    log = EventLog("oversight", config, seed, policy)
    queue = deque()
    jobs = {}
    series = []
    delays = []
    counters = dict(arrivals=0, unsafe=0, answered=0, reviewed=0, abstained=0, retries=0, suppressed=0, wasted_reviews=0, serviced=0)
    original_requests = retry_attempts = review_errors = hard_arrivals = 0
    extended = any(key not in config.legacy_fields for key in record_config(config))
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
                unsafe_review = config.review_accuracy < 1 and draw(config, seed, "review_accuracy", job_id) >= config.review_accuracy and job["hard"]
                job["status"] = "reviewed"
                counters["reviewed"] += 1
                if unsafe_review:
                    counters["unsafe"] += 1
                    review_errors += 1
                if extended:
                    log.emit("review_outcome", tick, "reviewer", [request_event], job_id=job_id, unsafe=unsafe_review)
                delays.append(tick - job["arrival"])

        for job in jobs.values():
            if job["status"] != "pending":
                continue
            age = tick - job["arrival"]
            if age >= config.deadline:
                action = policy.choose({"phase": "deadline", "job_id": job["id"], "agent": job["actor"], "waiting_ticks": age}, draw(config, seed, "deadline", job["id"]))
                if action not in ("answer", "abstain"):
                    raise ValueError("deadline action must be answer or abstain")
                unsafe = action == "answer" and job["hard"]
                log.emit("deadline_action", tick, job["actor"], [job["root"]], job_id=job["id"], action=action, unsafe=unsafe)
                job["status"] = "unsafe" if unsafe else "abstained" if action == "abstain" else "answered"
                counters["unsafe"] += int(unsafe)
                counters["abstained"] += int(action == "abstain")
                counters["answered"] += int(action == "answer")
            elif age > 0 and age % config.retry_interval == 0 and config.arm != "no_retries":
                if config.retry_mode == "agent":
                    observation = {"phase": "retry", "job_id": job["id"], "agent": job["actor"], "waiting_ticks": age,
                                   "prior_retry_attempts": job.get("retry_attempts", 0)}
                    action = policy.choose(observation, draw(config, seed, "retry_choice", job["id"], tick))
                    if action not in ("retry", "wait"):
                        raise ValueError("retry action must be retry or wait")
                    log.emit("retry_decision", tick, job["actor"], [job["root"]], observation=observation, action=action)
                    if action == "wait":
                        continue
                retry_attempts += 1
                job["retry_attempts"] = job.get("retry_attempts", 0) + 1
                enqueue(job, tick, retry=True)

        for actor in range(config.n):
            if draw(config, seed, "arrival", tick, actor) >= config.arrival_probability:
                continue
            job_id = f"{tick}:{actor}"
            hard = draw(config, seed, "difficulty", tick, actor) < config.difficulty
            hard_arrivals += int(hard)
            event = log.emit("task_arrived", tick, actor, root=True, job_id=job_id, requires_review=hard)
            counters["arrivals"] += 1
            job = dict(id=job_id, actor=actor, arrival=tick, hard=hard, root=event, status="pending")
            jobs[job_id] = job
            estimated_need = hard
            if config.baseline == "extended":
                estimate = draw(config, seed, "review_estimate", tick, actor)
                estimated_need = estimate < config.review_sensitivity if hard else estimate >= config.review_specificity
                log.emit("review_need_estimated", tick, actor, [event], estimated_need=estimated_need)
            action = policy.choose({"phase": "arrival", "job_id": job_id, "agent": actor, "requires_review": estimated_need}, draw(config, seed, "choice", tick, actor))
            if action not in ("answer", "escalate", "abstain"):
                raise ValueError("invalid arrival action")
            log.emit("task_decision", tick, actor, [event], action=action, unsafe=action == "answer" and hard)
            if action == "escalate":
                original_requests += 1
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
        if extended:
            snapshot.update(original_review_demand=original_requests, retry_attempts=retry_attempts, retry_demand=counters["retries"],
                            stale_requests=sum(jobs[item[0]]["status"] != "pending" for item in queue))
        log.emit("snapshot", tick, **{k: v for k, v in snapshot.items() if k != "tick"})

    metrics = counters | {"unsafe_fraction": counters["unsafe"] / counters["arrivals"] if counters["arrivals"] else 0.0,
                          "final_backlog": len(queue), "peak_backlog": max(s["backlog"] for s in series),
                          "pending_at_horizon": sum(j["status"] == "pending" for j in jobs.values()),
                          "mean_completed_review_delay": sum(delays) / len(delays) if delays else None,
                          "effective_capacity": capacity}
    if extended:
        nominal = offered_load(config.n, config.arrival_probability, config.difficulty, capacity)
        if config.arm == "unbounded":
            nominal.update(rho_0=0.0, rho_0_status="unbounded_service")
        metrics.update(nominal, original_review_demand=original_requests, retry_attempts=retry_attempts,
                       effective_review_capacity=capacity if config.arm != "unbounded" else None,
                       review_capacity_status="finite" if config.arm != "unbounded" else "unbounded",
                       retry_demand=counters["retries"], hard_task_arrivals=hard_arrivals,
                       stale_requests=sum(jobs[item[0]]["status"] != "pending" for item in queue),
                       live_requests=sum(jobs[item[0]]["status"] == "pending" for item in queue), review_errors=review_errors,
                       authorized_task_completion=(counters["answered"] + counters["reviewed"] - counters["unsafe"]) / counters["arrivals"] if counters["arrivals"] else 0.0)
    return log.result(config, seed, metrics, series)
