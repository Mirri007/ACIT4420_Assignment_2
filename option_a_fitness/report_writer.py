"""Write deterministic CSV and text reports for fitness-session analysis."""

from __future__ import annotations

import csv
from pathlib import Path

from .csv_fitness_loader import RejectedRecord


SUMMARY_COLUMNS = (
    "session_id",
    "participant_id",
    "classification",
    "data_status",
    "valid_observations",
    "rejected_observations",
    "total_observations",
    "average_heart_rate",
    "min_heart_rate",
    "max_heart_rate",
    "average_skin_response",
    "average_temperature",
    "average_activity",
    "min_activity",
    "max_activity",
    "average_signal_quality",
    "heart_rate_vs_baseline",
    "skin_response_vs_baseline",
    "temperature_vs_baseline",
    "classification_reason",
)


def write_reports(
    output_directory: str | Path,
    summaries: list[dict],
    rejected_records: list[RejectedRecord],
):
    """Create or replace all Assignment 2 output files and return their paths."""
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    summary_path = output_path / "analysis_summary.csv"
    report_path = output_path / "analysis_report.txt"
    rejected_path = output_path / "rejected_records.txt"

    ordered_summaries = sorted(summaries, key=lambda summary: summary["session_id"])
    with open(summary_path, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(ordered_summaries)

    with open(report_path, "w", encoding="utf-8", newline="") as report_file:
        if not ordered_summaries:
            report_file.write("No sessions could be analyzed.\n")
        for summary in ordered_summaries:
            report_file.write(
                f"Session {summary['session_id']} ({summary['participant_id']})\n"
            )
            report_file.write(
                f"  Classification: {summary['classification']}\n"
                f"  Data status: {summary['data_status']}\n"
                f"  Observations: {summary['valid_observations']} usable, "
                f"{summary['rejected_observations']} rejected, "
                f"{summary['total_observations']} total\n"
                f"  Reason: {summary['classification_reason']}\n"
            )
            for field in (
                "average_heart_rate",
                "min_heart_rate",
                "max_heart_rate",
                "average_skin_response",
                "average_temperature",
                "average_activity",
                "min_activity",
                "max_activity",
                "average_signal_quality",
                "heart_rate_vs_baseline",
                "skin_response_vs_baseline",
                "temperature_vs_baseline",
            ):
                report_file.write(f"  {field}: {summary[field]}\n")
            report_file.write("\n")

    with open(rejected_path, "w", encoding="utf-8", newline="") as rejected_file:
        ordered_rejections = sorted(
            rejected_records,
            key=lambda item: (item.source_file, item.row_number, item.field, item.reason),
        )
        if not ordered_rejections:
            rejected_file.write("No records were rejected.\n")
        for rejection in ordered_rejections:
            row_label = str(rejection.row_number) if rejection.row_number else "file-level"
            context = ""
            if rejection.session_id:
                context = f" session={rejection.session_id}"
            if rejection.participant_id:
                context += f" participant={rejection.participant_id}"
            rejected_file.write(
                f"{rejection.source_file}: row {row_label}{context}; "
                f"field {rejection.field}; {rejection.reason}\n"
            )

    return [summary_path, report_path, rejected_path]