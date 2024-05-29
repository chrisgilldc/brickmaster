import sys

# Import common Home Assistant methods.

from . import mqtt

# Conditionally import the correct version of the module.
if sys.implementation.name == 'cpython':
    from .linux import BM2NetworkLinux
elif sys.implementation.name == 'circuitpython':
    from .circuitpython import BM2NetworkCircuitPython