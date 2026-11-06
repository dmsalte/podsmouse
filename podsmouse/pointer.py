"""Adapter that lets the upstream mousepods Controller drive any Sink.

Upstream's Controller talks to a duck-typed pointer object (upstream ``Pointer``,
which writes to /dev/uinput). ``SinkPointer`` offers the same methods on top of a
``Sink``, so the upstream motion pipeline can feed a USB HID gadget instead.
See docs/upstream.md for the mapping.
"""

import logging
import time

from .sinks.base import Sink

log = logging.getLogger("podsmouse")

BUTTONS = {"left": 1, "right": 2, "middle": 3}
CLICK_HOLD_S = 0.015  # same press duration as upstream Pointer.click


class SinkPointer:
    """Upstream ``Pointer`` interface (move_rel, move_abs, click, scroll, close) over a Sink."""

    def __init__(self, sink: Sink, *, sleep=time.sleep) -> None:
        self.sink = sink
        self._sleep = sleep
        self._fx = 0.0
        self._fy = 0.0
        self._wheel = 0.0
        self._warned_abs = False

    def move_rel(self, dx: float, dy: float) -> None:
        # Keep the fractional remainder between calls, like upstream Pointer, so slow
        # head movement still adds up to whole pixels instead of being rounded away.
        self._fx += dx
        self._fy += dy
        ix, iy = int(self._fx), int(self._fy)
        self._fx -= ix
        self._fy -= iy
        if ix or iy:
            self.sink.move(ix, iy)

    def move_abs(self, fx: float, fy: float) -> None:
        # A relative HID mouse cannot jump to an absolute position. Upstream calls
        # move_abs(0.5, 0.5) on recenter in mouse mode, which we can safely ignore.
        # Pointer mode ("pointeur") relies on it and is out of scope for v1.
        if not self._warned_abs and (fx, fy) != (0.5, 0.5):
            self._warned_abs = True
            log.warning("Absolute positioning is not supported over USB HID; "
                        "use mode 'souris' (mouse) in the config")

    def click(self, button: str = "left") -> None:
        btn = BUTTONS[button]
        self.sink.button(btn, True)
        self._sleep(CLICK_HOLD_S)
        self.sink.button(btn, False)

    def scroll(self, lines: float) -> None:
        self._wheel += lines
        n = int(self._wheel)
        if n:
            self._wheel -= n
            self.sink.scroll(n)

    def close(self) -> None:
        self.sink.close()
