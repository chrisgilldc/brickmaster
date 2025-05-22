"""
Brickmaster Sensor - HTU31D Temperature and Humidity
"""

import adafruit_logging
from .BaseSensor import BaseSensor
import time


class SensorHTU31D(BaseSensor):
    """
    Sensor for an HTU31D temperature/humidity sensor.
    """
    def __init__(self, ctrl_id, name, i2c_bus, address, core, unit="C", publish_time=60,
                 icon="mdi:toy-brick", log_level=adafruit_logging.WARNING):
        """
        Args:
            ctrl_id (str): ID of the sensor. Cannot have spaces.
            name (str): Name of the sensor. Can be friendly.
            i2c_bus (busio.I2C): I2C bus object
            address (int): Address of the HTU31D sensor.
            core (Brickmaster): Reference to the Brickmaster core.
            unit (str): Temperature units to report. "F" or "C". Defaults to "C".
            publish_time (int): How often data should be published, in seconds.
            icon (str): Icon to use for discovery.
            log_level (str): Log level to use. Defaults to Warning.

        Returns:
            None
        """
        super().__init__(ctrl_id, name, core, icon, publish_time, log_level)

        try:
            import adafruit_htu31d
        except ImportError as ie:
            raise ie

        self._i2c_bus = i2c_bus
        self._address = address
        if unit not in ("F", "C"):
            raise ValueError("Unit must be 'C' for Celsis or 'F' for Farenheight")
        self._unit = unit
        self._latest_update = 0
        self._latest_data = None
        self._publish_time = publish_time
        self._sensor = adafruit_htu31d.HTU31D(self._i2c_bus, self._address)

    @property
    def status(self):
        """
        Get status from the sensor and package it.

        Args:
            None

        Returns:
            dict
        """

        # Update every 6 seconds - 10 times a minute.
        if time.monotonic() - self._latest_update > self._publish_time:
            temp, humidity = self._sensor.measurements
            # Convert temp if needed
            if self._unit == "F":
                temp = (temp - 32) * 5/9
            self._latest_data = {"temperature": f"{temp:.2f}", "humidity": f"{humidity:.2f}"}
            self._latest_update = time.monotonic()
        return self._latest_data

    def callback(self, client, topic, message):
        """
        Sensor callback. Does nothing.
        """
        pass

    @property
    def uom(self):
        """
        Unit of Measurement for Home Assistant. This only applies to temperature.
        """
        if self._unit == 'F':
            return "°F"
        else:
            return "°C"