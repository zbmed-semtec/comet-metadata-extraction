"""Custom errors for the extraction layer."""


class UnknownPropertyError(ValueError):
    """Raised when a property is not known to the schema or no plugin declares it."""
