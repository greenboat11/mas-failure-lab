"""Version-1 event envelopes, preserving legacy explicit-root semantics."""
from dataclasses import asdict
import hashlib

from .serialization import canonical, record_config


class ExplicitEventLog:
    def __init__(self, run_id):
        self.run_id, self.events = run_id, []

    def emit(self, kind, tick, actor=None, parents=(), roots=(), **data):
        event_id = len(self.events)
        if any(type(p) is not int or p < 0 or p >= event_id for p in parents):
            raise ValueError("event parents must refer to earlier events")
        self.events.append(dict(schema_version=1, run_id=self.run_id, event_id=event_id, tick=tick,
                                kind=kind, actor=actor, parents=list(parents), roots=sorted(set(roots)), **data))
        return event_id


class EventLog(ExplicitEventLog):
    def __init__(self, experiment, config, seed, policy):
        identity = {"experiment": experiment, "engine_version": 1, "config": record_config(config),
                    "seed": seed, "policy": policy.metadata()}
        super().__init__(hashlib.sha256(canonical(identity).encode()).hexdigest()[:20])
        self.emit("run_started", -1, **identity)

    def emit(self, kind, tick, actor=None, parents=(), *, root=False, **data):
        roots = [len(self.events)] if root else sorted({r for p in parents for r in self.events[p]["roots"]})
        return super().emit(kind, tick, actor, parents, roots, **data)

    def result(self, config, seed, metrics, series):
        return {"run_id": self.run_id, "config": record_config(config), "seed": seed,
                "metrics": metrics, "series": series, "events": self.events}
