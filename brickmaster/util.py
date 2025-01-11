"""
Brickmaster 2 Utility Functions
"""
import board
import json
import microcontroller
import os
import sys

# Conditionally import netifaces.
if sys.implementation.name == 'cpython':
    import netifaces

def active_interface():
    """
    Find the active interface.
    :return:
    """
    pass

def board_pins():
    """
    Fetch all the pins for the board. Filter out things that aren't pins.
    :return: list
    """
    available_pins = []
    for item in dir(board):
        if isinstance(getattr(board, item), microcontroller.Pin):
            available_pins.append(item)
    return available_pins

def determine_wifi_hw():
    """
    Figure out what our WiFi hardware is.
    :return: str
    """
    if os.uname().sysname.lower() == 'linux':
        return 'linux'
    elif os.uname().sysname.lower() == 'samd51':
        return 'esp32spi'
    elif os.uname().sysname.lower() == 'esp32':
        return 'esp32'
    else:
        raise OSError("OS Sysname '{}' does not have a known wifi type! Cannot continue!")

# def fetch_config(base_url):
#     """
#     Fetch a configuration json from a remote URL.
#
#     :param base_url: Base URL to fetch from.
#     :type base_url: str
#     :return: str
#     """
#     raise NotImplemented("Some day...")

def interface_status(interface):
    """
    Determine if linux interface is up or down.
    :param interface: Interface name.
    :type interface: str
    :return: bool
    """
    # If the interface has an IP, it's up.
    addr = netifaces.ifaddresses(interface)
    return netifaces.AF_INET in addr

def load_config(config_path):
    """
    Load a configuration json from the local filesystem.

    :param config_path:
    :type config_path: Path
    :return: str
    """
    with open(config_path) as config_file_handle:
        the_json = json.load(config_file_handle)
    return the_json

def mac_id(wifihw='wlan0'):
    """
    Get the MAC ID of the default gateway interface for a Linux system. Circuitpython doesn't need to use this method,
    as MAC is retrieved by the wifi class which is invoked by code.py prior to creating the Brickmaster instance.

    :return:
    """
    # #TODO: Replace this with actually checking against the default route. May be too many edge cases.
    mac = netifaces.ifaddresses(wifihw)[netifaces.AF_PACKET][0]['addr']
    return mac.replace(':', '')