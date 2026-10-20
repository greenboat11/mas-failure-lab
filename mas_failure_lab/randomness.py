"""Versioned semantic random keys and independently controlled seed domains."""
from dataclasses import dataclass
import hashlib

from .serialization import canonical


def uniform(seed, *key):
    digest = hashlib.sha256(canonical([seed, *key]).encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


@dataclass(frozen=True)
class RandomConfig:
    random_scheme: str = "sha256-keyed-v1"
    topology_seed: int | None = None
    task_seed: int | None = None
    policy_seed: int | None = None
    trial_id: str = "0"


def validate_random(config):
    if config.random_scheme not in ("sha256-keyed-v1", "split-v2"):
        raise ValueError("unknown random scheme")
    for name in ("topology_seed", "task_seed", "policy_seed"):
        value = getattr(config, name)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError(f"{name} must be a nonnegative integer or null")
    if not isinstance(config.trial_id, str) or not config.trial_id:
        raise ValueError("trial_id must be a nonempty string")
    if config.random_scheme == "sha256-keyed-v1" and any(getattr(config, n) is not None for n in ("topology_seed", "task_seed", "policy_seed")):
        raise ValueError("explicit seed domains require split-v2")


def seed_plan(config, seed):
    return {"scheme": config.random_scheme, "topology_seed": config.topology_seed if config.topology_seed is not None else seed,
            "task_seed": config.task_seed if config.task_seed is not None else seed,
            "policy_seed": config.policy_seed if config.policy_seed is not None else seed, "trial_id": config.trial_id}


def draw(config, seed, *key):
    if config.random_scheme == "sha256-keyed-v1":
        return uniform(seed, *key)
    domain = "topology" if key[0] in ("graph", "route") else "task" if key[0] in ("exogenous", "arrival", "difficulty", "truth", "claim") else "policy"
    actual_seed = seed_plan(config, seed)[domain + "_seed"]
    # Trial identity identifies repeated provider samples; it does not alter the
    # environment or scripted random keys. Vary policy_seed for scripted trials.
    return uniform(actual_seed, "split-v2", domain, *key)
