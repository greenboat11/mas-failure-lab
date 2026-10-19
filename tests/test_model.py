from dataclasses import replace
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from mas_failure_lab.agents import Decision, LLMAgent, ScriptedAgent
from mas_failure_lab.experiment import expand, run_sweep
from mas_failure_lab.model import Config, graph, simulate


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.base = Config(n=4, team_size=2, ticks=5, topology="complete", verification=0,
                           adoption=1, contacts=3, memory_ttl=0, recovery_delay=10, monitor_capacity=0)

    def test_deterministic_replay(self):
        self.assertEqual(simulate(self.base, 123), simulate(self.base, 123))

    def test_synchronous_one_hop_per_tick(self):
        run = simulate(replace(self.base, topology="ring", ticks=1), 0)
        self.assertEqual(run["series"][-1]["active"], 3)
        self.assertEqual({e["actor"] for e in run["events"] if e["kind"] == "deviation"}, {0, 1, 3})

    def test_complete_graph_limit(self):
        run = simulate(replace(self.base, ticks=1), 0)
        self.assertEqual(run["metrics"]["affected_fraction"], 1)
        self.assertEqual(sum(run["metrics"]["attributable_offspring"].values()), 3)

    def test_zero_transmission_and_perfect_verification(self):
        for changes in ({"adoption": 0}, {"contacts": 0}, {"verification": 1}):
            run = simulate(replace(self.base, **changes), 0)
            self.assertEqual(run["metrics"]["affected_fraction"], 0.25)
        self.assertEqual(simulate(replace(self.base, verification=1), 0)["metrics"]["final_active_fraction"], 0)

    def test_controls_disable_both_channels(self):
        for arm in ("isolated_seed", "independent", "common_cause"):
            config = replace(self.base, arm=arm, memory_ttl=10)
            run = simulate(config, 0)
            self.assertFalse(run["relationships"]["communication_edges"])
            self.assertFalse(run["relationships"]["artifact_membership"])
            self.assertFalse(any(e["kind"] in ("message", "artifact_write", "artifact_read") for e in run["events"]))
            other = simulate(replace(config, cross_probability=0.9, memory_ttl=0), 0)
            self.assertEqual(run["metrics"], other["metrics"])

    def test_shared_vs_independent_roots(self):
        shared = simulate(replace(self.base, arm="common_cause", exposure_probability=1), 0)
        independent = simulate(replace(self.base, arm="independent", exposure_probability=1), 0)
        for run, expected in ((shared, 1), (independent, 4)):
            roots = {root for e in run["events"] if e["kind"] == "deviation" for root in e["roots"]}
            self.assertEqual(len(roots), expected)

    def test_null_has_no_spontaneous_deviations(self):
        run = simulate(replace(self.base, arm="independent", exposure_probability=0), 0)
        self.assertEqual(run["metrics"]["affected_fraction"], 0)
        self.assertEqual(run["metrics"]["extinction_tick"], 0)
        self.assertFalse(run["metrics"]["right_censored"])

    def test_memory_can_reintroduce_after_recovery(self):
        run = simulate(replace(self.base, contacts=0, memory_ttl=6, memory_read=1, recovery_delay=2), 0)
        self.assertGreater(run["metrics"]["recurrence_count"], 0)
        self.assertTrue(any(e["kind"] == "artifact_read" for e in run["events"]))

    def test_monitor_capacity_latency_and_backlog(self):
        run = simulate(replace(self.base, arm="common_cause", exposure_probability=1, monitor_capacity=1, monitor_latency=2), 0)
        interventions = [e for e in run["events"] if e["kind"] == "intervention"]
        self.assertEqual([e["tick"] for e in interventions], [3, 4, 5])
        self.assertEqual(run["metrics"]["max_backlog"], 4)

    def test_recovery_and_censoring(self):
        resolved = simulate(replace(self.base, arm="isolated_seed", recovery_delay=2), 0)
        self.assertEqual(resolved["metrics"]["extinction_tick"], 2)
        self.assertFalse(resolved["metrics"]["right_censored"])
        self.assertTrue(simulate(self.base, 0)["metrics"]["right_censored"])

    def test_dag_provenance_and_answer_checker(self):
        run = simulate(replace(self.base, memory_ttl=4), 0)
        events = run["events"]
        for event in events:
            self.assertTrue(all(parent < event["event_id"] for parent in event["parents"]))
            self.assertTrue(all(events[r]["kind"] == "seed_perturbation" for r in event["roots"]))
            if event["kind"] == "deviation":
                self.assertEqual(event["roots"], events[event["parents"][0]]["roots"])
            if event["kind"] == "answer":
                self.assertEqual(event["correct"], event["answer"]["sample_count"] == 7)

    def test_compute_budget(self):
        fixed = simulate(replace(self.base, compute_scaling="fixed", compute_budget=2), 0)
        per_agent = simulate(self.base, 0)
        self.assertEqual(fixed["metrics"]["total_decisions"], 10)
        self.assertEqual(per_agent["metrics"]["total_decisions"], 20)

    def test_graph_layers(self):
        g = graph(replace(self.base, topology="modular", within_probability=1, cross_probability=0), 0)
        self.assertEqual(g["communication_edges"], [[0, 1], [2, 3]])
        self.assertEqual(len(g["authority_edges"]), 4)

    def test_ttl_one_expires_before_read(self):
        run = simulate(replace(self.base, contacts=0, memory_ttl=1, memory_read=1), 0)
        self.assertTrue(any(e["kind"] == "artifact_expired" for e in run["events"]))
        self.assertFalse(any(e["kind"] == "artifact_read" for e in run["events"]))
        self.assertEqual(run["metrics"]["affected_fraction"], 0.25)

    def test_proportional_monitoring_budget(self):
        run = simulate(replace(self.base, arm="common_cause", exposure_probability=1,
                               monitor_capacity=1, monitor_scaling="proportional", monitor_latency=0), 0)
        interventions = [e for e in run["events"] if e["kind"] == "intervention"]
        self.assertEqual([e["tick"] for e in interventions], [2, 2, 3, 3])

    def test_llm_adapter_uses_same_environment(self):
        calls = []
        def transport(obs):
            calls.append(obs)
            return {"verify": True, "adopt_event": None}
        agent = LLMAgent(transport, model="fake-test-model", settings={"temperature": 0})
        run = simulate(self.base, 0, agent)
        self.assertEqual(len(calls), 20)
        self.assertEqual(run["metrics"]["final_active_fraction"], 0)
        self.assertEqual(run["agent"]["kind"], "llm")

    def test_rejects_fabricated_provenance(self):
        agent = LLMAgent(lambda obs: {"verify": False, "adopt_event": 999999}, model="fake", settings={})
        with self.assertRaises(ValueError):
            simulate(self.base, 0, agent)
        agent = LLMAgent(lambda obs: {"verify": "yes", "adopt_event": None}, model="fake", settings={})
        with self.assertRaises(ValueError):
            simulate(self.base, 0, agent)

    def test_input_validation(self):
        for changes in ({"n": 0}, {"contacts": -1}, {"verification": float("nan")}, {"adoption": 1.1}, {"arm": "unknown"}, {"ticks": True}):
            with self.assertRaises(ValueError):
                replace(self.base, **changes)
        with self.assertRaises(ValueError):
            expand({"seeds": [1, 1]})

    def test_end_to_end_sweep_and_replay_bytes(self):
        spec = {"base": {"n": 4, "ticks": 2}, "axes": {"arm": ["cascade", "isolated_seed"], "memory_ttl": [0, 2]}, "seeds": [0, 1]}
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent.parent) as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            run_sweep(spec, a, plots=False)
            run_sweep(spec, b, plots=False)
            self.assertEqual((a / "summary.csv").read_bytes(), (b / "summary.csv").read_bytes())
            manifest = json.loads((a / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "complete")
            self.assertEqual(manifest["run_count"], 8)
            for log in (a / "runs").glob("*.gz"):
                self.assertEqual(log.read_bytes(), (b / "runs" / log.name).read_bytes())
                with gzip.open(log, "rt") as stream:
                    self.assertEqual(json.loads(next(stream))["kind"], "run_started")
            with self.assertRaises(ValueError):
                run_sweep(spec, a, plots=False)


if __name__ == "__main__":
    unittest.main()
