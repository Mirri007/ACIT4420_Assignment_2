"""Read and validate Option A profile and fitness-session CSV files."""

from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass, replace
from pathlib import Path

from .exceptions import CsvFormatError, InvalidIdentifierError, InvalidRecordError


PARTICIPANT_COLUMNS = (
    "participant_id",
    "name",
    "baseline_heart_rate",
    "baseline_skin_response",
    "baseline_temperature",
)
SESSION_COLUMNS = (
    "session_id",
    "participant_id",
    "timestamp",
    "heart_rate",
    "skin_response",
    "temperature",
    "activity_level",
    "signal_quality",
)
MIN_SIGNAL_QUALITY = 0.6


@dataclass(frozen=True)
class RejectedRecord:
    source_file: str
    row_number: int
    field: str
    reason: str
    session_id: str | None = None
    participant_id: str | None = None


def _read_rows(path: str | Path, expected_columns: tuple[str, ...]):
    source = Path(path)
    reader = None
    try:
        with open(source, encoding="utf-8", newline="") as csv_file:
            reader = csv.reader(csv_file, strict=True)
            header = next(reader, None)
            if header != list(expected_columns):
                raise InvalidRecordError(
                    f"expected columns {', '.join(expected_columns)} in the supplied order"
                )
            return [(row_number, row) for row_number, row in enumerate(reader, start=2)]
    except csv.Error as error:
        row_number = reader.line_num if reader is not None else 1
        raise CsvFormatError(row_number, f"malformed CSV: {error}") from error


def _read_table(path: str | Path, expected_columns: tuple[str, ...]):
    try:
        return _read_rows(path, expected_columns), []
    except CsvFormatError as error:
        return [], [RejectedRecord(Path(path).name, error.row_number, "csv", str(error))]
    except InvalidRecordError as error:
        return [], [RejectedRecord(Path(path).name, 1, "header", str(error))]


def _record_fields(
    source_file: str,
    row_number: int,
    row: list[str],
    expected_columns: tuple[str, ...],
):
    if len(row) != len(expected_columns):
        session_id = row[0].strip() if "session_id" in expected_columns and row else ""
        participant_id = row[1].strip() if "participant_id" in expected_columns and len(row) > 1 else ""
        return None, [
            RejectedRecord(
                source_file,
                row_number,
                "row",
                f"expected {len(expected_columns)} columns, found {len(row)}",
                session_id=session_id if re.fullmatch(r"FIT-\d{4}-\d{3}", session_id) else None,
                participant_id=participant_id if re.fullmatch(r"P\d{3}", participant_id) else None,
            )
        ]
    return dict(zip(expected_columns, (value.strip() for value in row))), []


def _parse_identifier(value: str, pattern: str, field: str) -> str:
    if not re.fullmatch(pattern, value):
        raise InvalidIdentifierError(f"{field} must match {pattern}")
    return value


def _parse_integer(value: str, field: str) -> int:
    if not value:
        raise InvalidRecordError("required value is missing")
    try:
        return int(value)
    except ValueError as error:
        raise InvalidRecordError("value must be an integer") from error


def _parse_number(value: str, field: str) -> float:
    if not value:
        raise InvalidRecordError("required value is missing")
    try:
        number = float(value)
    except ValueError as error:
        raise InvalidRecordError("value must be numeric") from error
    if not math.isfinite(number):
        raise InvalidRecordError("value must be finite")
    return number


def _validate_field(
    source_file: str,
    row_number: int,
    field: str,
    value: str,
    parser,
):
    try:
        return parser(value), None
    except (InvalidIdentifierError, InvalidRecordError) as error:
        return None, RejectedRecord(source_file, row_number, field, str(error))


def _add_session_context(rejections: list[RejectedRecord], fields: dict[str, str]):
    session_id = fields.get("session_id", "")
    participant_id = fields.get("participant_id", "")
    valid_session_id = session_id if re.fullmatch(r"FIT-\d{4}-\d{3}", session_id) else None
    valid_participant_id = participant_id if re.fullmatch(r"P\d{3}", participant_id) else None
    return [
        replace(
            rejection,
            session_id=valid_session_id,
            participant_id=valid_participant_id,
        )
        for rejection in rejections
    ]


def load_participants(path: str | Path):
    """Return valid profiles keyed by ID and detailed rejected-row entries."""
    source_file = Path(path).name
    rows, rejected = _read_table(path, PARTICIPANT_COLUMNS)
    participants = {}

    for row_number, row in rows:
        fields, row_errors = _record_fields(
            source_file, row_number, row, PARTICIPANT_COLUMNS
        )
        rejected.extend(row_errors)
        if fields is None:
            continue

        parsed = {}
        checks = (
            ("participant_id", lambda value: _parse_identifier(value, r"P\d{3}", "participant_id")),
            ("name", lambda value: value if value else _missing_value()),
            ("baseline_heart_rate", lambda value: _parse_integer(value, "baseline_heart_rate")),
            ("baseline_skin_response", lambda value: _parse_number(value, "baseline_skin_response")),
            ("baseline_temperature", lambda value: _parse_number(value, "baseline_temperature")),
        )
        row_rejections = []
        for field, parser in checks:
            parsed[field], error = _validate_field(
                source_file, row_number, field, fields[field], parser
            )
            if error:
                row_rejections.append(error)

        if row_rejections:
            rejected.extend(row_rejections)
            continue

        ranges = (
            ("baseline_heart_rate", 35 <= parsed["baseline_heart_rate"] <= 205, "must be between 35 and 205"),
            ("baseline_skin_response", parsed["baseline_skin_response"] >= 0, "cannot be negative"),
            ("baseline_temperature", 25 <= parsed["baseline_temperature"] <= 42, "must be between 25 and 42"),
        )
        for field, valid, reason in ranges:
            if not valid:
                row_rejections.append(RejectedRecord(source_file, row_number, field, reason))
        if row_rejections:
            rejected.extend(row_rejections)
            continue

        participant_id = parsed["participant_id"]
        if participant_id in participants:
            rejected.append(
                RejectedRecord(source_file, row_number, "participant_id", "duplicate participant ID")
            )
            continue
        participants[participant_id] = parsed

    return participants, rejected


def _missing_value():
    raise InvalidRecordError("required value is missing")


def load_sessions(path: str | Path, participant_ids: set[str]):
    """Return valid typed observation rows and detailed rejections.

    A signal quality below 0.6 is rejected as unreliable sensor data.
    """
    source_file = Path(path).name
    rows, rejected = _read_table(path, SESSION_COLUMNS)
    sessions = []

    for row_number, row in rows:
        fields, row_errors = _record_fields(source_file, row_number, row, SESSION_COLUMNS)
        rejected.extend(row_errors)
        if fields is None:
            continue

        parsed = {}
        checks = (
            ("session_id", lambda value: _parse_identifier(value, r"FIT-\d{4}-\d{3}", "session_id")),
            ("participant_id", lambda value: _parse_identifier(value, r"P\d{3}", "participant_id")),
            ("timestamp", lambda value: _parse_integer(value, "timestamp")),
            ("heart_rate", lambda value: _parse_number(value, "heart_rate")),
            ("skin_response", lambda value: _parse_number(value, "skin_response")),
            ("temperature", lambda value: _parse_number(value, "temperature")),
            ("activity_level", lambda value: _parse_number(value, "activity_level")),
            ("signal_quality", lambda value: _parse_number(value, "signal_quality")),
        )
        row_rejections = []
        for field, parser in checks:
            parsed[field], error = _validate_field(
                source_file, row_number, field, fields[field], parser
            )
            if error:
                row_rejections.append(error)
        if row_rejections:
            row_rejections = _add_session_context(row_rejections, fields)
            rejected.extend(row_rejections)
            continue

        if parsed["participant_id"] not in participant_ids:
            row_rejections.append(
                RejectedRecord(source_file, row_number, "participant_id", "unknown participant ID")
            )
        if parsed["timestamp"] < 0:
            row_rejections.append(RejectedRecord(source_file, row_number, "timestamp", "cannot be negative"))
        for field, low, high in (
            ("heart_rate", 35, 205),
            ("temperature", 25, 42),
            ("activity_level", 0, 1),
            ("signal_quality", 0, 1),
        ):
            if not low <= parsed[field] <= high:
                row_rejections.append(
                    RejectedRecord(source_file, row_number, field, f"must be between {low} and {high}")
                )
        if parsed["skin_response"] < 0:
            row_rejections.append(
                RejectedRecord(source_file, row_number, "skin_response", "cannot be negative")
            )
        elif 0 <= parsed["signal_quality"] < MIN_SIGNAL_QUALITY:
            row_rejections.append(
                RejectedRecord(
                    source_file,
                    row_number,
                    "signal_quality",
                    f"below minimum signal quality ({MIN_SIGNAL_QUALITY})",
                )
            )

        row_rejections = _add_session_context(row_rejections, fields)
        if not row_rejections:
            sessions.append(
                {
                    **parsed,
                    "_source_file": source_file,
                    "_row_number": row_number,
                }
            )
        else:
            rejected.extend(row_rejections)

    return sessions, rejected