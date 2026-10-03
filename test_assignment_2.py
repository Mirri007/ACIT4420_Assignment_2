"""End-to-end tests for the Assignment 2 file-based workflow."""

import csv
import tempfile
import unittest
from pathlib import Path

from main import analyze_files


class AssignmentTwoWorkflowTests(unittest.TestCase):
    def test_creates_predictable_reports_from_both_session_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            profiles = root / "participants.csv"
            sessions = root / "fitness_sessions.csv"
            invalid_sessions = root / "fitness_sessions_invalid.csv"
            output = root / "output"

            self._write_csv(
                profiles,
                ["participant_id", "name", "baseline_heart_rate", "baseline_skin_response", "baseline_temperature"],
                [["P001", "Amina Noor", "68", "1.20", "32.4"]],
            )
            self._write_csv(
                sessions,
                ["session_id", "participant_id", "timestamp", "heart_rate", "skin_response", "temperature", "activity_level", "signal_quality"],
                [
                    ["FIT-2026-001", "P001", "0", "68", "1.2", "32.4", "0.08", "0.98"],
                    ["FIT-2026-001", "P001", "1", "69", "1.2", "32.4", "0.08", "0.98"],
                    ["FIT-2026-001", "P001", "2", "67", "1.2", "32.4", "0.08", "0.98"],
                ],
            )
            self._write_csv(
                invalid_sessions,
                ["session_id", "participant_id", "timestamp", "heart_rate", "skin_response", "temperature", "activity_level", "signal_quality"],
                [["FIT-2026-001", "P001", "3", "68", "1.2", "32.4", "0.08", "0.59"]],
            )

            first_result = analyze_files(profiles, sessions, invalid_sessions, output)
            first_summary = (output / "analysis_summary.csv").read_text(encoding="utf-8")
            second_result = analyze_files(profiles, sessions, invalid_sessions, output)
            second_summary = (output / "analysis_summary.csv").read_text(encoding="utf-8")

            self.assertEqual(first_result[:2], (3, 1))
            self.assertEqual(second_result[:2], (3, 1))
            self.assertEqual(first_summary, second_summary)
            with open(output / "analysis_summary.csv", encoding="utf-8", newline="") as csv_file:
                summary_rows = list(csv.DictReader(csv_file))
            self.assertEqual(len(summary_rows), 1)
            self.assertEqual(summary_rows[0]["classification"], "poor_quality")
            self.assertEqual(summary_rows[0]["min_heart_rate"], "67.0")
            self.assertIn("max_activity", summary_rows[0])
            self.assertIn("signal_quality", (output / "rejected_records.txt").read_text(encoding="utf-8"))
            self.assertEqual(len(first_result[2]), 3)

    def test_malformed_session_file_does_not_block_other_session_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            profiles = root / "participants.csv"
            sessions = root / "fitness_sessions.csv"
            invalid_sessions = root / "fitness_sessions_invalid.csv"
            output = root / "output"
            self._write_csv(
                profiles,
                ["participant_id", "name", "baseline_heart_rate", "baseline_skin_response", "baseline_temperature"],
                [["P001", "Amina Noor", "68", "1.20", "32.4"]],
            )
            with open(sessions, "w", encoding="utf-8", newline="") as csv_file:
                csv_file.write(
                    "session_id,participant_id,timestamp,heart_rate,skin_response,temperature,activity_level,signal_quality\n"
                    '"FIT-2026-001,P001,0,68,1.2,32.4,0.08,0.98\n'
                )
            self._write_csv(
                invalid_sessions,
                ["session_id", "participant_id", "timestamp", "heart_rate", "skin_response", "temperature", "activity_level", "signal_quality"],
                [
                    ["FIT-2026-009", "P001", "0", "68", "1.2", "32.4", "0.08", "0.98"],
                    ["FIT-2026-009", "P001", "1", "69", "1.2", "32.4", "0.08", "0.98"],
                    ["FIT-2026-009", "P001", "2", "67", "1.2", "32.4", "0.08", "0.98"],
                ],
            )

            accepted, rejected, _ = analyze_files(profiles, sessions, invalid_sessions, output)

            self.assertEqual((accepted, rejected), (3, 1))
            summary_text = (output / "analysis_summary.csv").read_text(encoding="utf-8")
            rejected_text = (output / "rejected_records.txt").read_text(encoding="utf-8")
            self.assertIn("FIT-2026-009", summary_text)
            self.assertIn("fitness_sessions.csv: row 2; field csv", rejected_text)

    @staticmethod
    def _write_csv(path, header, rows):
        with open(path, "w", encoding="utf-8", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(header)
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()