"""Output relative mouse reports through a Linux USB HID gadget."""

import errno
import os
import struct

from .base import Sink


class HidSink(Sink):
    """Write four-byte reports: [buttons, dx, dy, wheel], without a report ID.

    This is a boot-protocol-style relative mouse layout extended with a wheel:
    byte 0 has left/right/middle in bits 0/1/2 and five zero padding bits;
    bytes 1/2/3 are signed int8 relative X/Y/wheel, each limited to -127..127.
    Positive Y moves down; positive wheel scrolls up. The descriptor must match
    this layout. The gadget uses report protocol, since a strict boot mouse
    report has only three bytes and cannot carry the wheel.

    Larger movements and scrolls are split without losing their totals. Button
    state persists across every report. Closing releases any held buttons before
    closing the device, and repeated close calls are harmless.
    """

    def __init__(self, path: str | os.PathLike[str] = "/dev/hidg0") -> None:
        try:
            # Open write-only without O_CREAT: a missing gadget must not become
            # an ordinary file, even when the process can write to its directory.
            fd = os.open(path, os.O_WRONLY)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                errno.ENOENT,
                "HID device is missing; run gadget/setup-hid-gadget.sh first",
                os.fspath(path),
            ) from exc
        self._device = os.fdopen(fd, "wb", buffering=0)
        self._buttons = 0

    def _write_report(self, buttons: int, dx: int, dy: int, wheel: int) -> None:
        report = struct.pack("Bbbb", buttons, dx, dy, wheel)
        written = self._device.write(report)
        if written != len(report):
            # Never retry a fragment: the gadget expects one whole report per
            # write, and a partial retry could be interpreted as another report.
            raise OSError(f"short HID write: expected 4 bytes, wrote {written}")

    def _write_steps(self, dx: int, dy: int, wheel: int) -> None:
        while True:
            x = max(-127, min(127, dx))
            y = max(-127, min(127, dy))
            w = max(-127, min(127, wheel))
            self._write_report(self._buttons, x, y, w)
            dx, dy, wheel = dx - x, dy - y, wheel - w
            if dx == dy == wheel == 0:
                return

    def move(self, dx: int, dy: int) -> None:
        self._write_steps(dx, dy, 0)

    def button(self, btn: int, down: bool) -> None:
        if btn not in (1, 2, 3):
            raise ValueError("button must be 1 (left), 2 (right), or 3 (middle)")
        mask = 1 << (btn - 1)
        buttons = self._buttons | mask if down else self._buttons & ~mask
        self._write_report(buttons, 0, 0, 0)
        self._buttons = buttons

    def scroll(self, n: int) -> None:
        self._write_steps(0, 0, n)

    def close(self) -> None:
        if self._device.closed:
            return
        try:
            if self._buttons:
                self._write_report(0, 0, 0, 0)
                self._buttons = 0
        finally:
            self._device.close()
