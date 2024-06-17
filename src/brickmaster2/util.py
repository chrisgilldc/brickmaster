import json
import os
import sys


if sys.implementation.name == 'cpython':
    import netifaces


def fetch_config(base_url):
    """
    Fetch a configuration json from a remote URL.

    :param base_url: Base URL to fetch from.
    :type base_url: str
    :return: str
    """
    pass


def load_config(config_path):
    """
    Load a configuration json from the local filesystem.

    :param config_path:
    :type config_path: Path
    :return: str
    """
    with open(config_path, 'r') as config_file_handle:
        the_json = json.load(config_file_handle)
    return the_json


def mac_id(wifihw=None):
    """
    Get the MAC ID of the default gateway interface for a Linux system.
    :return:
    """
    # getmac = __import__('getmac')
    # #TODO: Replace this with actually checking against the default route. May be too many edge cases.
    # mac = getmac.get_mac_address(interface="wlan0")
    # return mac.replace(':', '')
    if sys.implementation.name == 'cpython':
        mac = netifaces.ifaddresses('wlan0')[netifaces.AF_PACKET][0]['addr']
        return mac.replace(':', '')
    elif sys.implementation.name == 'circuitpython':
        #TODO: Test for Circuitpython MACs.
        # Try to auto-determine Wifi hardware if not explicitly set.
        if wifihw is None:
            pass
        if wifihw == 'esp32':
            pass
        elif wifihw == 'esp32spi':
            pass
        else:
            raise NotImplemented("Cannot determine platform!")
    else:
        raise NotImplemented("Unknown platform!")

def determine_wifi_hw():
    """
    Figure out what our WiFi hardware is.
    :return: str
    """
    if os.uname().sysname.lower() == 'linux':
        return 'linux'
    elif os.uname().sysname.lower() in ('samd51'):
        return 'esp32spi'
    elif os.uname().sysname.lower() in ('esp32'):
        return 'esp32'
    else:
        raise OSError("OS Sysname '{}' does not have a known wifi type! Cannot continue!")

def active_interface():
    """
    Find the active interface.
    :return:
    """
    pass


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