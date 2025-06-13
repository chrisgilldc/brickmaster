"""
Brickmaster Text Effects Base
"""

import time

class BaseEffect:
    """
    Base class for Brickmaster Text Effects
    """
    def __init__(self, text, animate=0.2):
        """
        Base initializer.

        :param text: The text to animate.
        :type text: str or list
        :param animate: Animation trigger time, in seconds. May be full or factional.
        :type animate: int or float

        """
        self._full_text = text
        self._animate_time = animate
        self._last_animate_time = 0
        # What is actively showing.
        self._showing = ""

    def update(self, force=False):
        """
        Update the animation.

        :param force: Force the update, even if the timer hasn't gone off yet.
        :type force: bool
        """

        if force or time.monotonic() - self._last_animate_time > self._animate_time:
            self._update()

    def _update(self):
        """
        Class-specific updater.
        """
        raise NotImplemented("Update must be defined by a specific implementation")

    @property
    def full_text(self):
        """
        Complete text that was submitted on creation.
        """
        return self._full_text

    def __str__(self):
        """
        The currently showing string.
        """
        return self._showing