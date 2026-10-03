"""Domain exceptions used while validating assignment input files."""


class InvalidIdentifierError(ValueError):
    """Raised when a participant or session identifier has an invalid format."""


class InvalidRecordError(ValueError):
    """Raised when a CSV record or table cannot be accepted."""


class CsvFormatError(InvalidRecordError):
    """Raised when CSV syntax is malformed at a known source row."""

    def __init__(self, row_number: int, message: str):
        super().__init__(message)
        self.row_number = row_number