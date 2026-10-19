"""Shared event envelope and restricted action-policy boundary for new engines."""
from dataclasses import asdict
import hashlib
from typing import Protocol

from .model import canonical


class ActionPolicy(Protocol):
    def metadata(self) -> dict: ...
    def choose(self, observation: dict, draw: float) -> str: ...


class EventLog:
    def __init__(self, experiment, config, seed, policy):
        identity = {"experiment": experiment, "engine_version": 1, "config": asdict(config),
                    "seed": seed, "policy": policy.metadata()}
        self.run_id = hashlib.sha256(canonical(identity).encode()).hexdigest()[:20]
        self.events = []
        self.emit("run_started", -1, **identity)

    def emit(self, kind, tick, actor=None, parents=(), *, root=False, **data):
        event_id = len(self.events)
        if any(type(p) is not int or p < 0 or p >= event_id for p in parents):
            raise ValueError("event parents must refer to earlier events")
        roots = [event_id] if root else sorted({r for p in parents for r in self.events[p]["roots"]})
        self.events.append({"schema_version": 1, "run_id": self.run_id, "event_id": event_id,
                            "tick": tick, "kind": kind, "actor": actor, "parents": list(parents), "roots": roots, **data})
        return event_id

    def result(self, config, seed, metrics, series):
        return {"run_id": self.run_id, "config": asdict(config), "seed": seed,
                "metrics": metrics, "series": series, "events": self.events}


def probability(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be a probability")


def integer(name, value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
