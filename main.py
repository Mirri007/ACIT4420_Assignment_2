"""Command-line entry point for the Option A Assignment 2 analyzer."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

from option_a_fitness.csv_fitness_loader import (
    RejectedRecord,
    load_participants,
    load_sessions,
)
from option_a_fitness.fitness_analyzer import FitnessSessionAnalyzer
from option_a_fitness.report_writer import write_reports


def _file_rejection(path: str | Path, reason: str):
    return RejectedRecord(Path(path).name, 0, "file", reason)


def _load_profiles(path: str | Path):
    try:
        return load_participants(path)
    except FileNotFoundError as error:
        return {}, [_file_rejection(path, f"file not found: {error}")]
    except PermissionError as error:
        return {}, [_file_rejection(path, f"permission denied: {error}")]
    except OSError as error:
        return {}, [_file_rejection(path, f"could not read file: {error}")]
    except ValueError as error:
        return {}, [_file_rejection(path, f"invalid profile data: {error}")]


def _load_session_file(path: str | Path, participant_ids: set[str]):
    try:
        return load_sessions(path, participant_ids)
    except FileNotFoundError as error:
        return [], [_file_rejection(path, f"file not found: {error}")]
    except PermissionError as error:
        return [], [_file_rejection(path, f"permission denied: {error}")]
    except OSError as error:
        return [], [_file_rejection(path, f"could not read file: {error}")]
    except ValueError as error:
        return [], [_file_rejection(path, f"invalid session data: {error}")]


def _invalid_sessions_path(sessions_path: str | Path):
    source = Path(sessions_path)
    return source.with_name(f"{source.stem}_invalid{source.suffix}")


def analyze_files(
    profiles_path: str | Path,
    sessions_path: str | Path,
    invalid_sessions_path: str | Path | None,
    output_path: str | Path,
):
    """Load both session files, analyze every identifiable session and write reports."""
    participants, profile_rejections = _load_profiles(profiles_path)
    valid_rows, valid_file_rejections = _load_session_file(
        sessions_path, set(participants)
    )
    if invalid_sessions_path is None:
        invalid_rows, invalid_file_rejections = [], []
    else:
        invalid_rows, invalid_file_rejections = _load_session_file(
            invalid_sessions_path, set(participants)
        )
    rejected_records = (
        profile_rejections + valid_file_rejections + invalid_file_rejections
    )
    session_rejections = valid_file_rejections + invalid_file_rejections

    groups = {}
    for row in valid_rows + invalid_rows:
        session_id = row["session_id"]
        participant_id = row["participant_id"]
        group = groups.setdefault(
            session_id,
            {"participant_id": participant_id, "rows": [], "rejected_rows": set()},
        )
        if group["participant_id"] != participant_id:
            rejected_records.append(
                RejectedRecord(
                    row["_source_file"],
                    row["_row_number"],
                    "participant_id",
                    "session ID is already associated with another participant",
                    session_id=session_id,
                    participant_id=participant_id,
                )
            )
            continue
        group["rows"].append(
            {key: value for key, value in row.items() if not key.startswith("_")}
        )

    for rejection in session_rejections:
        if not rejection.session_id or rejection.participant_id not in participants:
            continue
        group = groups.setdefault(
            rejection.session_id,
            {
                "participant_id": rejection.participant_id,
                "rows": [],
                "rejected_rows": set(),
            },
        )
        if group["participant_id"] == rejection.participant_id:
            group["rejected_rows"].add((rejection.source_file, rejection.row_number))

    summaries = []
    for session_id, group in sorted(groups.items()):
        try:
            profile = participants[group["participant_id"]]
        except KeyError:
            rejected_records.append(
                RejectedRecord(
                    "analysis",
                    0,
                    "participant_id",
                    f"profile not found for {group['participant_id']}",
                    session_id=session_id,
                    participant_id=group["participant_id"],
                )
            )
            continue
        analyzer = FitnessSessionAnalyzer(
            profile,
            session_id,
            group["rows"],
            rejected_observations=len(group["rejected_rows"]),
        )
        summaries.append(analyzer.session_summary)

    try:
        output_files = write_reports(output_path, summaries, rejected_records)
    except PermissionError as error:
        raise PermissionError(
            f"permission denied writing reports in {output_path}: {error}"
        ) from error
    except OSError as error:
        raise OSError(f"could not write reports in {output_path}: {error}") from error
    except csv.Error as error:
        raise OSError(f"could not serialize reports in {output_path}: {error}") from error
    accepted_rows = sum(len(group["rows"]) for group in groups.values())
    rejected_rows = len(
        {(item.source_file, item.row_number) for item in rejected_records}
    )
    return accepted_rows, rejected_rows, output_files


def build_parser():
    parser = argparse.ArgumentParser(description="Analyze fitness sessions from CSV files.")
    parser.add_argument("--profiles", required=True, help="path to participants.csv")
    parser.add_argument("--sessions", required=True, help="path to fitness_sessions.csv")
    parser.add_argument(
        "--invalid-sessions",
        help="path to fitness_sessions_invalid.csv (defaults beside --sessions)",
    )
    parser.add_argument("--output", default="output", help="report output directory")
    return parser


def main(argv=None):
    arguments = build_parser().parse_args(argv)
    invalid_path = arguments.invalid_sessions or _invalid_sessions_path(arguments.sessions)
    try:
        accepted, rejected, output_files = analyze_files(
            arguments.profiles,
            arguments.sessions,
            invalid_path,
            arguments.output,
        )
    except OSError as error:
        print(f"Could not write analysis reports: {error}", file=sys.stderr)
        return 2

    print(f"Analysis complete: {accepted} accepted rows, {rejected} rejected rows.")
    print("Created report files:")
    for output_file in output_files:
        print(f"- {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())