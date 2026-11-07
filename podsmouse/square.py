"""Draw a square with the mouse: the phase 2 acceptance test for the USB HID gadget.

Moves the pointer right, down, left and up in smooth steps at a fixed report rate,
so it ends where it started. Needs no AirPods and no Bluetooth.

Usage on the Pi, with the gadget bound (sudo gadget/setup-hid-gadget.sh):

    python -m podsmouse.square                  # one 400-count square on /dev/hidg0
    python -m podsmouse.square --repeat 3 --click --scroll 3
    python -m podsmouse.square --sink null      # dry run: print the reports' totals

The size on screen depends on Windows pointer settings: with "Enhance pointer precision"
on, slow moves come out smaller than fast ones, but the path should still close.
"""

import argparse
import sys
import time

from .sinks import HidSink, NullSink, Sink

# Right, down, left, up. HID Y is positive down.
DIRECTIONS = ((1, 0), (0, 1), (-1, 0), (0, -1))


def side_steps(length: int, steps: int) -> list[int]:
    """Split ``length`` into ``steps`` integer increments that differ by at most one and sum exactly."""
    if steps < 1:
        raise ValueError("steps must be at least 1")
    positions = [round(length * k / steps) for k in range(steps + 1)]
    return [b - a for a, b in zip(positions, positions[1:])]


def square_moves(side: int, steps_per_side: int) -> list[tuple[int, int]]:
    """All (dx, dy) moves of one square, starting with the top edge going right."""
    increments = side_steps(side, steps_per_side)
    return [(sx * d, sy * d) for sx, sy in DIRECTIONS for d in increments]


def draw_square(sink: Sink, side: int = 400, seconds_per_side: float = 1.0, rate: float = 120.0,
                repeat: int = 1, click: bool = False, scroll: int = 0,
                clock=time.monotonic, sleep=time.sleep) -> None:
    """Draw ``repeat`` squares on ``sink``, paced at ``rate`` reports per second.

    With ``click``, a left click is sent after each square, back at the start point.
    With ``scroll``, the wheel scrolls ``scroll`` steps up and then the same back down
    after the last square, one step per report period.
    """
    if side < 1 or repeat < 1 or rate <= 0 or seconds_per_side <= 0:
        raise ValueError("side, repeat, rate and seconds_per_side must be positive")
    period = 1.0 / rate
    moves = square_moves(side, max(1, round(seconds_per_side * rate)))
    deadline = clock()

    def tick() -> None:
        # Pace against a running deadline so sleep overshoot does not add up over a side.
        nonlocal deadline
        deadline += period
        delay = deadline - clock()
        if delay > 0:
            sleep(delay)
        else:
            deadline = clock()

    for _ in range(repeat):
        for dx, dy in moves:
            sink.move(dx, dy)
            tick()
        if click:
            sink.button(1, True)
            tick()
            sink.button(1, False)
            tick()
    for n in [1] * abs(scroll) + [-1] * abs(scroll):
        sink.scroll(n if scroll > 0 else -n)
        tick()


class _CountingSink(NullSink):
    """Dry-run sink that keeps only totals, so long runs do not grow a call list."""

    def __init__(self) -> None:
        super().__init__()
        self.x = self.y = self.wheel = self.moves = self.clicks = 0

    def move(self, dx: int, dy: int) -> None:
        self.x += dx
        self.y += dy
        self.moves += 1

    def button(self, btn: int, down: bool) -> None:
        if btn not in (1, 2, 3):
            raise ValueError("button must be 1 (left), 2 (right), or 3 (middle)")
        self.clicks += bool(down)

    def scroll(self, n: int) -> None:
        self.wheel += n

    def close(self) -> None:
        pass


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="python -m podsmouse.square", description=__doc__.split("\n\n")[0])
    ap.add_argument("--sink", choices=("hid", "null"), default="hid",
                    help="hid = USB HID gadget (default); null = dry run, print totals")
    ap.add_argument("--hid-device", default="/dev/hidg0", help="HID gadget device (default: /dev/hidg0)")
    ap.add_argument("--side", type=int, default=400, help="side length in mouse counts (default: 400)")
    ap.add_argument("--seconds", type=float, default=1.0, help="time per side in seconds (default: 1.0)")
    ap.add_argument("--rate", type=float, default=120.0, help="reports per second (default: 120)")
    ap.add_argument("--repeat", type=int, default=1, help="number of squares (default: 1)")
    ap.add_argument("--click", action="store_true", help="left click after each square")
    ap.add_argument("--scroll", type=int, default=0, help="after the squares, scroll N steps up, then N down")
    ap.add_argument("--delay", type=float, default=3.0,
                    help="seconds to wait before starting, to place the pointer (default: 3)")
    args = ap.parse_args(argv)
    for name in ("side", "repeat"):
        if getattr(args, name) < 1:
            ap.error(f"--{name} must be at least 1")
    for name in ("seconds", "rate"):
        if getattr(args, name) <= 0:
            ap.error(f"--{name} must be positive")
    if args.delay < 0:
        ap.error("--delay must not be negative")
    return args


def main(argv=None, sleep=time.sleep) -> int:
    args = parse_args(argv)
    try:
        sink = HidSink(args.hid_device) if args.sink == "hid" else _CountingSink()
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    with sink:
        if args.delay:
            print(f"Starting in {args.delay:g} s; place the pointer in the middle of the screen.")
            sleep(args.delay)
        print(f"Drawing {args.repeat} square(s), side {args.side}, {args.seconds:g} s per side, "
              f"{args.rate:g} Hz.")
        draw_square(sink, args.side, args.seconds, args.rate, args.repeat, args.click, args.scroll,
                    sleep=sleep)
        if isinstance(sink, _CountingSink):
            print(f"Dry run: {sink.moves} moves, net X {sink.x}, net Y {sink.y}, "
                  f"{sink.clicks} click(s), net wheel {sink.wheel}.")
    print("Done. The pointer should be back where it started.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
