"""
Brickmaster GPIO Classes
"""

import board
from digitalio import DigitalInOut

class EnhancedDigitalInOut:
    """
    Enhanced DigitalInOut. Inspired by, if not actually a subclass of, Adafruit's DigitalInOut

    Adds three additional features:
    - Create pins on GPIO expanders and make them look like on-board pins.
    - Change between active-high and active-low options.
    - Separate on and off pins, as for controlling latching relays.
    """
    def __init__(self, pin=None, on_pin=None, off_pin=None, extio_obj=None, active_low=False):
        # Initialize variables
        self._pin = None # Single mode pin
        self._on_pin = None # Split mode on pin.
        self._off_pin = None # Split mode off pin.
        self._extio_obj = extio_obj # The external IO object, if defined.
        self._split_pins = False
        self._active_low = active_low # By default, we're active high.

        # Check the inputs
        if pin is None:
            # If pin isn't set, then both on_pin and off_pin have to be set.
            if on_pin is None and off_pin is None:
                raise ValueError("No pins defined to control! Must either set 'pin', or split pin with 'on_pin' and "
                                 "'off_pin'")
            if on_pin is None or off_pin is None:
                raise ValueError("When using split-pin, both 'on_pin' and 'off_pin' must be set!")
            else:
                self._split_pins = True

        # Now make the pins.
        if self._split_pins:
            self._setup_split(on_pin, off_pin)
            self._controlled_pins = [on_pin, off_pin]
        else:
            self._setup_single(pin)
            self._controlled_pins = [pin]

    # Properties to get and set the pin/pins.

    @property
    def value(self):
        """
        Get the value of the pin(s)

        return bool
        """
        if self._split_pins:
            # Split pin logic.
            if self._active_low:
                if not self._on_pin.value and self._off_pin.value:
                    return True
                elif self._on_pin.value and not self._off_pin.value:
                    return False
                else:
                    raise ValueError("Split GPIO in disallowed state, On is '{}', Off is '{}'".
                                     format(self._on_pin.value, self._off_pin.value))
            else:
                if self._on_pin.value and not self._off_pin.value:
                    return True
                elif not self._on_pin.value and self._off_pin.value:
                    return False
                else:
                    raise ValueError("Split GPIO in disallowed state, On is '{}', Off is '{}'".
                                     format(self._on_pin.value, self._off_pin.value))
        else:
            # Single pin logic.
            if self._active_low:
                return not self._pin.value
            else:
                return self._pin.value

    @value.setter
    def value(self, target_value):
        """
        Set the value of the pin(s)

        :type target_value: bool
        """
        if self._split_pins:
            if self._active_low:
                if target_value:
                    # Active low turning on.
                    self._on_pin.value = False
                    self._off_pin.value = True
                else:
                    # Active low turning off.
                    self._on_pin.value = True
                    self._off_pin.value = False
            else:
                if target_value:
                    # Active high turning on:
                    self._on_pin.value = True
                    self._off_pin.value = False
                else:
                    # Active high turning off.
                    self._on_pin.value = False
                    self._off_pin.value = True
        else:
            if self._active_low:
                self._pin.value = not target_value
            else:
                self._pin.value = target_value

    # Utility properties.
    @property
    def controlled_pins(self):
        """
        Pins this object controls.

        return list
        """
        return self._controlled_pins

    # Pin setup methods.
    def _setup_single(self, pin):
        """
        Set up a single pin interface.
        """
        if self._extio_obj is None:
            # Onboard pin.
            try:
                the_pin = DigitalInOut(getattr(board, str(pin)))
            except AttributeError as ae:
                raise ae
        elif self._extio_obj is not None:
            the_pin = self._extio_obj.get_pin(pin)
        else:
            raise ValueError("Could not get pin.")
        # Common setup now that we have a pin.
        if self._active_low:
            the_pin.switch_to_output(value=True)
        else:
            the_pin.switch_to_output()
        # Assign the same pin to both on and off!
        self._pin = the_pin

    def _setup_split(self, on_pin, off_pin):
        """
        Set up a split pin interface.
        """
        if self._extio_obj is None:
            # On-Board pins.
            # Set up On
            try:
                self._on_pin = DigitalInOut(getattr(board, str(on_pin)))
            except AttributeError as ae:
                raise ae
            # Set up Off
            try:
                self._off_pin = DigitalInOut(getattr(board, str(off_pin)))
            except AttributeError as ae:
                raise ae
        elif self._extio_obj is not None:
            self._on_pin = self._extio_obj.get_pin(on_pin)
            self._off_pin = self._extio_obj.get_pin(off_pin)
        else:
            raise ValueError("Could not get pins.")
        # Common setup now that we have a pin.
        if self._active_low:
            self._on_pin.switch_to_output()
            self._off_pin.switch_to_output(value=True)
        else:
            self._on_pin.switch_to_output(value=True)
            self._off_pin.switch_to_output()
