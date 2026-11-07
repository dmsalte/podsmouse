"""PodsMouse entry point: AirPods head tracking -> USB HID mouse.

Runs the upstream mousepods pipeline (AAPClient -> MotionEngine -> Controller) and
sends its output to a Sink instead of /dev/uinput.

    python -m podsmouse.main --sink hid --config /var/lib/podsmouse/config.json
    python -m podsmouse.main --sink null          # dry run: no mouse output, logs totals
    python -m podsmouse.main --diag               # live sensor rates, no mouse output

Upstream's run loop is reused as is (reconnects, stem gestures, web UI, config reload).
It builds its pointer with ``Pointer()``, so we point that name at our SinkPointer before
calling it. Nothing under upstream/ is modified.
"""

import argparse
import contextlib
import logging
import os
import pathlib
import sys
import time

from . import english, web_english
from .pointer import SinkPointer
from .sinks import HidSink, Sink

UPSTREAM_DIR = pathlib.Path(__file__).resolve().parent.parent / "upstream"
DEFAULT_CONFIG = pathlib.Path(os.environ.get("XDG_CONFIG_HOME", pathlib.Path.home() / ".config")) / "podsmouse" / "config.json"
DEFAULT_HID_DEVICE = "/dev/hidg0"
DEFAULT_WEB_PORT = 8737

log = logging.getLogger("podsmouse")


def load_upstream():
    """Import the vendored upstream controller module (and make mousepods_web importable)."""
    path = str(UPSTREAM_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)
    import airpods_mouse_controller  # noqa: PLC0415  (import after sys.path setup)

    return airpods_mouse_controller


def load_web():
    """Import the vendored upstream web UI module (call load_upstream first)."""
    import mousepods_web  # noqa: PLC0415

    return mousepods_web


class DryRunSink(Sink):
    """Accumulates output and logs a summary once per interval. Bounded memory, for long dry runs."""

    def __init__(self, interval_s: float = 1.0, clock=time.monotonic) -> None:
        self.interval_s = interval_s
        self._clock = clock
        self._next = clock() + interval_s
        self.dx = self.dy = self.wheel = self.clicks = 0

    def _maybe_log(self) -> None:
        now = self._clock()
        if now >= self._next:
            self._next = now + self.interval_s
            if self.dx or self.dy or self.wheel or self.clicks:
                log.info("dry run: dx=%+d dy=%+d wheel=%+d clicks=%d", self.dx, self.dy, self.wheel, self.clicks)
                self.dx = self.dy = self.wheel = self.clicks = 0

    def move(self, dx: int, dy: int) -> None:
        self.dx += dx
        self.dy += dy
        self._maybe_log()

    def button(self, btn: int, down: bool) -> None:
        if btn not in (1, 2, 3):
            raise ValueError("button must be 1 (left), 2 (right), or 3 (middle)")
        if down:
            self.clicks += 1
        self._maybe_log()

    def scroll(self, n: int) -> None:
        self.wheel += n
        self._maybe_log()

    def close(self) -> None:
        pass


def calibrate(up, cfg, config_path: pathlib.Path, english_ui: bool = True) -> int:
    """Run upstream's calibration window; the profile is saved into config_path."""
    try:
        import tkinter  # noqa: PLC0415
    except ImportError:
        log.error("--calibrate needs tkinter and a desktop session: sudo apt install python3-tk")
        return 1
    # Upstream's calibrate() reads the config file back before saving the profile, and fails
    # if it does not exist yet.
    if not config_path.exists():
        config_path.write_text("{}\n")
    ui = english.english_tk(tkinter) if english_ui else contextlib.nullcontext()
    with ui:
        up.calibrate(cfg, str(config_path))
    return 0


def build_sink(kind: str, hid_device: str) -> Sink:
    if kind == "hid":
        return HidSink(hid_device)
    if kind == "null":
        return DryRunSink()
    raise ValueError(f"unknown sink: {kind}")


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="python -m podsmouse.main", description="AirPods head tracking as a USB HID mouse.")
    ap.add_argument("--sink", choices=("hid", "null", "uinput"), default="hid",
                    help="mouse output: hid = USB gadget (default), null = dry run that only logs, "
                         "uinput = move this Linux machine's own pointer (needs python3-evdev; for desktop testing)")
    ap.add_argument("--calibrate", action="store_true",
                    help="open the calibration window (needs a desktop and python3-tk), save the profile and exit")
    ap.add_argument("--lang", choices=("en", "fr"), default="en",
                    help="language of upstream messages, the calibration window and the web UI (default en)")
    ap.add_argument("--hid-device", default=DEFAULT_HID_DEVICE, help=f"HID gadget device (default {DEFAULT_HID_DEVICE})")
    ap.add_argument("-c", "--config", default=str(DEFAULT_CONFIG),
                    help=f"writable config and calibration file (default {DEFAULT_CONFIG})")
    ap.add_argument("--diag", action="store_true", help="show live sensor rates; no mouse output, no sink opened")
    ap.add_argument("--web-port", type=int, default=DEFAULT_WEB_PORT,
                    help=f"local web UI port on 127.0.0.1 (default {DEFAULT_WEB_PORT})")
    ap.add_argument("--no-web", action="store_true", help="do not start the web UI")
    ap.add_argument("-v", "--verbose", action="store_true")
    return ap.parse_args(argv)


def main(argv=None, upstream=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S")
    up = upstream or load_upstream()
    if args.lang == "en":
        english.install(up)

    config_path = pathlib.Path(args.config)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    cfg = up.load_config(str(config_path))

    if args.calibrate:
        return calibrate(up, cfg, config_path, english_ui=args.lang == "en")
    if cfg.get("mode") == "pointeur" and not args.diag:
        log.warning("Config mode 'pointeur' needs absolute positioning, which USB HID relative mouse "
                    "cannot do. Set \"mode\": \"souris\" in %s.", config_path)

    web_port = None if args.no_web else args.web_port
    if args.lang == "en" and web_port is not None and upstream is None:
        # A fake upstream (tests) has no web module to translate.
        web_english.install(load_web(), config_path.parent)

    if args.diag:
        # Upstream uses its own NullPointer in diag mode; do not open the HID device.
        up.run(cfg, str(config_path), diag=True, web_port=web_port)
        return 0

    if args.sink == "uinput":
        # Upstream's own Pointer writes to /dev/uinput, as in plain mousepods. For testing on a
        # Linux desktop before the USB gadget hardware is available.
        try:
            import evdev  # noqa: F401, PLC0415
        except ImportError:
            log.error("--sink uinput needs python-evdev: sudo apt install python3-evdev")
            return 1
        log.info("Output: this machine's pointer via /dev/uinput")
        up.run(cfg, str(config_path), diag=False, web_port=web_port)
        return 0

    try:
        sink = build_sink(args.sink, args.hid_device)
    except FileNotFoundError as exc:
        log.error("%s", exc)
        return 1

    # Upstream run() constructs its output with Pointer(); hand it our adapter instead.
    up.Pointer = lambda: SinkPointer(sink)
    log.info("Output: %s", "USB HID gadget " + args.hid_device if args.sink == "hid" else "dry run (no mouse output)")
    try:
        up.run(cfg, str(config_path), diag=False, web_port=web_port)
    finally:
        # run() closes the pointer (and so the sink) on a normal exit; this covers errors
        # raised before it built the pointer. Closing a sink twice is harmless.
        sink.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
