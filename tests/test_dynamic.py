import unittest

from choicegap.dynamic import DynamicSession, audit_study, compile_study


DESIGN = {
    "title": "Choose an invoicing app",
    "decision_prompt": "Which invoicing app would you choose for your freelance work?",
    "attributes": [
        {"id": "a", "label": "Automation", "low_label": "Manual reminders", "high_label": "Automatic reminders", "hypothesis_label": "Automation seeking", "hypothesis_description": "Reducing repetitive work drives the choice."},
        {"id": "b", "label": "Appearance", "low_label": "Standard templates", "high_label": "Custom branded templates", "hypothesis_label": "Professional image", "hypothesis_description": "Client-facing polish drives the choice."},
        {"id": "c", "label": "Payment speed", "low_label": "Standard settlement", "high_label": "Instant settlement", "hypothesis_label": "Cash-flow urgency", "hypothesis_description": "Faster access to funds drives the choice."},
        {"id": "d", "label": "Monthly price", "low_label": "$24 per month", "high_label": "$8 per month", "hypothesis_label": "Price sensitivity", "hypothesis_description": "Lower recurring cost drives the choice."},
    ],
}


class DynamicStudyTests(unittest.TestCase):
    def test_compiler_creates_complete_controlled_pairwise_design(self):
        study = compile_study(DESIGN)
        audit = audit_study(study)
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["experiment_count"], 6)
        self.assertTrue(all(audit["checks"].values()))

    def test_dynamic_session_adapts_and_reports(self):
        study = compile_study(DESIGN)
        session = DynamicSession.create(study, "a", "I like automation", seed=42)
        first = session.next_experiment()
        self.assertIsNotNone(first)
        session.observe(first["id"], "a", first["flipped"])
        self.assertAlmostEqual(sum(session.posterior.values()), 1.0)
        self.assertEqual(session.report()["rounds"], 1)

    def test_compiler_rejects_duplicate_axis_ids(self):
        broken = {**DESIGN, "attributes": [dict(item) for item in DESIGN["attributes"]]}
        broken["attributes"][3]["id"] = "c"
        with self.assertRaises(ValueError):
            compile_study(broken)


if __name__ == "__main__":
    unittest.main()
