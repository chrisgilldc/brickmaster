# Brickmaster2 Script

import adafruit_logging as logger
import time
import math
from pprint import pformat
from brickmaster2.segment_format import time_7s, number_7s

class BM2Script:
    def __init__(self, script, controls):
        # Create a logger.
        self._logger = logger.getLogger('BrickMaster2')
        # Initialize variables
        self._run_count = 0  # Which run of the script are we on. Starts at zero!
        self._status = 'idle'  # Status, start as idle.
        self._blocks = []  # Blocks to execute.
        self._start_time = None  # When we started.
        self._name = None
        self._type = None
        self._run = None
        self._loops = None
        self._current_loop = 0
        self._active_block = None
        self._pending_block = 0
        self._at_completion = "off"
        self._topics = None
        # Save the controls references.
        self._controls = controls

        # Validate and load the script.
        self._validate(script)

        # Create MQTT topics.
        self._create_topics()

    # Name of the script.
    @property
    def name(self):
        return self._name

    # Script Type
    @property
    def type(self):
        return self._type

    @property
    def loops(self):
        if self._type == 'once':
            # Single run scripts definitionally only run once!
            return 1
        else:
            return self._loops

    # Which loop are we on?
    @property
    def current_loop(self):
        return self._current_loop

    # Report our status.
    # Will be 'idle' or 'running'
    @property
    def status(self):
        return self._status

    # How long does the script take to run?
    @property
    def run_time(self):
        return self._run_time

    # How long has the script been running for? If the script hasn't started, it's obviously zero.
    @property
    def time_elapsed(self):
        if self._start_time is None:
            return 0
        else:
            return time.monotonic() - self._start_time

    # How much time is left? If the script hasn't started, it's all the time.
    @property
    def time_remaining(self):
        return self._run_time - (time.monotonic() - self._start_time)

    # Topics property.
    @property
    def topics(self):
        return self._topics

    # Set the running state. This is how the script gets started and stopped.
    def set(self, value):
        self._logger.debug("Setting script '{}' to '{}'".format(self.name, value))
        # Starting...
        if value == 'start':
            self._status = 'running'
            self._current_loop = 1
            self._active_block = None
            self._pending_block = 0
            if self._at_completion == 'restore':
                self._logger.debug("Freezing system state.")
                self._saved_state = self._system_status()
            self._start_time = time.monotonic()
        # Stopping...
        elif value == 'stop':
            self._start_time = None
            self._status = 'idle'
            self._reset_blocks()
            if self._at_completion == 'restore':
                self._logger.debug("Restoring original system state.")
                for control_state in self._saved_state:
                    control_state[0].set(control_state[1])
                self._saved_state = None
            else:
                for control in self._controls:
                    control.set('off')

    # Executor. Called to take actions based on the internal time index.
    def execute(self, implicit_start=False):
        # What to do if called when idle.
        if self._status == 'idle':
            if implicit_start:
                self.set('start')
            else:
                return

        # Is the active block none? This means we're at the start of the script. Move to Block 0
        if self._active_block is None:
            self._active_block = 1
        # Are we within a tenth of a second of the end time of the active block?
        if (time.monotonic() - self._start_time) >= (self._blocks[self._active_block]['end_time']):
            self._active_block += 1

        # Are we at the end of the script?
        if self._active_block >= len(self._blocks) - 1:
            # For repeating script. loop it.
            if self._run == 'repeat' and self._current_loop < self._loops:
                self._logger.debug("Ending loop {}.".format(self._current_loop))
                self._current_loop += 1
                self._reset_blocks()
                self._logger.debug("Script starting new cycle.")
                # Set Active block back to 0
                self._active_block = 0
                self._start_time = time.monotonic()
            else:
                self._logger.debug("Script Complete.")
                self.set('stop')

        self._execute_block(self._active_block)

    def _execute_block(self, block_num):
        # Traverse the controls and pass the intended value.
        if self._blocks[block_num]['status'] != 'complete':
            self._logger.debug("Executing control actions for block {} at run time {}".
                               format(block_num, time.monotonic() - self._start_time))
            for control_action in self._blocks[block_num]['control_actions']:
                control_action[0].set(control_action[1])
        self._blocks[block_num]['status'] = 'complete'

    # Simple method to reset the blocks from run to pending. Used when the script ends, or to reset the loop.
    def _reset_blocks(self):
        for block in self._blocks:
            block['status'] = 'pending'

    # Script validation.
    # Pull basic settings for the object out of the provided script.
    def _validate(self, script):
        # Make sure our required parameters are present.
        required_parameters = ["script", "type", "run", "blocks"]
        for rp in required_parameters:
            if rp not in script:
                self._logger.error("Required script parameter '{}' not present. Cannot continue.".format(rp))
                raise ValueError

        if len(script['blocks']) == 0:
            self._logger.error("Nothing defined in script blocks, so nothing to do! Cannot continue.")
            raise ValueError

        # Name is a string, it can be anything.
        self._name = script['script']
        # Validate settings for type and run.
        # Type of script.
        if script['type'] not in ('basic', 'flight'):
            self._logger.error("Script type must be 'basic' or 'flight'. Instead got '{}'. Cannot continue.".
                               format(script['type']))
        else:
            self._type = script['type']
        try:
            if script['at_completion'] == 'restore':
                self._at_completion = 'restore'
        except KeyError:
            pass
        # Run mode.
        if script['run'] not in ('once', 'repeat'):
            self._logger.error("Script run mode must be 'once' or 'repeat'. Instead got '{}'. Cannot continue.".
                               format(script['type']))
            raise ValueError("Script run mode must be 'once' or 'repeat'.")
        else:
            self._run = script['run']
            if self._run == 'repeat':
                try:
                    self._loops = script['loops']
                except KeyError:
                    self._logger.error("Script is repeating but no repeat count set. Cannot continue.")
                    raise ValueError("Script is repeating but no repeat count set.")

        # Check the blocks!
        i = 0
        while i < len(script['blocks']):
            self._logger.debug("Processing block number {}".format(i))
            try:
                block_data = self._validate_block(script['blocks'][i])
            except:
                raise ValueError("Could not validate block {} in script. Cannot continue.".format(i + 1))
            # Calculate the start and end time.
            if i == 0:
                block_data['start_time'] = 0
            else:
                # This block starts one second after the previous block.
                previous_end_time = self._blocks[i - 1]['end_time']
                block_data['start_time'] = previous_end_time + 1
            block_data['end_time'] = block_data['start_time'] + block_data['run_time']
            # Last block end time becomes the total run time, since we go from 0 to the end time of the last block.
            self._run_time = block_data['end_time']
            self._blocks.append(block_data)
            i += 1

    # Create the blocks and pre-fill various items.
    def _validate_block(self, block):
        # Iterate the configured blocks and add them.
        required_parameters = ['run_time', 'controls']
        # Make sure required parameters exist.
        for rp in required_parameters:
            if rp not in block:
                raise ValueError("Required parameter {} not in script block.".format(rp))

        block_data = {
            'name': None,
            'run_time': block['run_time'],
            'status': "pending",
            'start_time': None,
            'end_time': None,
            'control_actions': [],
        }
        if 'name' in block:
            block_data['name'] = block['name']
        # IF there's flight data, stash it. This actually gets processed by the subclass.
        if 'flight' in block:
            block_data['flight'] = block['flight']
        for control in block['controls']:
            # If the named control doesn't exist, skip it.
            if control not in self._controls:
                self._logger.warning("Block references non-existent control '{}'. Ignoring.".format(control))
            else:
                block_data['control_actions'].append((self._controls[control], block['controls'][control]))
        # For any control that didn't have an explicit definition, set it to off.
        for control in self._controls:
            if control not in block['controls']:
                block_data['control_actions'].append((self._controls[control], "off"))
        return block_data

    # Method to save a snapshot of the system state.
    def _system_status(self):
        return_list = []
        for control in self._controls:
            control_ref = self._controls[control]
            return_list.append(
                (control_ref, control_ref.status)
            )
        return return_list

    # Create topics for the network to latch onto.
    # We don't actually need to do anything dynamic, as this is pretty straight forward.
    def _create_topics(self):
        self._topics = [
            {
                'topic': self.name + '/set',
                'type': 'inbound',
                'values': ['start', 'stop']  # Values an inbound topic will consider valid.
            },
            {
                'topic': self.name + '/status',
                'type': 'outbound',
                'retain': False,  # Should this be retained? False is almost always the right choice.
                'repeat': False,  # Should this be sent, even if the value doesn't change?
                'obj': self,
                'value_attr': 'status'
            }
        ]


class BM2FlightScript(BM2Script):
    def __init__(self, script, controls, displays):
        # Call the superclass init
        super().__init__(script, controls)
        self._logger.debug("Flight script init...")
        # Build the flight plan.
        self._flight_plan = []
        self._build_flight_plan(script)
        # Convert the display map.
        self._display_map = {}
        self._map_displays(script, displays)
        self._logger.debug("Build display map...")
        self._logger.debug(pformat(self._display_map))

    def execute(self, implicit_start=False):
        # Call the parent class execute. This will handle all the controls.
        super().execute(implicit_start=implicit_start)

        # Now do the flight-specific items.
        # Make our run time an integer.
        run_time = math.ceil(time.monotonic() - self._start_time)
        flight_data = self._flight_plan[run_time]
        self._logger.debug("Using flight plan data for run time: {}".format(run_time))
        self._logger.debug(pformat(flight_data))
        # Send flight plan data to the displays.
        # Mission Elapsed Time goes through the time string processor.
        self._display_map['met'].show(time_7s(flight_data['met']))
        # Velocity and Altitude go through the general number preprocessor.
        for item in ('vel','alt'):
            self._display_map[item].show(number_7s(flight_data[item]))

    # Create the flight plan. This is second-by-second data pre-calculated.
    def _build_flight_plan(self, script):
        # Wipe the flight plan, make sure we don't have competing data.
        self._flight_plan = []

        run_time = 0
        met_state = 'hold'
        met = 0  # Mission elapsed time.
        alt = 0  # Altitude
        vel = 0  # Velocity
        da = 0  # The per-second change in altitude
        dv = 0  # Per-second change in velocity
        active_block = 0

        # Find the end time, which is the end time of the total
        end_time = self._blocks[-1]['end_time']

        self._logger.debug("Flight script blocks: {}".format(len(self._blocks)))
        self._logger.debug("Flight end time: {}".format(end_time))

        # Pre-create empty values for the list. That way we can direct assign it makes it easier to check for gaps.
        i = 0
        while i <= end_time:
            self._flight_plan.append(None)
            i += 1
        # Pre-calculate each second to figure out what's what.
        while run_time <= end_time:
            self._logger.debug("\tProcessing run time: {}".format(run_time))
            # If time has advanced past the end of the current block, move to the next one.
            if run_time > self._blocks[active_block]['end_time']:
                active_block += 1
                self._logger.debug("\t\tAdvancing to block {}".format(active_block))
                self._logger.debug(pformat(self._blocks[active_block]))
                # Calculate the altitude and velocity steps needed.
                self._logger.debug("\t\tCurrent Values:\n\t\t\tAlt: {}\n\t\t\tdA: {}\n\t\t\tVel: {}\n\t\t\tdV: {}".
                                   format(alt, da, vel, dv))
                try:
                    da = (float(self._blocks[active_block]['flight']['final_altitude']) - alt) / self._blocks[active_block]['run_time']
                except (KeyError, TypeError):
                    try:
                        if self._blocks[active_block]['flight']['alt'] == 'glide':
                            self._logger.debug("\t\tAltitude is gliding. Keeping previous dA.")
                        elif self._blocks[active_block]['flight']['alt'] == 'freeze':
                            self._logger.debug("\t\tFreezing Altitude.")
                    except KeyError:
                        self._logger.debug("Cannot determine action for block {} altitude. Needs correction!".format(active_block))
                        raise
                try:
                    dv = (float(self._blocks[active_block]['flight']['final_velocity']) - vel) / self._blocks[active_block]['run_time']
                except (KeyError, TypeError):
                    try:
                        if self._blocks[active_block]['flight']['vel'] == 'glide':
                            self._logger.debug("\t\tVelocity is gliding. Keeping previous dV.")
                        elif self._blocks[active_block]['flight']['vel'] == 'freeze':
                            self._logger.debug("\t\tFreezing Velocity.")
                    except KeyError:
                        self._logger.debug("Cannot determine action for block {} altitude. Needs correction!".format(active_block))
                        raise
                self._logger.debug("\t\tNew dA: {}\n\t\tNew dV: {}".format(da, dv))

            # Update state based on instructions in this block.
            try:
                met_state = self._blocks[active_block]['flight']['met_state']
            except KeyError:
                pass
            self._logger.debug("\t\tMET Clock State: {}".format(met_state))
            # If an absolute time is defined for MET, use that.
            if 'met' in self._blocks[active_block]['flight']:
                met = self._blocks[active_block]['flight']['met']
                self._logger.debug("Set absolute MET: {}".format(met))
            elif met_state != 'hold':
                # If clock is set to run, advance that.
                met += 1
            self._logger.debug("\t\tMET Clock Time: {}".format(met))

            # Calculate a new altitude.
            # If there's an absolute value for altitude, set it.
            if 'alt' in self._blocks[active_block]['flight']:
                # Don't put string values in.
                if not isinstance(self._blocks[active_block]['flight']['alt'], str):
                    alt = self._blocks[active_block]['flight']['alt']
                    self._logger.debug("\t\tSetting absolute altitude.")
                else:
                    alt = alt + da
            else:
                # Otherwise, increment based on the target velocity.
                alt = round(alt + da,3)
            self._logger.debug("\t\tAltitude: {}".format(alt))

            # Calculate velocity
            # If there's an absolute value for velocity, set it.
            if 'vel' in self._blocks[active_block]['flight']:
                if not isinstance(self._blocks[active_block]['flight']['vel'], str):
                    vel = self._blocks[active_block]['flight']['vel']
                    self._logger.debug("\t\tSetting absolute velocity")
                else:
                    vel = vel + dv
            else:
                # Otherwise, increment based on the target velocity.
                vel = vel + dv
            self._logger.debug("\t\tVelocity: {}".format(vel))

            # Assemble it all into a nice dict.
            flight_data = {
                'met': met,
                'alt': alt,
                'vel': vel
            }

            self._flight_plan[run_time] = flight_data

            run_time += 1

    def _map_displays(self, script, displays):
        if 'display_map' not in script:
            raise ValueError("Script does not have display map.")
        self._logger.debug(pformat(script['display_map']))
        for val in ('met','alt','vel'):
            if val not in script['display_map']:
                raise ValueError("Display map does not map '{}'!".format(val))
        for md in script['display_map']:
            self._display_map[md] = displays[script['display_map'][md]]
