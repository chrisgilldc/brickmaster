"""
Brickmaster Constants
"""

# Network status codes. Can be applied to MQTT or WiFi, if we're managing WiFi.
NET_STATUS_DISCONNECTED = 0 # Not Connected
NET_STATUS_CONNECTED = 1 # Connected!
NET_STATUS_CONNECTING = 2 # In the process of connecting, ie: not yet acknowledged
NET_STATUS_DISCONNECT_PLANNED = 3 # Planning to disconnect. Use this to flag that we're
                                # intentionally disconnecting and shouldn't reconnect immediately.
NET_STATUS_NOACTION = 100 # Nothing to do.