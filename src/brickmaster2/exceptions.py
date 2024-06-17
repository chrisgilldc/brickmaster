"""
BrickMaster2 Exceptions
"""

class BM2RecoverableError(Exception):
    """
    BrickMaster2 error that may be fixable by resetting the system.
    """
    pass

class BM2FatalError(Exception):
    """
    BrickMaster2 error that cannot be fixed by resetting the system.
    """
    pass