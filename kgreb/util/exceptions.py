class UnclosedJSONError(Exception):
    """
    Raised when a JSON string is never closed.
    """
    pass