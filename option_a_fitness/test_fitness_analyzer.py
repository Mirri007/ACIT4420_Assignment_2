"""Tests for session classification and insufficient-data handling."""

import unittest

from option_a_fitness.fitness_analyzer import FitnessSessionAnalyzer


PROFILE = {
    "participant_id": "P001",
    "baseline_heart_rate": 68,
    "baseline_skin_response": 1.2,
    "baseline_temperature": 32.4,
}


def observations(heart_rates, activity=0.08):
    return [
        {
            "timestamp": index,
            "heart_rate": heart_rate,
            "skin_response": 1.2,
            "temperature": 32.4,
            "activity_level": activity,
            "signal_quality": 0.95,
        }
        for index, heart_rate in enumerate(heart_rates)
    ]


class FitnessSessionAnalyzerTests(unittest.TestCase):
    def test_classifies_resting_session_and_compares_personal_baseline(self):
        analyzer = FitnessSessionAnalyzer(PROFILE, "FIT-2026-001", observations([68, 69, 67]))

        self.assertEqual(analyzer.session_summary["classification"], "resting")
        self.assertEqual(analyzer.session_summary["data_status"], "usable")
        self.assertEqual(analyzer.session_summary["heart_rate_vs_baseline"], 0)
        self.assertEqual(analyzer.session_summary["min_heart_rate"], 67)
        self.assertEqual(analyzer.session_summary["max_heart_rate"], 69)
        self.assertEqual(analyzer.session_summary["min_activity"], 0.08)
        self.assertEqual(analyzer.session_summary["max_activity"], 0.08)

    def test_classifies_unusual_baseline_deviations_with_reasons(self):
        rows = observations([70, 71, 69])
        for row in rows:
            row["skin_response"] = 2.0
            row["temperature"] = 34.0

        analyzer = FitnessSessionAnalyzer(PROFILE, "FIT-2026-007", rows)

        self.assertEqual(analyzer.session_summary["classification"], "unusual")
        self.assertIn("skin response", analyzer.session_summary["classification_reason"])
        self.assertIn("temperature", analyzer.session_summary["classification_reason"])
        self.assertEqual(analyzer.session_summary["skin_response_vs_baseline"], 0.8)
        self.assertEqual(analyzer.session_summary["temperature_vs_baseline"], 1.6)

    def test_classifies_high_activity_session(self):
        analyzer = FitnessSessionAnalyzer(
            PROFILE, "FIT-2026-002", observations([110, 115, 120], activity=0.8)
        )

        self.assertEqual(analyzer.session_summary["classification"], "high_activity")
        self.assertTrue(analyzer.session_summary["classification_reason"])

    def test_expected_fitness_response_does_not_override_high_activity(self):
        rows = observations([126, 132, 138], activity=0.8)
        for row in rows:
            row["skin_response"] = 1.85
            row["temperature"] = 32.95

        analyzer = FitnessSessionAnalyzer(PROFILE, "FIT-2026-008", rows)

        self.assertEqual(analyzer.session_summary["classification"], "high_activity")

    def test_classifies_moderate_activity_against_personal_baseline(self):
        analyzer = FitnessSessionAnalyzer(
            PROFILE, "FIT-2026-005", observations([85, 90, 88], activity=0.3)
        )

        self.assertEqual(analyzer.session_summary["classification"], "moderate_activity")
        self.assertGreater(analyzer.session_summary["heart_rate_vs_baseline"], 15)
        self.assertIn("baseline", analyzer.session_summary["classification_reason"])

    def test_classifies_recovery_and_explains_heart_rate_trend(self):
        analyzer = FitnessSessionAnalyzer(
            PROFILE, "FIT-2026-006", observations([100, 95, 85, 75], activity=0.5)
        )

        self.assertEqual(analyzer.session_summary["classification"], "recovery")
        self.assertIn("declined", analyzer.session_summary["classification_reason"])

    def test_distinguishes_insufficient_data_from_normal(self):
        analyzer = FitnessSessionAnalyzer(PROFILE, "FIT-2026-003", observations([68, 69]))

        self.assertEqual(analyzer.session_summary["classification"], "insufficient_data")
        self.assertEqual(analyzer.session_summary["data_status"], "insufficient_data")
        self.assertIn("fewer than", analyzer.session_summary["classification_reason"])

    def test_rejected_fraction_marks_usable_session_as_poor_quality(self):
        analyzer = FitnessSessionAnalyzer(
            PROFILE,
            "FIT-2026-004",
            observations([68, 69, 70]),
            rejected_observations=1,
        )

        self.assertEqual(analyzer.session_summary["classification"], "poor_quality")


if __name__ == "__main__":
    unittest.main()