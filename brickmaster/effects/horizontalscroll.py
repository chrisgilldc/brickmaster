"""
Brickmaster Text Effects Horizontal Scroll
"""

from .baseeffect import BaseEffect
import time

class HorizontalScroll(BaseEffect):
    """
    Scrolls a section of text left or right along the line.
    """
    def __init__(self, text, width, scroll_right=False, animate=0.2, padding=5):
        """
        Set up a horizontal scroller

        :param text: The text to animate.
        :type text: str
        :param width: Width of the viewport.
        :type width: int
        :param scroll_right: Scroll to the right. Default is to scroll to the left.
        :type scroll_right: bool
        :param animate: Animation trigger time, in seconds. May be full or factional. Defaults to 0.2s (200ms)
        :type animate: int or float
        :param padding: Padding between iterations when scrolling. Defaults to 5.
        :type padding: int

        """

        super().__init__(text, animate)

        # Save additional values.
        self._scroll_right = scroll_right
        self._padding = padding
        self._width = width

        # Initialize values.
        self._index = 0 # Starting text index should start by eating through the padding.
        self._trailing_text = 0 # Trailing text from a previous iteration
        self.update()

    def _update(self, force=False):
        """
        Horizontal Scroll Updater
        """

        # Combine the full text with the padding.
        if self._scroll_right:
            # Use negatives to reverse index from the right.
            self._showing = ((" " * self._padding) + self._full_text)[(self._width + self._index )* -1:self._index * -1]
            if len(self._showing) < self._width:
                self._showing = (self._full_text + self._showing)[self._width * -1:]
        else:
            # Left Scroll
            self._showing = (self._full_text + (" " * self._padding))[self._index:self._width + self._index]
            if len(self._showing) < self._width:
                self._showing = (self._showing + self._full_text)[:self._width]

        self._index += 1
        if self._index >= (len(self._full_text) + self._padding):
            self._index = 0

        self._last_animate_time = time.monotonic()