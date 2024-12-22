"""
Brickmaster2 MQTT Method Generation methods.

These methods are meant to work with either the Linux or CircuitPython classes. It's the responsibility of those
classes to handle the actual publication!
"""

import adafruit_logging
import json
import brickmaster2.util
import board
import brickmaster2.controls.CtrlFlasher

logger = adafruit_logging.getLogger('BrickMaster2')
logger.setLevel(adafruit_logging.DEBUG)

def initial_messages(short_name, topic_prefix='brickmaster2'):
    """
    Generate initial messages to send once on start-up that don't change dynamically.
    """

    outbound_messages = [
        {'topic': topic_prefix + '/' + short_name + '/system/board_id', 'message': board.board_id},
        {'topic': topic_prefix + '/' + short_name + '/system/pins', 'message': brickmaster2.util.board_pins()}
    ]
    return outbound_messages


def messages(core, object_register, short_name, logger, force_repeat=False, topic_prefix='brickmaster2'):
    """
    Generate mqtt messages to send out.

    :param core: Reference to the Brickmaster Core.
    :type core: Object
    :param object_register: The control objects to generate messages for.
    :type object_register: dict
    :param short_name: Short name of the system. No spaces!
    :type short_name: str
    :param logger: The Network Module's logger.
    :type logger: adafruit_logger
    :param force_repeat: Should we send messages that haven't changed since previous send?
    :type force_repeat: bool
    :param topic_prefix: Base topic to send messages to. Defaults to 'brickmaster2'.
    :type topic_prefix: str
    :return: dict
    """
    outbound_messages = [
        {'topic': 'brickmaster2/' + short_name + '/connectivity',
         'message': 'online'}
    ]

    # Controls
    # print("Network (MQTT): Processing Control object list '{}'.".format(object_register['controls']))
    for item in object_register['controls']:
        # print("Network (MQTT): Processing Control '{}' ({})".format(item, type(object_register['controls'][item])))
        control_object = object_register['controls'][item]
        logger.debug("Network (MQTT): Generating control message for control '{}' ({})".
                     format(control_object.id, type(control_object)))
        # logger.debug("Generating messages for object '{}' (type: {})".
        #              format(control_object.id, type(control_object)))
        # Control statuses should be retained. This allows state to be preserved over HA restarts.
        outbound_messages.append(
            {'topic': 'brickmaster2/' + short_name + '/controls/' + control_object.id + '/status',
             'message': control_object.status, 'force_repeat': force_repeat, 'retain': True}
        )
        # Additional information for flashers
        if isinstance(control_object, brickmaster2.controls.CtrlFlasher):
            # Sequence position.
            outbound_messages.append(
                {'topic': 'brickmaster2/' + short_name + '/controls/' + control_object.id + '/seq_pos',
                 'message': control_object.seq_pos, 'force_repeat': force_repeat, 'retain': False}
            )
            # Running Configuration.
            outbound_messages.append(
                {'topic': 'brickmaster2/' + short_name + '/controls/' + control_object.id + '/loiter_time',
                 'message': control_object.loiter_time, 'force_repeat': force_repeat, 'retain': False}
            )
            outbound_messages.append(
                {'topic': 'brickmaster2/' + short_name + '/controls/' + control_object.id + '/switch_time',
                 'message': control_object.switch_time, 'force_repeat': force_repeat, 'retain': False}
            )

    # Displays aren't yet supported. Maybe some day.
    # for item in object_register['displays']:
    # display_object = object_register['displays'][item]
    # logger.debug("Generating messages for object '{}' (type: {})".format(
    #     display_object.id, type(display_object)))
    # outbound_messages

    ## Active script.
    # logger.debug("Generating active script message...")
    outbound_messages.append({
        'topic': topic_prefix + '/' + short_name + '/script/active',
        'message': core.active_script,
        'force_repeat': force_repeat})

    return outbound_messages


# HA Device Info
def ha_device_info(system_id, long_name, ha_area, version):
    """
    Device information to include in Home Assistant discovery messages.
    """
    return_data = dict(
        name=long_name,
        identifiers=[system_id],
        manufacturer='ConHugeCo',
        model='BrickMaster2 Lego Control',
        suggested_area=ha_area,
        sw_version=str(version)
    )
    # Only add suggested_area if it's set to not None, otherwise discovery will reject this.
    if ha_area is not None:
        return_data['suggested_area'] = ha_area
    return return_data


def ha_availability(topic_prefix, short_name):
    """
    Create the availability data for other elements.

    :param topic_prefix: Topic prefix
    :param short_name: Short name of the system.
    :return: dict
    """
    return_data = dict(
        topic=topic_prefix + short_name + "/connectivity",
        payload_not_available="offline",
        payload_available="online"
    )
    return return_data


#TODO: Refactor discovery to support device-based discovery.
# https://www.home-assistant.io/integrations/mqtt/#device-discovery-payload

# HA Discovery
def ha_discovery(short_name, system_id, device_info, topic_prefix, ha_base, meminfo_mode, object_registry):
    """
    Create all discovery messages for publication.

    :param short_name: Short name of the system
    :type short_name: str
    :param system_id: ID of the system
    :type system_id: str
    :param device_info: Device info block.
    :type device_info: str
    :param topic_prefix: Topic prefix
    :type topic_prefix: str
    :param ha_base: Home Assistant topic base
    :type ha_base: str
    :param meminfo_mode: Memory mode.
    :type meminfo_mode: str
    :param object_registry: The network module's object registry.
    :type object_registry: dict
    :return: dict
    """

    outbound_messages = []
    # Set up the Connectivity entities.
    outbound_messages.extend(ha_discovery_connectivity(short_name, system_id, device_info, topic_prefix, ha_base))
    # Set up the Memory Info entities.
    outbound_messages.extend(ha_discovery_meminfo(short_name, system_id, device_info, topic_prefix, ha_base,
                                                  meminfo_mode))
    # Current active script.
    #outbound_messages.extend(ha_discovery_activescript(short_name, system_id, device_info, topic_prefix, ha_base))
    # Script control
    outbound_messages.extend(ha_discovery_script(short_name, system_id, device_info, topic_prefix, ha_base,
                                                 object_registry['scripts']))

    # Discover controls.
    for control_id in object_registry['controls']:
        outbound_messages.extend(ha_discovery_control(
            short_name, system_id, device_info, topic_prefix, ha_base, object_registry['controls'][control_id]))

    #TODO: Add discovery for scripts and send script data, ie: elapsed time.
    # The outbound topics dict includes references to the objects, so we can get the objects from there.
    # for item in self._topics_outbound:
    #     if isinstance(self._topics_outbound[item]['obj'], brickmaster2.controls.CtrlGPIO):
    #         discovered = False
    #         while not discovered:
    #             discovered = self.ha_discovery_gpio(self._topics_outbound[item]['obj'])
    return outbound_messages


def ha_discovery_activescript(short_name, system_id, device_info, topic_prefix, ha_base):
    """
    Create Home Assistant discovery message for system connectivity

    :param short_name: Short name of the system
    :param system_id: ID of the system
    :param device_info: Device info block.
    :param topic_prefix: Topic prefix
    :param ha_base: Home Assistant topic base
    :return: list
    """
    discovery_dict = {
        'name': "Active Script",
        'object_id': short_name + "_activescript",
        'device': device_info,
        'unique_id': system_id + "_activescript",
        'state_topic': topic_prefix + short_name + '/active_script',
        'availability': ha_availability(topic_prefix, short_name)
    }
    discovery_json = json.dumps(discovery_dict)
    discovery_topic = ha_base + '/sensor/' + 'bm2_' + system_id + '/activescript/config'
    return [{'topic': discovery_topic, 'message': discovery_json}]


def ha_discovery_connectivity(short_name, system_id, device_info, topic_prefix, ha_base):
    """
    Create Home Assistant discovery message for system connectivity

    :return: tuple
    """
    discovery_dict = {
        'name': "Connectivity",
        'object_id': short_name + "_connectivity",
        'device': device_info,
        'device_class': 'connectivity',
        'unique_id': system_id + "_connectivity",
        'state_topic': topic_prefix + short_name + '/connectivity',
        'payload_on': 'online',
        'payload_off': 'offline'
    }
    discovery_json = json.dumps(discovery_dict)
    discovery_topic = ha_base + '/binary_sensor/' + 'bm2_' + system_id + '/connectivity/config'
    return [{'topic': discovery_topic, 'message': discovery_json}]
    # self._mqtt_client.publish(discovery_topic, discovery_json, True)
    # self._topics_outbound['connectivity']['discovery_time'] = time.monotonic()


def ha_discovery_meminfo(short_name, system_id, device_info, topic_prefix, ha_base, mode):
    """
    Create Home Assistant discovery message for free memory.

    :param short_name: Short name of the system
    :param system_id: ID of the system
    :param device_info: Device info block.
    :param topic_prefix: Topic prefix
    :param ha_base: Home Assistant topic base
    :param mode: Memory mode.
    :return: dict
    """

    # Define all the entity options, then send based on what's been configured.

    # Memfreepct
    memfreepct_dict = {
        'name': "Memory Available (Pct)",
        'object_id': short_name + "_memfreepct",
        'device': device_info,
        'unique_id': system_id + "_memfreepct",
        'state_topic': topic_prefix + short_name + '/meminfo',
        'unit_of_measurement': '%',
        'value_template': '{{ value_json.pct_avail }}',
        'icon': 'mdi:memory',
        'availability': ha_availability(topic_prefix, short_name)
    }
    memusedpct_dict = {
        'name': "Memory Used (Pct)",
        'object_id': short_name + "_memusedpct",
        'device': device_info,
        'unique_id': system_id + "_memusedpct",
        'state_topic': topic_prefix + short_name + '/meminfo',
        'unit_of_measurement': '%',
        'value_template': '{{ value_json.pct_used }}',
        'icon': 'mdi:memory',
        'availability': ha_availability(topic_prefix, short_name)
    }
    memfreebytes_dict = {
        'name': "Memory Available (Bytes)",
        'object_id': short_name + "_memfree",
        'device': device_info,
        'unique_id': system_id + "_memfree",
        'state_topic': topic_prefix + short_name + '/meminfo',
        'unit_of_measurement': 'B',
        'value_template': '{{ value_json.mem_free }}',
        'icon': 'mdi:memory',
        'availability': ha_availability(topic_prefix, short_name)
    }
    memusedbytes_dict = {
        'name': "Memory Used (Bytes)",
        'object_id': short_name + "_memusedpct",
        'device': device_info,
        'unique_id': system_id + "_memusedpct",
        'state_topic': topic_prefix + short_name + '/meminfo',
        'unit_of_measurement': 'B',
        'value_template': '{{ value_json.mem_used }}',
        'icon': 'mdi:memory',
        'availability': ha_availability(topic_prefix, short_name)
    }

    if mode == 'unified':
        # Unified just sets up Memory, Percent Free. Add in the other memory info as JSON attributes.
        memfreepct_dict['json_attributes_topic'] = topic_prefix + short_name + '/meminfo'
        return [{'topic': ha_base + '/sensor/' + 'bm2_' + system_id + '/memfreepct/config',
                 'message': json.dumps(memfreepct_dict)}]
    elif mode == 'unified-used':
        memusedpct_dict['json_attributes_topic'] = topic_prefix + short_name + '/meminfo'
        return [{'topic': ha_base + '/sensor/' + 'bm2_' + system_id + '/memusedpct/config',
                 'message': json.dumps(memusedpct_dict)}]
    elif mode == 'split-pct':
        # When providing separate memory percentages, add JSON attributes on free or used.
        memfreepct_dict['json_attributes_topic'] = topic_prefix + short_name + '/meminfo'
        memfreepct_dict['json_attributes_template'] = \
            "{{ {'mem_free': value_json.mem_free, 'mem_total': value_json.mem_total} | tojson }}"
        memusedpct_dict['json_attributes_topic'] = topic_prefix + short_name + '/meminfo'
        memusedpct_dict['json_attributes_template'] = \
            "{{ {'mem_used': value_json.mem_used, 'mem_total': value_json.mem_total} | tojson }}"
        return [
            {'topic': ha_base + '/sensor/' + 'bm2_' + system_id + '/memfreepct/config',
             'message': json.dumps(memfreepct_dict)},
            {'topic': ha_base + '/sensor/' + 'bm2_' + system_id + '/memusedpct/config',
             'message': json.dumps(memusedpct_dict)}]
    elif mode == 'split-all':
        # If we're splitting everything, we don't need to add JSON attributes.
        return [
            {'topic': ha_base + '/sensor/' + 'bm2_' + system_id + '/memfreepct/config',
             'message': json.dumps(memfreepct_dict)},
            {'topic': ha_base + '/sensor/' + 'bm2_' + system_id + '/memusedpct/config',
             'message': json.dumps(memusedpct_dict)},
            {'topic': ha_base + '/sensor/' + 'bm2_' + system_id + '/memfreebytes/config',
             'message': json.dumps(memfreebytes_dict)},
            {'topic': ha_base + '/sensor/' + 'bm2_' + system_id + '/memusedbytes/config',
             'message': json.dumps(memusedbytes_dict)}
        ]
    #self._topics_outbound['meminfo']['discovery_time'] = time.monotonic()


def ha_discovery_control(short_name, system_id, device_info, topic_prefix, ha_base, control):
    """
    Discovery message for a GPIO control.

    :param short_name: Short name of the system.
    :type short_name: str
    :param system_id: System ID
    :type system_id: str
    :param device_info: Device Info block
    :type device_info:
    :param topic_prefix: Our own topic prefix
    :param ha_base: Prefix for Home Assistant
    :param control: GPIO control object
    :type control: brickmaster2.controls.Control
    :return: list
    """

    discovery_dict = {
        'name': control.name,
        'object_id': short_name + "_" + control.id,
        'device': device_info,
        'unique_id': system_id + "_" + control.id,
        'command_topic': topic_prefix + short_name + '/controls/' + control.id + '/set',
        'state_topic': topic_prefix + short_name + '/controls/' + control.id + '/status',
        'availability': ha_availability(topic_prefix, short_name)
    }

    # This try/except is arguably a legacy holdover...it may be possible to remove it in the future.
    try:
        discovery_dict['icon'] = control.icon
    except AttributeError:
        logger.warning("Network (MQTT): Control '{}' does not have icon set. This should never happen. Defaulting to 'toy-brick'".format(control.id))
        discovery_dict['icon'] = 'mdi:toy-brick'

    return [{'topic': ha_base + '/switch/' + 'bm2_' + system_id + '/' + control.id + '/config',
             'message': json.dumps(discovery_dict)}]


def ha_discovery_script(short_name, system_id, device_info, topic_prefix, ha_base,
                        script_registry):
    """
    Create the script control based on the available scripts

    :param short_name:
    :param system_id:
    :param device_info:
    :param topic_prefix:
    :param ha_base:
    :param script_registry:
    :return: list
    """
    # If no scripts are defined, don't do discovery.

    if len(script_registry) == 0:
        logger.info("MQTT: Cannot create discovery messages for scripts, none defined!")
        return []

    return_data = []

    # MQTT Selector.
    # Assemble the options list for the selector. Always start with Inactive and Abort
    options_list = ['Inactive', 'Abort']
    script_names = []
    for script in script_registry:
        logger.debug("Adding script ID '{}', Name '{}'".
                     format(script_registry[script].id, script_registry[script].name))
        script_names.append(script_registry[script].name)
    options_list.extend(sorted(script_names))

    script_selector = {
        'topic': ha_base + '/select/' + 'bm2_' + system_id + '/script/config',
        'message': {
            'name': short_name + ' Script Selection',
            'object_id': short_name + "_script_select",
            'device': device_info,
            'unique_id': system_id + "_script_select",
            'icon': 'mdi:script-text-outline',
            'options': options_list,
            'command_topic': topic_prefix + short_name + '/script/set',
            'state_topic': topic_prefix + short_name + '/script/active',
            'availability': ha_availability(topic_prefix, short_name)
        }
    }
    return_data.append(script_selector)

    return return_data

# def ha_discovery_display(short_name, system_id, device_info, topic_prefix, ha_base, display_obj):
#     """
#     Discovery message for a GPIO control.
#
#     :param short_name: Short name of the system.
#     :type short_name: str
#     :param system_id: System ID
#     :type system_id: str
#     :param device_info: Device Info block
#     :type device_info:
#     :param topic_prefix: Our own topic prefix
#     :param ha_base: Prefix for Home Assistant
#     :param display_obj: Display object
#     :type display_obj: brickmaster2.BM2Display
#     :return: list
#     """
#     raise NotImplemented("Nope, not yet!")
