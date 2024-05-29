import sys
import json

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


def mac_id():
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
        raise NotImplemented("Circuitpython not yet tested.")
    else:
        raise NotImplemented("Unknown platform!")


def active_interface():
    """
    Find the active interface.
    :return:
    """
    pass


def interface_status(interface):
    """
    Determine if interface is up or down.
    :param interface: Interface name.
    :type interface: str
    :return: bool
    """
    if sys.implementation.name == 'cpython':  # Assuming cpython is linux...
        # If the interface has an IP, it's up.
        addr = netifaces.ifaddresses(interface)
        return netifaces.AF_INET in addr
    elif sys.implementation.name == 'circuitpython':
        raise NotImplemented("Circuitpython not yet tested.")
    else:
        raise NotImplemented("Unknown platform!")
