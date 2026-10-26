import unittest

from choicegap.benchmark import run_benchmark
from choicegap.engine import DRIVERS, Session, expected_information_gain, find_experiment, update_posterior
from choicegap.meta import MetaClient


class EngineTests(unittest.TestCase):
    def test_posterior_stays_normalized(self):
        session = Session.create("impact", "I want lower emissions", seed=1)
        experiment = find_experiment("impact-v-price")
        updated = update_posterior(session.posterior, experiment, "a")
        self.assertAlmostEqual(sum(updated.values()), 1.0)
        self.assertTrue(all(0 <= value <= 1 for value in updated.values()))

    def test_stated_profile_does_not_bias_behavioural_prior(self):
        ratings = {"impact": 5, "price": 1, "convenience": 2, "trust": 4}
        session = Session.create("impact", "I choose lower impact", seed=10, stated_ratings=ratings, intention_score=5)
        self.assertEqual(session.stated_ratings, ratings)
        self.assertEqual(session.intention_score, 5)
        self.assertTrue(all(value == 0.25 for value in session.posterior.values()))

    def test_expected_information_gain_is_non_negative(self):
        session = Session.create("convenience", "Timing matters", seed=2)
        for experiment_id in ("impact-v-price", "impact-v-convenience", "trust-v-price"):
            self.assertGreaterEqual(expected_information_gain(session.posterior, find_experiment(experiment_id)), -1e-12)

    def test_repeated_convenience_evidence_can_overturn_stated_preference(self):
        session = Session.create("price", "Price matters", seed=3)
        experiment = find_experiment("convenience-v-price")
        for _ in range(3):
            session.posterior = update_posterior(session.posterior, experiment, "a")
        self.assertEqual(max(session.posterior, key=session.posterior.get), "convenience")

    def test_side_randomization_is_reproducible(self):
        first = Session.create("trust", "Verify green claims", seed=99).next_experiment()
        second = Session.create("trust", "Verify green claims", seed=99).next_experiment()
        self.assertEqual(first, second)

    def test_benchmark_is_reproducible_and_adaptive_is_competitive(self):
        first = run_benchmark(participants=240, seed=7)
        second = run_benchmark(participants=240, seed=7)
        self.assertEqual(first, second)
        adaptive = first["strategies"]["adaptive"]["top1_accuracy"]
        random = first["strategies"]["random"]["top1_accuracy"]
        self.assertGreaterEqual(adaptive, random - 0.03)

    def test_falsification_plan_is_auditable_and_constrained(self):
        session = Session.create("impact", "I want lower emissions", seed=11)
        candidates = session.candidates()
        plan = MetaClient.fallback_plan(candidates, session.posterior)
        self.assertIn(plan["experiment_id"], {item["id"] for item in candidates})
        self.assertNotEqual(plan["leading_account"], plan["rival_account"])
        self.assertTrue(plan["falsification_rule"])


if __name__ == "__main__":
    unittest.main()

