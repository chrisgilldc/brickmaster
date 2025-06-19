"""
Brickmaster Text Effects Rotater
"""

from .baseeffect import BaseEffect
import time

class RotateText(BaseEffect):
    """
    Rotates among several text options.
    """
    def __init__(self, text, animate=0.2):
        """
        Set up a text rotater.

        :param text: List of text strings to rotate among.
        :type text: list
        :param width: Width of the viewport.
        :type width: int
        :param animate: Animation trigger time, in seconds. May be full or factional. Defaults to 0.2s (200ms)
        :type animate: int or float

        """

        super().__init__(text, animate)

        # Save additional values.

        # Initialize values.
        self._index = 0

    def _update(self, force=False):
        """
        Rotation Updater
        """

        self._showing = self._full_text[self._index]

        self._index += 1
        if self._index >= len(self._full_text):
            self._index = 0

        self._last_animate_time = time.monotonic()

    def __str__(self):
        """
        The currently showing string.
        """
        if isinstance(self._showing, dict):
            return self._showing['text']
        else:
            return self._showing
