from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import SimpleTestCase
from ingestion.parser import parse_line, parse_text_file

SAMPLE = "[2025-09-22 00:23:24] Match:MATCH001 Team:Team B Player:Player 9 Event:LBW given Runs:5 Over:37 Status:pending review Commentary:Player 9 () performed LBW given, adding 5 runs in over 37."

class CricketParserTests(SimpleTestCase):
    def test_sample_line_is_structured(self):
        e = parse_line(SAMPLE)
        self.assertEqual(e["match_id"], "MATCH001")
        self.assertEqual(e["player"], "Player 9")
        self.assertEqual(e["event_type"], "LBW given")
        self.assertEqual(e["runs"], 5)
        self.assertEqual(e["status"], "pending review")
        self.assertIn("lbw_given_with_positive_runs", e["quality_flags"])
        self.assertIsNone(e["role"])

    def test_dataset_parses_all_500_lines(self):
        candidates = [Path(__file__).resolve().parents[2] / "data" / "cricket_log.txt", Path("/app/data/cricket_log.txt")]
        path = next((candidate for candidate in candidates if candidate.exists()), None)
        if path is not None:
            events = parse_text_file(path)
            self.assertEqual(len(events), 500)
            self.assertEqual(len({e["event_id"] for e in events}), 500)

    def test_invalid_line_rejected(self):
        with self.assertRaises(ValueError):
            parse_line("not a cricket log line")

    def test_empty_file_rejected(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "empty.txt"
            p.write_text("", encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_text_file(p)
