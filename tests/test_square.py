"""Tests for the square-drawing gadget test (T07). Simulation only: no gadget, no Windows."""

import contextlib
import io
import os
import struct
import tempfile
import unittest

from podsmouse import square
from podsmouse.sinks import HidSink, NullSink


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def clock(self):
        return self.now

    def sleep(self, s):
        self.sleeps.append(s)
        self.now += s


class SideStepsTests(unittest.TestCase):
    def test_increments_sum_exactly_and_are_even(self):
        for length, steps in ((400, 120), (7, 3), (1, 120), (1000, 1), (123, 17)):
            inc = square.side_steps(length, steps)
            self.assertEqual(len(inc), steps)
            self.assertEqual(sum(inc), length)
            self.assertLessEqual(max(inc) - min(inc), 1)

    def test_rejects_zero_steps(self):
        with self.assertRaises(ValueError):
            square.side_steps(10, 0)


class SquareMovesTests(unittest.TestCase):
    def test_sides_go_right_down_left_up_and_close(self):
        moves = square.square_moves(400, 120)
        self.assertEqual(len(moves), 480)
        sides = [moves[i * 120:(i + 1) * 120] for i in range(4)]
        totals = [(sum(m[0] for m in s), sum(m[1] for m in s)) for s in sides]
        self.assertEqual(totals, [(400, 0), (0, 400), (-400, 0), (0, -400)])
        self.assertEqual((sum(m[0] for m in moves), sum(m[1] for m in moves)), (0, 0))


class DrawSquareTests(unittest.TestCase):
    def run_square(self, **kw):
        sink, fc = NullSink(), FakeClock()
        square.draw_square(sink, clock=fc.clock, sleep=fc.sleep, **kw)
        return sink, fc

    def test_paces_at_rate_and_returns_to_start(self):
        sink, fc = self.run_square(side=400, seconds_per_side=1.0, rate=120.0)
        moves = [c for c in sink.calls if c[0] == "move"]
        self.assertEqual(len(moves), 480)
        self.assertEqual((sum(c[1] for c in moves), sum(c[2] for c in moves)), (0, 0))
        self.assertAlmostEqual(fc.now, 4.0, places=6)
        self.assertNotIn(("close",), sink.calls)  # the caller owns the sink

    def test_late_ticks_do_not_sleep_or_bunch_up(self):
        sink, fc = NullSink(), FakeClock()

        def slow_clock():
            fc.now += 0.02  # every clock read costs more than a 120 Hz period
            return fc.now

        square.draw_square(sink, side=10, seconds_per_side=0.1, rate=120.0, clock=slow_clock, sleep=fc.sleep)
        self.assertEqual(fc.sleeps, [])

    def test_click_after_each_square_and_scroll_returns(self):
        sink, _ = self.run_square(side=20, seconds_per_side=0.1, rate=100.0, repeat=2, click=True, scroll=3)
        buttons = [c for c in sink.calls if c[0] == "button"]
        self.assertEqual(buttons, [("button", 1, True), ("button", 1, False)] * 2)
        scrolls = [c[1] for c in sink.calls if c[0] == "scroll"]
        self.assertEqual(scrolls, [1, 1, 1, -1, -1, -1])
        # The first click comes right after the first square's last move.
        first_button = sink.calls.index(("button", 1, True))
        self.assertEqual(first_button, 40)

    def test_negative_scroll_goes_down_first(self):
        sink, _ = self.run_square(side=4, seconds_per_side=0.1, rate=40.0, scroll=-2)
        self.assertEqual([c[1] for c in sink.calls if c[0] == "scroll"], [-1, -1, 1, 1])

    def test_rejects_bad_parameters(self):
        for kw in ({"side": 0}, {"repeat": 0}, {"rate": 0}, {"seconds_per_side": 0}):
            with self.assertRaises(ValueError):
                square.draw_square(NullSink(), **kw)

    def test_hid_reports_are_valid_and_close(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "hidg0")
            open(path, "wb").close()
            fc = FakeClock()
            with HidSink(path) as sink:
                square.draw_square(sink, side=600, seconds_per_side=0.025, rate=120.0, click=True,
                                   clock=fc.clock, sleep=fc.sleep)
            with open(path, "rb") as f:
                data = f.read()
        self.assertEqual(len(data) % 4, 0)
        reports = [struct.unpack("Bbbb", data[i:i + 4]) for i in range(0, len(data), 4)]
        self.assertTrue(all(-127 <= v <= 127 for r in reports for v in r[1:]))
        self.assertEqual((sum(r[1] for r in reports), sum(r[2] for r in reports)), (0, 0))
        self.assertEqual([r[0] for r in reports[-2:]], [1, 0])


class MainTests(unittest.TestCase):
    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        sleeps = []
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = square.main(argv, sleep=sleeps.append)
        return code, out.getvalue(), err.getvalue(), sleeps

    def test_dry_run_prints_closed_path(self):
        code, out, _, sleeps = self.run_main(
            ["--sink", "null", "--side", "50", "--seconds", "0.05", "--rate", "200", "--click", "--scroll", "2"])
        self.assertEqual(code, 0)
        self.assertIn("net X 0, net Y 0, 1 click(s), net wheel 0", out)
        self.assertEqual(sleeps[0], 3.0)  # default start delay

    def test_missing_gadget_reports_setup_script(self):
        code, _, err, _ = self.run_main(["--hid-device", "/nonexistent/hidg0", "--delay", "0"])
        self.assertEqual(code, 1)
        self.assertIn("setup-hid-gadget.sh", err)

    def test_rejects_bad_arguments(self):
        for argv in (["--side", "0"], ["--rate", "0"], ["--seconds", "-1"], ["--delay", "-1"], ["--repeat", "0"]):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                square.parse_args(argv)


if __name__ == "__main__":
    unittest.main()
