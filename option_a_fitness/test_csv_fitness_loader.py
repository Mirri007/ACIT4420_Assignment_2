"""Focused tests for the Assignment 2 CSV validation layer."""

import csv
import tempfile
import unittest
from pathlib import Path

from option_a_fitness.csv_fitness_loader import load_participants, load_sessions


class CsvFitnessLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.directory = Path(self.temp_dir.name)

    def _write_csv(self, name, header, rows):
        path = self.directory / name
        with open(path, "w", encoding="utf-8", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(header)
            writer.writerows(rows)
        return path

    def test_loads_typed_profiles_and_valid_session(self):
        profile_path = self._write_csv(
            "participants.csv",
            ["participant_id", "name", "baseline_heart_rate", "baseline_skin_response", "baseline_temperature"],
            [["P001", "Amina Noor", "68", "1.20", "32.4"]],
        )
        session_path = self._write_csv(
            "fitness_sessions.csv",
            ["session_id", "participant_id", "timestamp", "heart_rate", "skin_response", "temperature", "activity_level", "signal_quality"],
            [["FIT-2026-001", "P001", "0", "68", "1.18", "32.4", "0.08", "0.98"]],
        )

        profiles, profile_rejections = load_participants(profile_path)
        sessions, session_rejections = load_sessions(session_path, set(profiles))

        self.assertEqual(profile_rejections, [])
        self.assertEqual(session_rejections, [])
        self.assertIsInstance(profiles["P001"]["baseline_heart_rate"], int)
        self.assertIsInstance(sessions[0]["heart_rate"], float)
        self.assertEqual(sessions[0]["session_id"], "FIT-2026-001")

    def test_rejects_invalid_ids_unknown_participants_and_bad_signal(self):
        profile_path = self._write_csv(
            "participants.csv",
            ["participant_id", "name", "baseline_heart_rate", "baseline_skin_response", "baseline_temperature"],
            [["P001", "Amina Noor", "68", "1.20", "32.4"]],
        )
        session_path = self._write_csv(
            "fitness_sessions_invalid.csv",
            ["session_id", "participant_id", "timestamp", "heart_rate", "skin_response", "temperature", "activity_level", "signal_quality"],
            [
                ["FIT-2026-1", "P001", "0", "68", "1.18", "32.4", "0.08", "0.98"],
                ["FIT-2026-002", "P999", "1", "68", "1.18", "32.4", "0.08", "0.98"],
                ["FIT-2026-003", "P001", "2", "68", "1.18", "32.4", "0.08", "0.59"],
            ],
        )

        profiles, _ = load_participants(profile_path)
        sessions, rejected = load_sessions(session_path, set(profiles))

        self.assertEqual(sessions, [])
        self.assertEqual(len(rejected), 3)
        self.assertEqual(
            [(item.row_number, item.field) for item in rejected],
            [(2, "session_id"), (3, "participant_id"), (4, "signal_quality")],
        )

    def test_identifier_patterns_must_match_the_entire_value(self):
        profile_path = self._write_csv(
            "participants.csv",
            ["participant_id", "name", "baseline_heart_rate", "baseline_skin_response", "baseline_temperature"],
            [
                ["P001", "Amina Noor", "68", "1.20", "32.4"],
                ["P001x", "Invalid ID", "68", "1.20", "32.4"],
            ],
        )
        session_path = self._write_csv(
            "fitness_sessions.csv",
            ["session_id", "participant_id", "timestamp", "heart_rate", "skin_response", "temperature", "activity_level", "signal_quality"],
            [
                ["FIT-2026-001", "P00x", "0", "68", "1.18", "32.4", "0.08", "0.98"],
                ["xFIT-2026-001", "P001", "1", "68", "1.18", "32.4", "0.08", "0.98"],
                ["FIT-2026-001x", "P001", "2", "68", "1.18", "32.4", "0.08", "0.98"],
                ["FIT-2026-001", "P001", "3", "68", "1.18", "32.4", "0.08", "0.98"],
            ],
        )

        profiles, profile_rejections = load_participants(profile_path)
        sessions, session_rejections = load_sessions(session_path, set(profiles))

        self.assertEqual(set(profiles), {"P001"})
        self.assertEqual([(item.row_number, item.field) for item in profile_rejections], [(3, "participant_id")])
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["session_id"], "FIT-2026-001")
        self.assertEqual(
            [(item.row_number, item.field) for item in session_rejections],
            [(2, "participant_id"), (3, "session_id"), (4, "session_id")],
        )

    def test_rejections_include_source_row_field_and_reason(self):
        path = self._write_csv(
            "fitness_sessions_invalid.csv",
            ["session_id", "participant_id", "timestamp", "heart_rate", "skin_response", "temperature", "activity_level", "signal_quality"],
            [
                ["FIT-2026-001", "P001", "0", "", "1.18", "32.4", "0.08", "0.98"],
                ["FIT-2026-002", "P001", "one", "68", "1.18", "32.4", "0.08", "0.98"],
                ["FIT-2026-003", "P001", "2", "206", "1.18", "32.4", "0.08", "0.98"],
                ["FIT-2026-004", "P999", "3", "68", "1.18", "32.4", "0.08", "0.98"],
                ["FIT-2026-005", "P001", "4", "68", "1.18", "32.4", "0.08"],
            ],
        )

        sessions, rejected = load_sessions(path, {"P001"})

        self.assertEqual(sessions, [])
        self.assertEqual(
            [
                (item.source_file, item.row_number, item.field, item.reason)
                for item in rejected
            ],
            [
                ("fitness_sessions_invalid.csv", 2, "heart_rate", "required value is missing"),
                ("fitness_sessions_invalid.csv", 3, "timestamp", "value must be an integer"),
                ("fitness_sessions_invalid.csv", 4, "heart_rate", "must be between 35 and 205"),
                ("fitness_sessions_invalid.csv", 5, "participant_id", "unknown participant ID"),
                ("fitness_sessions_invalid.csv", 6, "row", "expected 8 columns, found 7"),
            ],
        )

    def test_rejects_missing_required_profile_field(self):
        path = self._write_csv(
            "participants.csv",
            ["participant_id", "name", "baseline_heart_rate", "baseline_skin_response", "baseline_temperature"],
            [["P001", "Amina Noor", "", "1.20", "32.4"]],
        )

        profiles, rejected = load_participants(path)

        self.assertEqual(profiles, {})
        self.assertEqual(
            [(item.source_file, item.row_number, item.field, item.reason) for item in rejected],
            [("participants.csv", 2, "baseline_heart_rate", "required value is missing")],
        )

    def test_malformed_csv_has_source_row_and_parse_context(self):
        path = self.directory / "fitness_sessions_invalid.csv"
        with open(path, "w", encoding="utf-8", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(
                ["session_id", "participant_id", "timestamp", "heart_rate", "skin_response", "temperature", "activity_level", "signal_quality"]
            )
            csv_file.write('"FIT-2026-001,P001,0,68,1.18,32.4,0.08,0.98\n')

        sessions, rejected = load_sessions(path, {"P001"})

        self.assertEqual(sessions, [])
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0].source_file, "fitness_sessions_invalid.csv")
        self.assertEqual(rejected[0].row_number, 2)
        self.assertEqual(rejected[0].field, "csv")
        self.assertIn("malformed CSV", rejected[0].reason)

    def test_rejects_wrong_row_length_and_out_of_range_boundary(self):
        path = self._write_csv(
            "fitness_sessions.csv",
            ["session_id", "participant_id", "timestamp", "heart_rate", "skin_response", "temperature", "activity_level", "signal_quality"],
            [
                ["FIT-2026-000", "P001", "0", "35", "0", "25", "0", "0.6"],
                ["FIT-2026-001", "P001", "0", "205.1", "1.18", "32.4", "0.08", "0.98"],
                ["FIT-2026-002", "P001", "1", "68", "1.18", "32.4", "0.08"],
            ],
        )

        sessions, rejected = load_sessions(path, {"P001"})

        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["heart_rate"], 35)
        self.assertEqual(sessions[0]["temperature"], 25)
        self.assertEqual(sessions[0]["signal_quality"], 0.6)
        self.assertEqual([(item.row_number, item.field) for item in rejected], [(3, "heart_rate"), (4, "row")])

    def test_missing_input_file_is_reported_to_caller(self):
        with self.assertRaises(FileNotFoundError):
            load_participants(self.directory / "participants.csv")


if __name__ == "__main__":
    unittest.main()