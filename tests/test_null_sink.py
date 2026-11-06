"""Tests for the shared sink contract and recording sink."""

import unittest

from podsmouse.sinks import NullSink, Sink


class NullSinkTests(unittest.TestCase):
    def test_records_every_operation_in_order_without_clamping(self):
        sink = NullSink()
        self.assertIsInstance(sink, Sink)
        sink.move(300, -400)
        for btn in (1, 2, 3):
            sink.button(btn, True)
            sink.button(btn, False)
        sink.scroll(-200)
        sink.move(0, 0)
        sink.scroll(0)
        sink.close()
        sink.close()
        self.assertEqual(sink.calls, [
            ("move", 300, -400),
            ("button", 1, True), ("button", 1, False),
            ("button", 2, True), ("button", 2, False),
            ("button", 3, True), ("button", 3, False),
            ("scroll", -200), ("move", 0, 0), ("scroll", 0),
            ("close",), ("close",),
        ])

    def test_instances_have_independent_call_lists(self):
        first, second = NullSink(), NullSink()
        first.move(1, 2)
        self.assertEqual(second.calls, [])

    def test_context_manager_closes_and_returns_sink(self):
        sink = NullSink()
        with sink as entered:
            self.assertIs(entered, sink)
            entered.move(5, -2)
        self.assertEqual(sink.calls, [("move", 5, -2), ("close",)])

    def test_context_manager_closes_and_propagates_exception(self):
        sink = NullSink()
        with self.assertRaisesRegex(RuntimeError, "body failed"):
            with sink:
                raise RuntimeError("body failed")
        self.assertEqual(sink.calls, [("close",)])

    def test_invalid_buttons_are_rejected(self):
        sink = NullSink()
        for btn in (-1, 0, 4):
            with self.subTest(btn=btn), self.assertRaises(ValueError):
                sink.button(btn, True)
        self.assertEqual(sink.calls, [])

    def test_sink_is_abstract(self):
        with self.assertRaises(TypeError):
            Sink()

        class IncompleteSink(Sink):
            def move(self, dx, dy):
                pass

            def button(self, btn, down):
                pass

            def scroll(self, n):
                pass

        with self.assertRaises(TypeError):
            IncompleteSink()


if __name__ == "__main__":
    unittest.main()
