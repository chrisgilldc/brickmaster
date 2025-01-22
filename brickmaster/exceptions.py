"""
Brickmaster Exceptions
"""

#TODO: Fix these to properly wrap them and take their strings.

class BMRecoverableError(Exception):
    """
    Brickmaster error that may be fixable by resetting the system.
    """
    pass

class BMFatalError(Exception):
    """
    Brickmaster error that cannot be fixed by resetting the system.
    """
    pass