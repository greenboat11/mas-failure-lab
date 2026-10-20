from dataclasses import replace
import math
import unittest

from mas_failure_lab.benchmarks import composition_disclosure, fifo_backlog, offered_load
from mas_failure_lab.composition import CompositionConfig, simulate as composition
from mas_failure_lab.oversight import OversightConfig, simulate as oversight


class AnalyticalTests(unittest.TestCase):
    def test_declared_workflow_formula(self):
        for r in (0, 1, 3):
            for p in (0, 0.6, 1):
                config = CompositionConfig(relays=r, provenance_retention=p, authorization="declared", audit_coalitions=False)
                count = 800 if 0 < p < 1 else 1
                observed = sum(composition(config, s)["metrics"]["global_violation"] for s in range(count)) / count
                expected = composition_disclosure(p, r)
                tolerance = 5 * math.sqrt(expected * (1 - expected) / count) if count > 1 else 0
                self.assertLessEqual(abs(observed - expected), tolerance)

    def test_queue_recurrence_and_capacity_limits(self):
        config = OversightConfig(n=3, ticks=8, arrival_probability=1, difficulty=1, arm="no_retries", deadline=2)
        for capacity in (0, 1, 3, 8):
            run = oversight(replace(config, review_capacity=capacity), 0)
            self.assertEqual([r["backlog"] for r in run["series"]], fifo_backlog([3] * 8, capacity))
        self.assertEqual(offered_load(3, 1, 1, 0)["rho_0_status"], "infinite")
        self.assertEqual(offered_load(3, 0, 1, 0)["rho_0_status"], "undefined_zero_over_zero")


if __name__ == "__main__":
    unittest.main()
