"""Decode reports from temporary regular files; no HID hardware is used."""

import errno
import io
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from podsmouse.sinks import HidSink, Sink


class HidSinkTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "hidg0"
        self.path.touch()
        self.sink = HidSink(self.path)
        self.addCleanup(self.sink.close)

    def reports(self):
        data = self.path.read_bytes()
        self.assertEqual(len(data) % 4, 0)
        return list(struct.iter_unpack("Bbbb", data))

    def test_opens_binary_unbuffered_write_only_device(self):
        self.assertIsInstance(self.sink, Sink)
        self.assertIsInstance(self.sink._device, io.FileIO)
        self.assertTrue(self.sink._device.writable())
        self.assertFalse(self.sink._device.readable())
        self.assertEqual(self.reports(), [])

    def test_single_move_is_visible_without_flush_or_close(self):
        self.sink.move(12, 34)
        self.assertEqual(self.reports(), [(0, 12, 34, 0)])

    def test_negative_values_use_signed_int8_encoding(self):
        self.sink.move(-1, -127)
        self.assertEqual(self.path.read_bytes(), bytes([0, 255, 129, 0]))
        self.assertEqual(self.reports(), [(0, -1, -127, 0)])

    def test_boundaries_and_zero_have_one_report_each(self):
        for dx, dy in ((127, -127), (-127, 127), (0, 0)):
            self.sink.move(dx, dy)
        self.assertEqual(self.reports(), [
            (0, 127, -127, 0), (0, -127, 127, 0), (0, 0, 0, 0),
        ])

    def test_large_move_clamps_each_axis_and_preserves_remainder(self):
        self.sink.move(300, -130)
        self.assertEqual(self.reports(), [
            (0, 127, -127, 0), (0, 127, -3, 0), (0, 46, 0, 0),
        ])

    def test_large_negative_move_and_longer_y_axis(self):
        self.sink.move(-300, 400)
        self.assertEqual(self.reports(), [
            (0, -127, 127, 0), (0, -127, 127, 0),
            (0, -46, 127, 0), (0, 0, 19, 0),
        ])

    def test_move_totals_and_bounds_across_edge_cases(self):
        values = (-300, -254, -128, -127, -1, 0, 1, 127, 128, 254, 300)
        offset = 0
        for dx in values:
            for dy in values:
                with self.subTest(dx=dx, dy=dy):
                    self.sink.move(dx, dy)
                    reports = self.reports()[offset:]
                    offset += len(reports)
                    self.assertEqual(sum(r[1] for r in reports), dx)
                    self.assertEqual(sum(r[2] for r in reports), dy)
                    self.assertEqual(len(reports), max(
                        1, (abs(dx) + 126) // 127, (abs(dy) + 126) // 127,
                    ))
                    for buttons, x, y, wheel in reports:
                        self.assertEqual((buttons, wheel), (0, 0))
                        self.assertTrue(-127 <= x <= 127)
                        self.assertTrue(-127 <= y <= 127)

    def test_each_button_press_and_release(self):
        for btn in (1, 2, 3):
            self.sink.button(btn, True)
            self.sink.button(btn, False)
        self.assertEqual(self.reports(), [
            (1, 0, 0, 0), (0, 0, 0, 0),
            (2, 0, 0, 0), (0, 0, 0, 0),
            (4, 0, 0, 0), (0, 0, 0, 0),
        ])

    def test_buttons_are_combined_and_repeated_presses_do_not_toggle(self):
        for btn, down in ((1, True), (2, True), (3, True),
                          (2, True), (2, False), (2, False)):
            self.sink.button(btn, down)
        self.assertEqual([r[0] for r in self.reports()], [1, 3, 7, 7, 5, 5])

    def test_split_moves_and_scroll_keep_held_buttons(self):
        self.sink.button(1, True)
        self.sink.button(3, True)
        self.sink.move(300, -1)
        self.sink.scroll(-128)
        self.sink.button(1, False)
        self.sink.move(1, 2)
        self.assertEqual(self.reports(), [
            (1, 0, 0, 0), (5, 0, 0, 0),
            (5, 127, -1, 0), (5, 127, 0, 0), (5, 46, 0, 0),
            (5, 0, 0, -127), (5, 0, 0, -1),
            (4, 0, 0, 0), (4, 1, 2, 0),
        ])

    def test_scroll_in_both_directions_and_zero(self):
        for n in (3, -2, 0):
            self.sink.scroll(n)
        self.assertEqual(self.reports(), [
            (0, 0, 0, 3), (0, 0, 0, -2), (0, 0, 0, 0),
        ])

    def test_large_scrolls_preserve_the_full_total(self):
        self.sink.scroll(300)
        self.sink.scroll(-300)
        self.assertEqual([r[3] for r in self.reports()],
                         [127, 127, 46, -127, -127, -46])

    def test_invalid_buttons_do_not_write_or_change_held_state(self):
        self.sink.button(2, True)
        for btn in (-1, 0, 4):
            with self.subTest(btn=btn), self.assertRaises(ValueError):
                self.sink.button(btn, True)
        self.sink.move(1, 0)
        self.assertEqual(self.reports(), [(2, 0, 0, 0), (2, 1, 0, 0)])

    def test_each_report_is_one_four_byte_write(self):
        with patch.object(self.sink._device, "write",
                          wraps=self.sink._device.write) as write:
            self.sink.move(300, -1)
            self.sink.button(1, True)
            self.sink.scroll(1)
        self.assertEqual(len(write.call_args_list), 5)
        self.assertEqual([len(c.args[0]) for c in write.call_args_list], [4] * 5)
        self.assertEqual(b"".join(c.args[0] for c in write.call_args_list),
                         self.path.read_bytes())

    def test_missing_device_error_names_setup_script_and_does_not_create_file(self):
        missing = self.path.parent / "missing-hidg0"
        with self.assertRaisesRegex(FileNotFoundError,
                                    "gadget/setup-hid-gadget.sh") as caught:
            HidSink(missing)
        self.assertEqual(caught.exception.errno, errno.ENOENT)
        self.assertEqual(caught.exception.filename, str(missing))
        self.assertFalse(missing.exists())

    def test_default_device_path(self):
        with patch("podsmouse.sinks.hid_gadget.os.open",
                   side_effect=FileNotFoundError) as device_open:
            with self.assertRaisesRegex(FileNotFoundError,
                                        "gadget/setup-hid-gadget.sh"):
                HidSink()
        self.assertEqual(device_open.call_args.args[0], "/dev/hidg0")

    def test_permission_error_is_not_reported_as_missing_device(self):
        with patch("podsmouse.sinks.hid_gadget.os.open",
                   side_effect=PermissionError("access denied")):
            with self.assertRaisesRegex(PermissionError, "access denied"):
                HidSink(self.path)

    def test_short_write_fails_without_retrying_a_fragment(self):
        with patch.object(self.sink._device, "write", return_value=3) as write:
            with self.assertRaisesRegex(OSError, "short HID write"):
                self.sink.move(1, 2)
        write.assert_called_once_with(bytes([0, 1, 2, 0]))

    def test_close_releases_buttons_and_is_idempotent(self):
        self.sink.button(2, True)
        self.sink.close()
        self.sink.close()
        self.assertTrue(self.sink._device.closed)
        self.assertEqual(self.reports(), [(2, 0, 0, 0), (0, 0, 0, 0)])
        with self.assertRaises(ValueError):
            self.sink.move(1, 2)

    def test_context_manager_returns_sink_and_closes_on_success(self):
        with self.sink as entered:
            self.assertIs(entered, self.sink)
            entered.move(1, 2)
        self.assertTrue(self.sink._device.closed)
        self.assertEqual(self.reports(), [(0, 1, 2, 0)])

    def test_context_manager_releases_buttons_and_propagates_exception(self):
        with self.assertRaisesRegex(RuntimeError, "body failed"):
            with self.sink:
                self.sink.button(1, True)
                raise RuntimeError("body failed")
        self.assertTrue(self.sink._device.closed)
        self.assertEqual(self.reports(), [(1, 0, 0, 0), (0, 0, 0, 0)])

    def test_close_still_closes_device_if_release_fails(self):
        self.sink.button(1, True)
        with patch.object(self.sink._device, "write",
                          side_effect=OSError("device disconnected")):
            with self.assertRaisesRegex(OSError, "device disconnected"):
                self.sink.close()
        self.assertTrue(self.sink._device.closed)


if __name__ == "__main__":
    unittest.main()
