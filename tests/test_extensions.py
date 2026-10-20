from dataclasses import replace
import unittest

from mas_failure_lab.composition import CompositionConfig, simulate as composition
from mas_failure_lab.model import Config, graph, graph_statistics, simulate
from mas_failure_lab.oversight import OversightConfig, simulate as oversight
from mas_failure_lab.randomness import draw, seed_plan, uniform


class CorrectionAndScaling(unittest.TestCase):
    def setUp(self):
        self.base = Config(n=2, team_size=2, ticks=2, topology="complete", verification=0, adoption=1,
                           contacts=1, memory_ttl=0, recovery_delay=20, monitor_capacity=0)

    def test_peer_truth_can_correct_in_synchronous_round(self):
        original = simulate(replace(self.base, ticks=1), 0)
        corrected = simulate(replace(self.base, ticks=1, baseline="corrective", corrective_peer=1), 0)
        self.assertEqual(original["metrics"]["final_active_fraction"], 1)
        self.assertEqual(corrected["metrics"]["final_active_fraction"], 0.5)
        self.assertTrue(any(e["kind"] == "peer_or_artifact_correction" for e in corrected["events"]))

    def test_corrective_write_and_cleanup(self):
        config = replace(self.base, contacts=0, baseline="corrective", memory_ttl=6, memory_read=1, corrective_write=1)
        result = simulate(config, 0)
        self.assertEqual(result["metrics"]["final_active_fraction"], 0)
        self.assertFalse(result["metrics"]["right_censored"])
        self.assertEqual(result["series"][-1]["contaminated_artifacts"], 0)
        cleaned = simulate(replace(config, corrective_write=0, artifact_cleanup=1), 0)
        self.assertTrue(any(e["kind"] == "artifact_cleanup" for e in cleaned["events"]))

    def test_matched_message_budget(self):
        for n in (4, 8, 16):
            config = replace(self.base, n=n, ticks=3, contacts=3, scaling_treatment="communication_budget", communication_budget=5)
            result = simulate(config, 0)
            self.assertEqual([s["messages"] for s in result["series"][1:]], [5, 5, 5])

    def test_expected_degree_and_probability_are_distinct(self):
        for n in (8, 16):
            config = replace(self.base, n=n, topology="erdos_renyi", scaling_treatment="expected_degree", expected_degree=3)
            mean = sum(graph_statistics(config, graph(config, s))["graph_mean_degree"] for s in range(300)) / 300
            self.assertAlmostEqual(mean, 3, delta=0.18)
        sparse = replace(self.base, n=8, topology="erdos_renyi", scaling_treatment="edge_probability", cross_probability=0.5)
        dense = replace(sparse, n=16)
        self.assertGreater(sum(len(graph(dense, s)["communication_edges"]) for s in range(20)), sum(len(graph(sparse, s)["communication_edges"]) for s in range(20)))

    def test_seed_domains_and_legacy_draws(self):
        self.assertEqual(draw(self.base, 4, "graph", 0, 1), uniform(4, "graph", 0, 1))
        a = replace(self.base, random_scheme="split-v2", topology_seed=9, task_seed=4, policy_seed=2)
        b = replace(a, policy_seed=10, trial_id="trial-2")
        self.assertEqual(graph(a, 0), graph(b, 0))
        self.assertEqual(draw(a, 0, "exogenous", 1), draw(b, 0, "exogenous", 1))
        self.assertNotEqual(draw(a, 0, "decision", 1), draw(b, 0, "decision", 1))
        self.assertEqual(seed_plan(a, 0)["task_seed"], 4)


class AlternativeWorkflow(unittest.TestCase):
    def test_configured_roles_are_distinct_from_actual_participation(self):
        config = CompositionConfig(workflow_mode="alternatives", redundant_publishers=2, control="remove_transform")
        result = composition(config, 0)
        events = [e for e in result["events"] if e["kind"] in ("restricted_read", "artifact_transformed", "handoff", "publication", "publication_blocked")]
        self.assertEqual(result["metrics"]["participating_agents"], len({e["actor"] for e in events}))
        self.assertLess(result["metrics"]["participating_agents"], result["metrics"]["configured_agents"])

    def test_coalitions_use_routes_instead_of_total_roles(self):
        config = CompositionConfig(workflow_mode="alternatives", relays=1, redundant_publishers=2)
        result = composition(config, 0)
        self.assertEqual(result["metrics"]["minimum_coalition_size"], 4)
        self.assertEqual(result["metrics"]["necessary_agents"], 2)
        for control in ("remove_transform", "remove_publisher", "cut_handoff"):
            self.assertTrue(composition(replace(config, control=control), 0)["metrics"]["global_violation"])
        self.assertFalse(composition(replace(config, control="remove_retriever"), 0)["metrics"]["global_violation"])

    def test_useful_authorization_versus_blocking_everything(self):
        config = CompositionConfig(workflow_mode="alternatives", relays=0, sanitizing_routes=1, authorization="global_policy")
        useful = composition(config, 0)["metrics"]
        blocked = composition(replace(config, authorization="lineage"), 0)["metrics"]
        self.assertFalse(useful["global_violation"])
        self.assertTrue(useful["authorized_task_completion"])
        self.assertFalse(blocked["authorized_task_completion"])
        self.assertIsNone(useful["minimum_coalition_size"])


class OversightExtensions(unittest.TestCase):
    def setUp(self):
        self.base = OversightConfig(n=2, ticks=6, arrival_probability=1, difficulty=1, baseline="extended", review_capacity=0, deadline=3)

    def test_false_negatives_and_false_positives(self):
        missed = oversight(replace(self.base, review_sensitivity=0), 0)["metrics"]
        self.assertEqual(missed["unsafe_fraction"], 1)
        self.assertEqual(missed["original_review_demand"], 0)
        false_positive = oversight(replace(self.base, difficulty=0, review_specificity=0), 0)["metrics"]
        self.assertEqual(false_positive["original_review_demand"], 12)
        self.assertEqual(false_positive["nominal_offered_review_load"], 0)

    def test_agent_wait_decisions_and_imperfect_review(self):
        wait = oversight(replace(self.base, retry_mode="agent", retry_probability=0), 0)
        self.assertEqual(wait["metrics"]["retry_demand"], 0)
        self.assertTrue(any(e["kind"] == "retry_decision" for e in wait["events"]))
        reviewed = oversight(replace(self.base, arm="unbounded", review_accuracy=0), 0)["metrics"]
        self.assertEqual(reviewed["review_errors"], 10)
        self.assertEqual(reviewed["unsafe"], 10)
        self.assertEqual(reviewed["pending_at_horizon"], 2)

    def test_demand_conservation_and_zero_load(self):
        result = oversight(self.base, 0)["metrics"]
        self.assertEqual(result["final_backlog"], result["original_review_demand"] + result["retry_demand"] - result["serviced"])
        self.assertEqual(result["final_backlog"], result["stale_requests"] + result["live_requests"])
        self.assertIsNone(result["rho_0"])
        self.assertEqual(result["rho_0_status"], "infinite")
        self.assertEqual(oversight(replace(self.base, arrival_probability=0), 0)["metrics"]["rho_0_status"], "undefined_zero_over_zero")
