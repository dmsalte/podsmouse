"""SinkPointer: the upstream Pointer interface over a Sink."""

import logging
import unittest

from podsmouse.pointer import SinkPointer
from podsmouse.sinks import NullSink


class SinkPointerTest(unittest.TestCase):
    def setUp(self):
        self.sink = NullSink()
        self.sleeps = []
        self.ptr = SinkPointer(self.sink, sleep=self.sleeps.append)

    def test_whole_pixels_pass_through(self):
        self.ptr.move_rel(5, -3)
        self.assertEqual(self.sink.calls, [("move", 5, -3)])

    def test_fractions_accumulate_instead_of_being_lost(self):
        for _ in range(12):  # 0.25 is exact in binary floating point
            self.ptr.move_rel(0.25, -0.25)
        total_x = sum(c[1] for c in self.sink.calls if c[0] == "move")
        total_y = sum(c[2] for c in self.sink.calls if c[0] == "move")
        self.assertEqual((total_x, total_y), (3, -3))

    def test_sub_pixel_move_sends_nothing(self):
        self.ptr.move_rel(0.4, 0.2)
        self.assertEqual(self.sink.calls, [])

    def test_large_move_is_passed_whole_to_sink(self):
        # Splitting into int8 reports is the sink's job (HidSink), not the adapter's.
        self.ptr.move_rel(300.7, 0)
        self.assertEqual(self.sink.calls, [("move", 300, 0)])

    def test_click_presses_waits_and_releases(self):
        self.ptr.click("right")
        self.assertEqual(self.sink.calls, [("button", 2, True), ("button", 2, False)])
        self.assertEqual(self.sleeps, [0.015])

    def test_click_names_map_to_button_numbers(self):
        for name, btn in (("left", 1), ("right", 2), ("middle", 3)):
            self.sink.calls.clear()
            self.ptr.click(name)
            self.assertEqual(self.sink.calls[0], ("button", btn, True))

    def test_default_click_is_left(self):
        self.ptr.click()
        self.assertEqual(self.sink.calls[0], ("button", 1, True))

    def test_scroll_accumulates_fractional_lines(self):
        for _ in range(4):
            self.ptr.scroll(0.5)
        self.assertEqual(self.sink.calls, [("scroll", 1), ("scroll", 1)])

    def test_negative_scroll(self):
        self.ptr.scroll(-2.5)
        self.assertEqual(self.sink.calls, [("scroll", -2)])

    def test_recenter_move_abs_is_silent_noop(self):
        with self.assertNoLogs("podsmouse", level=logging.WARNING):
            self.ptr.move_abs(0.5, 0.5)
        self.assertEqual(self.sink.calls, [])

    def test_other_move_abs_warns_once(self):
        with self.assertLogs("podsmouse", level=logging.WARNING) as logs:
            self.ptr.move_abs(0.1, 0.9)
            self.ptr.move_abs(0.2, 0.8)
        self.assertEqual(len(logs.records), 1)
        self.assertEqual(self.sink.calls, [])

    def test_close_closes_sink(self):
        self.ptr.close()
        self.assertEqual(self.sink.calls, [("close",)])


if __name__ == "__main__":
    unittest.main()
