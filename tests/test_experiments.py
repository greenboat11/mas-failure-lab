from dataclasses import replace
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from mas_failure_lab.composition import CompositionConfig, roles, simulate as composition
from mas_failure_lab.oversight import OversightConfig, simulate as oversight
from mas_failure_lab.suite import expand, run_sweep


class CompositionTests(unittest.TestCase):
    def test_composition_without_local_violation(self):
        config = CompositionConfig()
        run = composition(config, 1)
        self.assertTrue(run["metrics"]["locally_compliant_violation"])
        self.assertEqual(run["metrics"]["minimum_coalition_size"], len(roles(config)))
        self.assertEqual(run["metrics"]["necessary_agents"], len(roles(config)))
        audit = next(e for e in run["events"] if e["kind"] == "coalition_audit")
        self.assertFalse(any(audit["leave_one_out_violations"].values()))

    def test_authorization_and_label_loss(self):
        for authorization, retention, expected in (("local", 1, True), ("declared", 1, False),
                                                   ("declared", 0, True), ("lineage", 0, False)):
            run = composition(CompositionConfig(authorization=authorization, provenance_retention=retention), 0)
            self.assertEqual(run["metrics"]["global_violation"], expected)

    def test_removal_cut_and_sanitization_controls(self):
        for control in ("remove_retriever", "remove_transform", "remove_publisher", "cut_handoff", "sanitize"):
            run = composition(CompositionConfig(control=control), 0)
            self.assertFalse(run["metrics"]["global_violation"], control)
            self.assertIsNone(run["metrics"]["minimum_coalition_size"])

    def test_partition_changes_required_coalition(self):
        for partitioned, size in ((False, 3), (True, 4)):
            run = composition(CompositionConfig(partitioned=partitioned, relays=0), 0)
            self.assertEqual(run["metrics"]["minimum_coalition_size"], size)

    def test_roots_survive_visible_label_loss(self):
        run = composition(CompositionConfig(provenance_retention=0), 0)
        event = next(e for e in run["events"] if e["kind"] == "publication")
        self.assertFalse(event["declared_restricted"])
        self.assertEqual(len(event["roots"]), 2)
        for entry in run["events"]:
            self.assertTrue(all(p < entry["event_id"] for p in entry["parents"]))

    def test_deterministic_and_validated(self):
        self.assertEqual(composition(CompositionConfig(), 1), composition(CompositionConfig(), 1))
        for changes in ({"relays": 4}, {"provenance_retention": float("nan")}, {"authorization": "unknown"}):
            with self.assertRaises(ValueError):
                CompositionConfig(**changes)


class OversightTests(unittest.TestCase):
    def setUp(self):
        self.base = OversightConfig(n=2, ticks=8, arrival_probability=1, difficulty=1,
                                    review_capacity=0, retry_interval=1, deadline=3, impatience=1)

    def test_no_arrivals(self):
        run = oversight(replace(self.base, arrival_probability=0), 0)
        self.assertEqual(run["metrics"]["arrivals"], 0)
        self.assertEqual(run["metrics"]["final_backlog"], 0)
        self.assertIsNone(run["metrics"]["mean_completed_review_delay"])

    def test_no_difficulty(self):
        run = oversight(replace(self.base, difficulty=0), 0)
        self.assertEqual(run["metrics"]["answered"], 16)
        self.assertEqual(run["metrics"]["unsafe"], 0)
        self.assertEqual(run["metrics"]["final_backlog"], 0)

    def test_unbounded_capacity_cannot_ignore_latency(self):
        run = oversight(replace(self.base, arm="unbounded"), 0)
        self.assertEqual(run["metrics"]["unsafe"], 0)
        self.assertEqual(run["metrics"]["pending_at_horizon"], 2)
        delayed = oversight(replace(self.base, arm="unbounded", review_latency=5), 0)
        self.assertGreater(delayed["metrics"]["unsafe"], 0)

    def test_retry_amplification_and_suppression(self):
        runs = {arm: oversight(replace(self.base, arm=arm), 0) for arm in ("feedback", "no_retries", "deduplicated")}
        self.assertGreater(runs["feedback"]["metrics"]["final_backlog"], runs["no_retries"]["metrics"]["final_backlog"])
        self.assertEqual(runs["deduplicated"]["metrics"]["final_backlog"], runs["no_retries"]["metrics"]["final_backlog"])
        self.assertGreater(runs["deduplicated"]["metrics"]["suppressed"], 0)

    def test_capacity_and_task_conservation(self):
        run = oversight(replace(self.base, review_capacity=1), 0)
        m = run["metrics"]
        self.assertEqual(m["arrivals"], m["answered"] + m["reviewed"] + m["abstained"] + m["pending_at_horizon"])
        self.assertTrue(all(row["serviced_this_tick"] <= 1 for row in run["series"]))
        self.assertEqual(m["unsafe"], sum(e.get("unsafe", False) for e in run["events"] if e["kind"] in ("task_decision", "deadline_action")))

    def test_abstention_not_unsafe(self):
        run = oversight(replace(self.base, impatience=0), 0)
        self.assertEqual(run["metrics"]["unsafe"], 0)
        self.assertGreater(run["metrics"]["abstained"], 0)

    def test_scaling_budget_and_replay(self):
        config = replace(self.base, n=16, review_capacity=2, capacity_scaling="proportional")
        run = oversight(config, 0)
        self.assertEqual(run["metrics"]["effective_capacity"], 4)
        self.assertEqual(run, oversight(config, 0))
        for event in run["events"]:
            self.assertTrue(all(p < event["event_id"] for p in event["parents"]))


class SuiteTests(unittest.TestCase):
    def test_end_to_end_both_engines(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent.parent) as tmp:
            for experiment, base in (("composition", {"relays": 0}), ("oversight", {"n": 2, "ticks": 4})):
                spec = {"base": base, "seeds": [0, 1]}
                a, b = Path(tmp) / (experiment + "a"), Path(tmp) / (experiment + "b")
                run_sweep(experiment, spec, a, plots=False)
                run_sweep(experiment, spec, b, plots=False)
                self.assertEqual((a / "runs.csv").read_bytes(), (b / "runs.csv").read_bytes())
                self.assertEqual(json.loads((a / "manifest.json").read_text())["status"], "complete")
                for path in (a / "runs").glob("*.gz"):
                    self.assertEqual(path.read_bytes(), (b / "runs" / path.name).read_bytes())
                    with gzip.open(path, "rt") as stream:
                        self.assertEqual(json.loads(next(stream))["kind"], "run_started")
                with self.assertRaises(ValueError):
                    run_sweep(experiment, spec, a, plots=False)

    def test_sweep_validation(self):
        for spec in ({"seeds": [0, 0]}, {"seeds": [0], "axes": {"n": []}}, {"seeds": [True]}):
            with self.assertRaises(ValueError):
                expand("oversight", spec)
