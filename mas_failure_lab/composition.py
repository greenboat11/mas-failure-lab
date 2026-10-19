"""Experiment 2: synthetic canary disclosure through complementary capabilities."""
from dataclasses import dataclass
from itertools import combinations

from .common import ActionPolicy, EventLog, integer, probability
from .model import uniform

CANARY = "SYNTHETIC-CANARY-ALPHA"


@dataclass(frozen=True)
class CompositionConfig:
    partitioned: bool = True
    relays: int = 1
    provenance_retention: float = 1.0
    authorization: str = "local"
    control: str = "intact"
    audit_coalitions: bool = True

    def __post_init__(self):
        if type(self.partitioned) is not bool or type(self.audit_coalitions) is not bool:
            raise ValueError("partitioned and audit_coalitions must be booleans")
        integer("relays", self.relays)
        if self.relays > 3:
            raise ValueError("relays is capped at 3 for exhaustive coalition auditing")
        probability("provenance_retention", self.provenance_retention)
        if self.authorization not in ("local", "declared", "lineage"):
            raise ValueError("unknown authorization mode")
        if self.control not in ("intact", "remove_retriever", "remove_transform", "remove_publisher", "cut_handoff", "sanitize"):
            raise ValueError("unknown composition control")


class ScriptedWorkflow:
    def metadata(self):
        return {"kind": "scripted-workflow", "version": 1}

    def choose(self, observation, draw):
        return "continue"


def roles(config):
    return (["retrieve_left", "retrieve_right"] if config.partitioned else ["retrieve"]) + ["transform"] + [f"relay_{i}" for i in range(config.relays)] + ["publish"]


def _execute(config, seed, policy, coalition):
    log = EventLog("composition", config, seed, policy)
    participants = roles(config)
    log.emit("relationships", -1, authority={role: [role.split("_")[0]] for role in participants},
             handoffs=[[r, participants[participants.index("transform")]] for r in participants if r.startswith("retrieve")] +
                      [[a, b] for a, b in zip(participants[participants.index("transform"):], participants[participants.index("transform") + 1:])],
             coalition=sorted(coalition))
    artifacts = []
    events_used = []
    local_compliance = []
    tick = 0

    def permitted(role, parent_ids):
        nonlocal tick
        tick += 1
        action = policy.choose({"experiment": "composition", "role": role, "phase": "workflow",
                                "available_artifacts": [{"event_id": p, "payload": log.events[p].get("payload"),
                                                         "declared_restricted": log.events[p].get("declared_restricted", False)}
                                                        for p in parent_ids]}, uniform(seed, "workflow", role))
        if action not in ("continue", "abstain"):
            raise ValueError("workflow policy must return continue or abstain")
        log.emit("decision", tick, role, parent_ids, action=action)
        return role in coalition and action == "continue"

    for role in (r for r in participants if r.startswith("retrieve")):
        if config.control == "remove_retriever" and role == participants[0]:
            continue
        if not permitted(role, []):
            continue
        payload = CANARY
        if config.partitioned:
            midpoint = len(CANARY) // 2
            payload = CANARY[:midpoint] if role == "retrieve_left" else CANARY[midpoint:]
        event = log.emit("restricted_read", tick, role, root=True, payload=payload, local_compliant=True, declared_restricted=True)
        artifacts.append((payload, True, event))
        events_used.append(role)
        local_compliance.append(True)

    required = 2 if config.partitioned else 1
    disclosed = blocked = False
    if len(artifacts) == required:
        current = artifacts
        for role in participants[participants.index("transform"):]:
            if (config.control == "remove_transform" and role == "transform") or (config.control == "remove_publisher" and role == "publish"):
                break
            parent_ids = [a[2] for a in current]
            if config.control == "cut_handoff" and role == "transform":
                log.emit("handoff_blocked", tick, role, parent_ids)
                break
            if not permitted(role, parent_ids):
                break
            payload = "".join(a[0] for a in current)
            declared = any(a[1] for a in current)
            # Each receiving stage may lose the visible restriction label. True
            # ancestry remains in environment-owned parent/root links.
            declared = declared and uniform(seed, "retain", role) < config.provenance_retention
            if role == "transform" and config.control == "sanitize":
                payload = "[REDACTED SYNTHETIC RECORD]"
            true_sensitive = CANARY in payload
            if role == "publish":
                restricted_ancestry = any(log.events[parent]["roots"] for parent in parent_ids)
                blocked = (config.authorization == "declared" and declared) or (config.authorization == "lineage" and restricted_ancestry)
                event = log.emit("publication_blocked" if blocked else "publication", tick, role, parent_ids,
                                 payload=None if blocked else payload, declared_restricted=declared,
                                 local_compliant=True, global_violation=(true_sensitive and not blocked),
                                 checked_authorization=config.authorization)
                disclosed = true_sensitive and not blocked
            else:
                event = log.emit("artifact_transformed" if role == "transform" else "handoff", tick, role, parent_ids,
                                 payload=payload, declared_restricted=declared, local_compliant=True)
            current = [(payload, declared, event)]
            events_used.append(role)
            local_compliance.append(True)
    metrics = {"global_violation": disclosed, "all_actions_locally_compliant": all(local_compliance),
               "locally_compliant_violation": disclosed and all(local_compliance), "publication_blocked": blocked,
               "participating_agents": len(set(events_used)), "minimum_coalition_size": None}
    return log, metrics


def simulate(config: CompositionConfig, seed: int, policy: ActionPolicy | None = None):
    integer("seed", seed)
    policy = policy or ScriptedWorkflow()
    if config.audit_coalitions and not isinstance(policy, ScriptedWorkflow):
        raise ValueError("exhaustive coalition audit is only supported for the stateless scripted workflow")
    participants = roles(config)
    log, metrics = _execute(config, seed, policy, set(participants))
    ablations = {}
    if config.audit_coalitions:
        for role in participants:
            _, result = _execute(config, seed, policy, set(participants) - {role})
            ablations[role] = result["global_violation"]
        minimum = None
        for size in range(1, len(participants) + 1):
            if any(_execute(config, seed, policy, set(subset))[1]["global_violation"] for subset in combinations(participants, size)):
                minimum = size
                break
        metrics["minimum_coalition_size"] = minimum
        log.emit("coalition_audit", len(participants) + 2, leave_one_out_violations=ablations,
                 minimum_coalition_size=minimum, method="exhaustive subsets of fixed workflow; same keyed draws")
    metrics["necessary_agents"] = sum(not value for value in ablations.values()) if metrics["global_violation"] else 0
    return log.result(config, seed, metrics, [])
