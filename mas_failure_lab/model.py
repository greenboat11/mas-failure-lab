"""Discrete-time, synchronous, synthetic claim propagation model."""
from dataclasses import asdict, dataclass
import hashlib
import json
import math

from .agents import Agent, Decision, Exposure, Observation, ScriptedAgent

TRUTH = 7
FALSE = 9
ARMS = ("cascade", "isolated_seed", "independent", "common_cause")


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def uniform(seed: int, *key) -> float:
    """Keyed random numbers: independent of iteration order and unused draws."""
    digest = hashlib.sha256(canonical([seed, *key]).encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


@dataclass(frozen=True)
class Config:
    n: int = 16
    team_size: int = 4
    ticks: int = 24
    topology: str = "modular"
    within_probability: float = 0.7
    cross_probability: float = 0.1
    contacts: int = 2
    adoption: float = 0.65
    verification: float = 0.15
    memory_read: float = 0.5
    memory_ttl: int = 6
    recovery_delay: int = 5
    monitor_capacity: int = 1
    monitor_scaling: str = "fixed"
    monitor_latency: int = 2
    compute_scaling: str = "per_agent"
    compute_budget: int = 16
    exposure_probability: float = 0.0625
    arm: str = "cascade"

    def __post_init__(self):
        for name in ("n", "team_size", "ticks", "recovery_delay", "compute_budget"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("contacts", "memory_ttl", "monitor_capacity", "monitor_latency"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        for name in ("within_probability", "cross_probability", "adoption", "verification", "memory_read", "exposure_probability"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be a probability")
        if self.arm not in ARMS or self.topology not in ("modular", "ring", "complete"):
            raise ValueError("unknown arm or topology")
        if self.compute_scaling not in ("fixed", "per_agent") or self.monitor_scaling not in ("fixed", "proportional"):
            raise ValueError("unknown scaling treatment")


def graph(config: Config, seed: int) -> dict:
    edges = []
    for i in range(config.n):
        for j in range(i + 1, config.n):
            p = config.within_probability if i // config.team_size == j // config.team_size else config.cross_probability
            connected = (config.topology == "complete" or
                         (config.topology == "ring" and (j == i + 1 or (i == 0 and j == config.n - 1))) or
                         (config.topology == "modular" and uniform(seed, "graph", i, j) < p))
            if connected:
                edges.append([i, j])
    if config.arm != "cascade":
        edges = []
    return {
        "communication_edges": edges,
        "artifact_membership": [[i, "team-" + str(i // config.team_size)] for i in range(config.n)] if config.arm == "cascade" else [],
        "authority_edges": [["monitor", i] for i in range(config.n)],
    }


def simulate(config: Config, seed: int, agent: Agent | None = None) -> dict:
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    agent = agent or ScriptedAgent(config.verification, config.adoption)
    relationships = graph(config, seed)
    run_id = hashlib.sha256(canonical({"config": asdict(config), "seed": seed, "agent": agent.metadata()}).encode()).hexdigest()[:20]
    events: list[dict] = []

    def emit(kind, tick, actor=None, parents=(), roots=(), **data):
        event_id = len(events)
        events.append(dict(schema_version=1, run_id=run_id, event_id=event_id, tick=tick,
                           kind=kind, actor=actor, parents=list(parents), roots=sorted(set(roots)), **data))
        return event_id

    def root(kind, tick, **data):
        event_id = emit(kind, tick, **data)
        events[event_id]["roots"] = [event_id]
        return event_id

    emit("run_started", -1, config=asdict(config), seed=seed, agent=agent.metadata(), relationships=relationships)
    evidence = emit("document", -1, artifact="D0", value=TRUTH, text=Observation(0, 0, TRUTH, ()).document)
    state: list[int | None] = [None] * config.n  # last false-state event, not a probability
    onset = [0] * config.n
    ever = set()
    episodes = [0] * config.n
    memory: dict[int, tuple[int, int]] = {}  # team -> (write event, exclusive expiry)
    queue: dict[int, tuple[int, int]] = {}  # agent -> (due tick, state episode event)
    neighbors = [[] for _ in state]
    for i, j in relationships["communication_edges"]:
        neighbors[i].append(j)
        neighbors[j].append(i)

    def infect(i, tick, parent, reason, decision_id=None):
        if state[i] is not None:
            return
        parents = [parent] + ([decision_id] if decision_id is not None else [])
        state[i] = emit("deviation", tick, i, parents, events[parent]["roots"], value=FALSE, reason=reason)
        onset[i] = tick
        ever.add(i)
        episodes[i] += 1

    if config.arm in ("cascade", "isolated_seed"):
        source = root("seed_perturbation", 0, value=FALSE)
        infect(0, 0, source, "seed")
    else:
        # One-shot exposures; same marginal probability, different dependence.
        shared = uniform(seed, "exogenous", 0) < config.exposure_probability
        source = root("shared_shock", 0, value=FALSE) if config.arm == "common_cause" and shared else None
        for i in range(config.n):
            exposed = shared if config.arm == "common_cause" else uniform(seed, "exogenous", i) < config.exposure_probability
            if exposed:
                parent = source if source is not None else root("independent_error", 0, actor=i, value=FALSE)
                infect(i, 0, parent, "exogenous")

    series = []
    def snapshot(tick, decisions=0, messages=0):
        series.append(dict(tick=tick, active=sum(s is not None for s in state), affected=len(ever), backlog=len(queue), decisions=decisions, messages=messages))
        emit("snapshot", tick, **{k: v for k, v in series[-1].items() if k != "tick"})

    snapshot(0)
    for tick in range(1, config.ticks + 1):
        # Expiration and interventions happen before observing this tick's state.
        for team, (event_id, expiry) in list(memory.items()):
            if expiry <= tick:
                emit("artifact_expired", tick, parents=[event_id], team=team)
                del memory[team]
        capacity = config.monitor_capacity * (math.ceil(config.n / config.team_size) if config.monitor_scaling == "proportional" else 1)
        serviced = 0
        for i, (due, episode) in sorted(list(queue.items()), key=lambda item: (item[1][0], item[0])):
            if state[i] != episode:
                emit("review_cancelled", tick, i, [episode], reason="episode_already_resolved")
                del queue[i]
            elif due <= tick and serviced < capacity:
                emit("intervention", tick, i, [episode, evidence], delay=tick - onset[i])
                state[i] = None
                del queue[i]
                serviced += 1
        for i in range(config.n):
            if state[i] is not None and tick - onset[i] >= config.recovery_delay:
                emit("recovery", tick, i, [state[i], evidence], reason="scheduled_recheck")
                state[i] = None
        previous = state.copy()
        budget = config.n if config.compute_scaling == "per_agent" else min(config.n, config.compute_budget)
        active_agents = sorted(range(config.n), key=lambda i: (uniform(seed, "scheduler", tick, i), i))[:budget]
        pending: list[tuple[int, Observation, Decision, int]] = []
        message_count = 0
        for i in active_agents:
            exposures = []
            contacts = sorted(neighbors[i], key=lambda j: (uniform(seed, "contact", tick, i, j), j))[:config.contacts]
            for j in contacts:
                # Correct peer answers are logged too; this baseline only copies deviations.
                parent = previous[j] if previous[j] is not None else evidence
                value = FALSE if previous[j] is not None else TRUTH
                event_id = emit("message", tick, j, [parent], events[parent]["roots"], recipient=i, value=value)
                message_count += 1
                if value != TRUTH:
                    exposures.append(Exposure(event_id, value, "communication"))
            team = i // config.team_size
            if team in memory and uniform(seed, "read", tick, i) < config.memory_read:
                parent = memory[team][0]
                event_id = emit("artifact_read", tick, i, [parent], events[parent]["roots"], team=team, value=FALSE)
                exposures.append(Exposure(event_id, FALSE, "artifact"))
            obs = Observation(i, tick, FALSE if previous[i] is not None else TRUTH, tuple(exposures))
            draws = tuple(uniform(seed, "decision", tick, i, k) for k in range(3))
            decision = agent.decide(obs, draws)
            if not isinstance(decision, Decision) or type(decision.verify) is not bool:
                raise ValueError("agent must return a valid Decision")
            allowed = {x.event_id for x in exposures}
            if decision.adopt_event is not None and (type(decision.adopt_event) is not int or decision.adopt_event not in allowed):
                raise ValueError("agent cited an unavailable exposure")
            if decision.verify and decision.adopt_event is not None:
                raise ValueError("verify and adoption are mutually exclusive")
            event_id = emit("decision", tick, i, observation=asdict(obs), decision=asdict(decision), draws=draws)
            pending.append((i, obs, decision, event_id))
        for i, obs, decision, event_id in pending:
            if decision.verify:
                emit("verification", tick, i, [event_id, evidence] + ([state[i]] if state[i] is not None else []), was_deviating=state[i] is not None)
                state[i] = None
            elif decision.adopt_event is not None:
                infect(i, tick, decision.adopt_event, "adoption", event_id)
            parent = state[i] if state[i] is not None else evidence
            emit("answer", tick, i, [parent, event_id], events[parent]["roots"],
                 answer={"sample_count": FALSE if state[i] is not None else TRUTH, "citations": [parent]},
                 correct=state[i] is None)
        # One shared last-writer-wins slot per team, written only after all reads.
        for i in sorted(active_agents):
            if state[i] is not None and config.arm == "cascade" and config.memory_ttl > 0:
                parent = state[i]
                event_id = emit("artifact_write", tick, i, [parent], events[parent]["roots"], team=i // config.team_size, value=FALSE, expiry=tick + config.memory_ttl)
                memory[i // config.team_size] = (event_id, tick + config.memory_ttl)
        for i in range(config.n):
            if state[i] is not None and (i not in queue or queue[i][1] != state[i]):
                queue[i] = (tick + config.monitor_latency, state[i])
                emit("review_enqueued", tick, i, [state[i]], due=tick + config.monitor_latency)
        snapshot(tick, len(active_agents), message_count)

    # Extinction requires both no active deviations and no live contaminated artifacts.
    extinction = None
    active_ticks = [s["tick"] for s in series if s["active"]]
    if not any(s is not None for s in state) and not memory:
        # Earliest suffix with no activity; artifact expiry may occur later than last activity.
        last_activity = max(active_ticks, default=-1)
        last_expiry = max((e["tick"] for e in events if e["kind"] == "artifact_expired"), default=0)
        extinction = max(last_activity + 1, last_expiry)
    answers = [e for e in events if e["kind"] == "answer"]
    offspring = {}
    for event in events:
        if event["kind"] == "deviation" and event["reason"] == "adoption":
            parent = events[event["parents"][0]]
            while parent["kind"] in ("message", "artifact_read", "artifact_write"):
                parent = events[parent["parents"][0]]
            offspring[str(parent["event_id"])] = offspring.get(str(parent["event_id"]), 0) + 1
    metrics = dict(affected_fraction=len(ever) / config.n, final_active_fraction=series[-1]["active"] / config.n,
                   peak_active_fraction=max(s["active"] for s in series) / config.n,
                   active_agent_ticks=sum(s["active"] for s in series[1:]),
                   recurrence_count=sum(max(0, e - 1) for e in episodes),
                   extinction_tick=extinction, right_censored=extinction is None,
                   last_active_tick=max(active_ticks, default=None),
                   wrong_answer_fraction=sum(not e["correct"] for e in answers) / len(answers),
                   max_backlog=max(s["backlog"] for s in series),
                   total_decisions=sum(s["decisions"] for s in series), total_messages=sum(s["messages"] for s in series),
                   attributable_offspring=offspring)
    return dict(run_id=run_id, config=asdict(config), seed=seed, agent=agent.metadata(), relationships=relationships,
                metrics=metrics, series=series, events=events)
