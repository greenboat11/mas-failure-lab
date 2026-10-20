"""Shared event envelope and restricted action-policy boundary for new engines."""
from dataclasses import asdict
import hashlib
from typing import Protocol

from .events import EventLog


class ActionPolicy(Protocol):
    def metadata(self) -> dict: ...
    def choose(self, observation: dict, draw: float) -> str: ...


def probability(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be a probability")


def integer(name, value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
