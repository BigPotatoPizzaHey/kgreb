class UnclosedJSONError(Exception):
    """
    Raised when a JSON string is never closed.
    """
    pass

# Deprecated exceptions because it is more appropriate to give a warning instead of an error
#
# class UserConnectError(Exception):
#     """
#     Base class for errors raised when a user cannot be found
#     """
#     pass
#
# class DeletedUser(UserConnectError):
#     pass
#
#
# class InvalidUser(UserConnectError):
#     pass
#
#
# class ForbiddenUser(UserConnectError):
#     pass
