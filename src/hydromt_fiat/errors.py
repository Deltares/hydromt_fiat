"""Custom Hydromt FIAT errors."""


class MissingRegionError(Exception):
    """Exception class for missing region."""

    def __init__(self, message):
        super().__init__(message)
