import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ParticipantBlindnessTests(unittest.TestCase):
    def test_sensitive_research_signals_are_hidden_by_default(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        for element_id in ("agent-note", "experiment-rationale"):
            marker = f'id="{element_id}"'
            start = html.index(marker)
            tag_start = html.rfind("<", 0, start)
            tag_end = html.index(">", start)
            self.assertIn("researcher-only", html[tag_start:tag_end])
        self.assertIn('class="hypotheses researcher-only"', html)
        self.assertIn('class="uncertainty researcher-only"', html)

    def test_debrief_requires_explicit_action(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="open-debrief"', html)
        self.assertIn("$('#open-debrief').addEventListener", script)

    def test_researcher_can_compile_a_new_study(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="design-context"', html)
        self.assertIn("api('/api/design'", script)


if __name__ == "__main__":
    unittest.main()
