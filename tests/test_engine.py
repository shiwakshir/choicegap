import unittest

from choicegap.benchmark import run_benchmark
from choicegap.engine import DRIVERS, Session, expected_information_gain, find_experiment, update_posterior
from choicegap.meta import MetaClient
from unittest.mock import patch


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

    def test_outside_option_does_not_manufacture_evidence(self):
        session = Session.create("impact", "", seed=12)
        before = dict(session.posterior)
        experiment = session.next_experiment()
        session.observe(experiment["id"], "outside", experiment["flipped"])
        self.assertEqual(session.posterior, before)
        self.assertEqual(session.report()["opt_out_count"], 1)

    def test_reversed_holdout_checks_consistency_without_updating(self):
        session = Session.create("impact", "", seed=13)
        experiment = session.next_experiment()
        session.observe(experiment["id"], "a", experiment["flipped"])
        after_choice = dict(session.posterior)
        holdout = session.holdout_experiment()
        expected_displayed = "b" if session.holdout_source["choice"] == "a" else "a"
        if not holdout["flipped"]:
            expected_displayed = session.holdout_source["choice"]
        session.observe_holdout(expected_displayed, holdout["flipped"])
        self.assertTrue(session.holdout_consistent)
        self.assertEqual(session.posterior, after_choice)

    def test_repeat_disagreement_does_not_exclude_an_answered_session(self):
        session = Session.create("price", "", seed=14)
        experiment = find_experiment("impact-v-price")
        for _ in range(4):
            session.observe(experiment.id, "a", False)
        session.holdout_consistent = False
        report = session.report()
        self.assertEqual(report["evidence_quality"], "high")
        self.assertFalse(report["gap_detected"])
        self.assertFalse(report['holdout_consistent'])
        self.assertNotIn('importance ratings', report['headline'])

    def test_low_quality_report_bypasses_model_narration(self):
        client = MetaClient()
        client.api_key = "would-enable-model"
        narrative = client.narrate_report({
            "evidence_quality": "low",
            "headline": "The evidence is inconclusive because the response-quality threshold was not met.",
        })
        self.assertEqual(narrative["source"], "quality-guardrail")
        self.assertIn("inconclusive", narrative["summary"].lower())

    def test_model_cannot_select_an_unissued_experiment(self):
        client = MetaClient()
        client.api_key = 'test-only'
        session = Session.create('impact', '', seed=1)
        result = {'experiment_id': 'invented'}
        with patch.object(client, '_structured', return_value=result):
            with self.assertRaises(RuntimeError):
                client.choose_experiment(session.candidates(), session.posterior)

    def test_candidates_include_computed_predictions_for_every_account(self):
        session = Session.create('impact', '', seed=1)
        for candidate in session.candidates():
            experiment = find_experiment(candidate['id'])
            from choicegap.engine import choice_probability
            for driver in DRIVERS:
                self.assertAlmostEqual(
                    candidate['predictions'][driver], choice_probability(experiment, driver), places=4,
                )


if __name__ == "__main__":
    unittest.main()

