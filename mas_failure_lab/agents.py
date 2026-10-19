"""Interchangeable policies. The environment owns truth, provenance and effects."""
from dataclasses import asdict, dataclass
from typing import Callable, Protocol


@dataclass(frozen=True)
class Exposure:
    event_id: int
    value: int
    channel: str


@dataclass(frozen=True)
class Observation:
    agent: int
    tick: int
    current_value: int
    exposures: tuple[Exposure, ...]
    document: str = "Document D0: the synthetic station recorded 7 samples."
    task: str = "Report the station's sample count as a structured integer answer."


@dataclass(frozen=True)
class Decision:
    verify: bool = False
    adopt_event: int | None = None


class Agent(Protocol):
    def metadata(self) -> dict: ...
    def decide(self, observation: Observation, draws: tuple[float, float, float]) -> Decision: ...


@dataclass
class ScriptedAgent:
    verification: float
    adoption: float

    def metadata(self) -> dict:
        return {"kind": "scripted", "verification": self.verification, "adoption": self.adoption}

    def decide(self, observation: Observation, draws: tuple[float, float, float]) -> Decision:
        if draws[0] < self.verification:
            return Decision(verify=True)
        if observation.exposures and draws[1] < self.adoption:
            chosen = min(int(draws[2] * len(observation.exposures)), len(observation.exposures) - 1)
            return Decision(adopt_event=observation.exposures[chosen].event_id)
        return Decision()


class LLMAgent:
    """Provider-neutral adapter; callers supply transport and record model settings.

    Transport receives JSON-compatible observations and returns exactly
    {"verify": bool, "adopt_event": int | null}. No provider SDK or network calls
    are built in. Requests/responses are recorded in decision events. Exceptions
    abort the run instead of silently substituting a scripted response.
    """

    def __init__(self, transport: Callable[[dict], dict], *, model: str, settings: dict):
        self.transport, self.model, self.settings = transport, model, dict(settings)

    def metadata(self) -> dict:
        return {"kind": "llm", "model": self.model, "settings": self.settings}

    def decide(self, observation: Observation, draws: tuple[float, float, float]) -> Decision:
        response = self.transport(asdict(observation))
        if not isinstance(response, dict) or set(response) != {"verify", "adopt_event"}:
            raise ValueError("LLM response must contain exactly verify and adopt_event")
        if type(response["verify"]) is not bool:
            raise ValueError("verify must be a boolean")
        value = response["adopt_event"]
        if value is not None and type(value) is not int:
            raise ValueError("adopt_event must be an integer or null")
        return Decision(**response)
