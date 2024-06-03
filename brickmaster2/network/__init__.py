import sys

# Import common MQTT methods.
from . import mqtt

# Conditionally import the correct version of the module.
if sys.implementation.name == 'cpython':
    from .linux import BM2NetworkLinux
elif sys.implementation.name == 'circuitpython':
    from .wifi import BM2WiFi
    from .circuitpython import BM2NetworkCircuitPython