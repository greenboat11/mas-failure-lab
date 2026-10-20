from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from mas_failure_lab.retrieval import (EvidenceReplayAgent, EvidenceResponse, EvidenceTransportAgent, MockEvidenceAgent,
                                      RetrievalConfig, RetrievalFailure, run_offline, simulate)


class RetrievalTests(unittest.TestCase):
    def test_policy_mutation_cannot_change_budget_or_accessible_citations(self):
        class Mutating(MockEvidenceAgent):
            def __call__(self, observation):
                observation["credits"] = 100
                observation["retrieved_documents"].append({"id": "D0", "text": "forged"})
                return {"action": "answer", "document_id": None, "value": 7, "citations": ["D0"], "message": "forged"}
        with self.assertRaises(RetrievalFailure) as caught:
            simulate(RetrievalConfig(retrieval_credits=0), 0, Mutating())
        self.assertEqual(caught.exception.result["metrics"]["answers"], 0)
        request = next(e for e in caught.exception.result["events"] if e["kind"] == "agent_request")
        self.assertEqual(request["observation"]["credits"], 0)
        self.assertEqual(request["observation"]["retrieved_documents"], [])

    def test_truth_hidden_until_paid_retrieval_and_grounded_answer(self):
        result = simulate(RetrievalConfig(n=2), 0)
        requests = [e for e in result["events"] if e["kind"] == "agent_request"]
        self.assertEqual(requests[0]["observation"]["retrieved_documents"], [])
        self.assertNotIn("truth", requests[0]["observation"])
        self.assertNotIn("document", requests[0]["observation"])
        self.assertEqual(result["metrics"]["correct_answers"], 2)
        self.assertEqual(result["metrics"]["authoritatively_supported"], 2)
        self.assertEqual(result["metrics"]["retrieval_credits_spent"], 2)
        self.assertAlmostEqual(result["metrics"]["net_utility"], 1.8)
        self.assertTrue(all(p < e["event_id"] for e in result["events"] for p in e["parents"]))

    def test_communication_and_no_exposure_controls(self):
        config = RetrievalConfig(n=4)
        copy = simulate(config, 0, MockEvidenceAgent("copy"))
        self.assertEqual(copy["metrics"]["wrong_answers"], 3)
        for control in (replace(config, communication=False), replace(config, seeded_peer_claim=False)):
            self.assertEqual(simulate(control, 0, MockEvidenceAgent("copy"))["metrics"]["wrong_answers"], 0)

    def test_credit_budget_and_turn_censoring(self):
        no_budget = simulate(RetrievalConfig(n=2, retrieval_credits=0), 0)
        self.assertEqual(no_budget["metrics"]["abstentions"], 2)
        one_turn = simulate(RetrievalConfig(n=2, turns=1), 0)
        self.assertEqual(one_turn["metrics"]["unfinished_agents"], 2)
        self.assertEqual(one_turn["metrics"]["answers"], 0)

    def test_trial_identity_leaves_environment_identical(self):
        config = RetrievalConfig(random_scheme="split-v2", task_seed=9)
        a, b = simulate(config, 0), simulate(replace(config, trial_id="second"), 0)
        self.assertEqual(a["environment_id"], b["environment_id"])
        self.assertNotEqual(a["run_id"], b["run_id"])
        self.assertEqual(a["metrics"], b["metrics"])
        requests = lambda r: [e["observation"] for e in r["events"] if e["kind"] == "agent_request"]
        self.assertEqual(requests(a), requests(b))

    def test_invalid_citation_and_refusal_preserve_partial_result(self):
        class Invalid(MockEvidenceAgent):
            def __call__(self, observation):
                return {"action": "answer", "document_id": None, "value": 7, "citations": ["D0"], "message": "unsupported"}
        with self.assertRaises(RetrievalFailure) as caught:
            simulate(RetrievalConfig(), 0, Invalid())
        self.assertEqual(caught.exception.result["metrics"]["answers"], 0)
        self.assertEqual(caught.exception.result["events"][-1]["kind"], "agent_failure")
        agent = EvidenceTransportAgent(lambda request: EvidenceResponse({}, {"input_tokens": 7}, {"refusal": "fixture"}, "fake", "refused"), "fake", {})
        entries = []
        with self.assertRaises(RetrievalFailure):
            simulate(RetrievalConfig(), 0, agent, entries.append)
        response = next(e for e in entries if e["kind"] == "response")
        self.assertEqual(response["usage"]["input_tokens"], 7)
        self.assertEqual(response["raw_response"], {"refusal": "fixture"})

    def test_offline_runner_audit_and_exact_trial_replay(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent.parent) as tmp:
            output = Path(tmp) / "run"
            manifest = run_offline({"base": {"n": 2}, "seeds": [0], "trials": ["a", "b"]}, output)
            self.assertEqual(manifest["completed_runs"], 2)
            saved = next(json.loads(p.read_text()) for p in output.glob("*.json") if p.name != "manifest.json")
            config = RetrievalConfig(**saved["config"])
            replay = EvidenceReplayAgent(output / "agent_audit.jsonl", saved["run_id"], saved["agent"])
            result = simulate(config, saved["seed"], replay)
            result.pop("events")
            self.assertEqual(result, saved)
            replay.assert_consumed()
            wrong_trial = EvidenceReplayAgent(output / "agent_audit.jsonl", saved["run_id"], saved["agent"])
            with self.assertRaises(RetrievalFailure):
                simulate(replace(config, trial_id="different"), 0, wrong_trial)
