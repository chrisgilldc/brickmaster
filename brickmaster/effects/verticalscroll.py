"""
Brickmaster Text Effects Vertical Scroll
"""

from .baseeffect import BaseEffect
import time

class VerticalScroll(BaseEffect):
    """
    Scrolls a section of text left or right along the line.
    """
    def __init__(self, text, height, scroll_down=False, animate=0.2, padding=1):
        """
        Set up a horizontal scroller

        :param text: The text to animate.
        :type text: str
        :param height: Height of the viewport. Each iteration this many lines of the available lines (including padding) will be returned.
        :type height: int
        :param scroll_down: Scroll to the right. Default is to scroll to the left.
        :type scroll_down: bool
        :param animate: Animation trigger time, in seconds. May be full or factional. Defaults to 0.2s (200ms)
        :type animate: int or float
        :param padding: Insert this many blank lines between iterations. Defaults to 1.
        :type padding: int

        """

        super().__init__(text, animate)

        self._showing = [] # Make showing a list.

        # Save additional values.
        self._scroll_down = scroll_down
        self._padding = padding
        self._height = height

        # Initialize values.
        self._index = self._padding # Starting text index should start by eating through the padding.
        self.update()

    def _update(self, force=False):
        """
        Horizontal Scroll Updater
        """

        # Combine the full text with the padding.
        # if self._scroll_right:
        #     # Use negatives to reverse index from the right.
        #     self._showing = ((" " * self._padding) + self._full_text)[(self._width + self._index )* -1:self._index * -1]
        #     if len(self._showing) < self._width:
        #         self._showing = (self._full_text + self._showing)[self._width * -1:]
        # else:
        # Upward scrolling
        self._showing = self._full_text[self._index:self._height]

        if len(self._showing) < self._height:
            self._showing = (self._showing + self._full_text)[:self._height]

        self._index += 1
        if self._index >= (len(self._full_text) + self._padding):
            self._index = 0

        self._last_animate_time = time.monotonic()

    def showing(self):
        """
        Currently showing items.
        :returns: list
        """
        return self._showing

    def __str__(self):
        """
        Merge items with a \n to make combined lines.
        """
        return "\n".join(self._showing)