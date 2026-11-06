"""podsmouse.main: CLI, wiring, and the full upstream pipeline driving our sinks in simulation."""

import json
import pathlib
import struct
import tempfile
import sys
import types
import unittest
from unittest import mock

from podsmouse import main as pm
from podsmouse.pointer import SinkPointer
from podsmouse.sinks import HidSink, NullSink

UPSTREAM = pm.load_upstream()
CAPTURE = pm.UPSTREAM_DIR / "captures" / "airpods3_motion_capture.json"


def fake_upstream():
    """A stand-in for the upstream module that records how main() calls it."""
    up = types.SimpleNamespace(calls=[], Pointer=None, notify=lambda cfg, text: None)
    up.load_config = lambda path: {"mode": "souris", "_path": path}

    def run(cfg, cfg_path, diag=False, web_port=8737):
        ptr = None if diag else up.Pointer()
        up.calls.append({"cfg": cfg, "cfg_path": cfg_path, "diag": diag, "web_port": web_port, "ptr": ptr})
        if ptr:
            ptr.close()

    up.run = run
    return up


def make_controller(ptr):
    cfg = UPSTREAM.load_config("/nonexistent.json")
    cfg["mode"] = "souris"
    cfg["notifications"] = False
    ctl = UPSTREAM.Controller(cfg, ptr)
    ctl.engine.set_profile({"yaw_sign": 1, "lat": [0, 1, 0], "pitch_sign": 1, "roll_sign": 1})
    return ctl


def feed_rates(ctl, w_dps, secs, step=0.01):
    t = 0.0
    for _ in range(int(secs / step)):
        t += step
        ctl.on_rates(w_dps[0], w_dps[1], w_dps[2], step, t)
        ctl._last_render = t - step
        ctl.last_sample = t
        ctl.render(t)


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = str(pathlib.Path(self.tmp.name) / "sub" / "config.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_defaults(self):
        args = pm.parse_args([])
        self.assertEqual((args.sink, args.hid_device, args.diag, args.web_port, args.no_web),
                         ("hid", "/dev/hidg0", False, 8737, False))

    def test_rejects_unknown_sink(self):
        with self.assertRaises(SystemExit):
            pm.parse_args(["--sink", "bogus"])

    def test_null_sink_runs_upstream_with_sink_pointer(self):
        up = fake_upstream()
        self.assertEqual(pm.main(["--sink", "null", "--config", self.cfg, "--no-web"], upstream=up), 0)
        (call,) = up.calls
        self.assertIsInstance(call["ptr"], SinkPointer)
        self.assertIsInstance(call["ptr"].sink, pm.DryRunSink)
        self.assertEqual((call["cfg_path"], call["diag"], call["web_port"]), (self.cfg, False, None))

    def test_creates_config_directory(self):
        pm.main(["--sink", "null", "--config", self.cfg, "--no-web"], upstream=fake_upstream())
        self.assertTrue(pathlib.Path(self.cfg).parent.is_dir())

    def test_diag_opens_no_sink(self):
        up = fake_upstream()
        # A missing HID device must not matter in diag mode.
        pm.main(["--diag", "--hid-device", "/nonexistent/hidg0", "--config", self.cfg], upstream=up)
        (call,) = up.calls
        self.assertTrue(call["diag"])
        self.assertIsNone(call["ptr"])
        self.assertEqual(call["web_port"], 8737)

    def test_hid_sink_writes_to_device(self):
        dev = pathlib.Path(self.tmp.name) / "hidg0"
        dev.touch()
        up = fake_upstream()
        pm.main(["--sink", "hid", "--hid-device", str(dev), "--config", self.cfg, "--web-port", "9000"], upstream=up)
        (call,) = up.calls
        self.assertIsInstance(call["ptr"].sink, HidSink)
        self.assertEqual(call["web_port"], 9000)

    def test_missing_hid_device_fails_cleanly(self):
        up = fake_upstream()
        with self.assertLogs("podsmouse", level="ERROR") as logs:
            rc = pm.main(["--sink", "hid", "--hid-device", "/nonexistent/hidg0", "--config", self.cfg], upstream=up)
        self.assertEqual(rc, 1)
        self.assertEqual(up.calls, [])
        self.assertIn("setup-hid-gadget.sh", logs.output[0])

    def test_warns_about_pointer_mode(self):
        up = fake_upstream()
        up.load_config = lambda path: {"mode": "pointeur"}
        with self.assertLogs("podsmouse", level="WARNING") as logs:
            pm.main(["--sink", "null", "--config", self.cfg, "--no-web"], upstream=up)
        self.assertTrue(any("souris" in line for line in logs.output))


class DesktopModesTest(unittest.TestCase):
    """--sink uinput and --calibrate, for testing on a Linux desktop."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = pathlib.Path(self.tmp.name) / "config.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_uinput_without_evdev_fails_cleanly(self):
        up = fake_upstream()
        with mock.patch.dict(sys.modules, {"evdev": None}), self.assertLogs("podsmouse", "ERROR") as logs:
            rc = pm.main(["--sink", "uinput", "--config", str(self.cfg), "--no-web"], upstream=up)
        self.assertEqual(rc, 1)
        self.assertEqual(up.calls, [])
        self.assertIn("python3-evdev", logs.output[0])

    def test_uinput_keeps_upstream_pointer(self):
        up = fake_upstream()
        sentinel = types.SimpleNamespace(close=lambda: None)
        up.Pointer = lambda: sentinel
        with mock.patch.dict(sys.modules, {"evdev": types.ModuleType("evdev")}):
            rc = pm.main(["--sink", "uinput", "--config", str(self.cfg), "--no-web"], upstream=up)
        self.assertEqual(rc, 0)
        self.assertIs(up.calls[0]["ptr"], sentinel)

    def test_calibrate_without_tkinter_fails_cleanly(self):
        up = fake_upstream()
        with mock.patch.dict(sys.modules, {"tkinter": None}), self.assertLogs("podsmouse", "ERROR"):
            rc = pm.main(["--calibrate", "--config", str(self.cfg)], upstream=up)
        self.assertEqual(rc, 1)

    def test_calibrate_creates_config_and_calls_upstream(self):
        up = fake_upstream()
        seen = []
        up.calibrate = lambda cfg, path: seen.append((path, pathlib.Path(path).read_text()))
        fake_tk = types.SimpleNamespace(Misc=type("Misc", (), {"configure": lambda self, cnf=None, **kw: None}))
        with mock.patch.dict(sys.modules, {"tkinter": fake_tk}):
            rc = pm.main(["--calibrate", "--config", str(self.cfg)], upstream=up)
        self.assertEqual(rc, 0)
        self.assertEqual(seen, [(str(self.cfg), "{}\n")])
        self.assertEqual(up.calls, [])  # calibration does not start the mouse


class DryRunSinkTest(unittest.TestCase):
    def test_logs_totals_per_interval_and_resets(self):
        now = [0.0]
        sink = pm.DryRunSink(interval_s=1.0, clock=lambda: now[0])
        sink.move(10, -5)
        sink.button(1, True)
        sink.button(1, False)
        now[0] = 1.5
        with self.assertLogs("podsmouse", level="INFO") as logs:
            sink.scroll(2)
        self.assertIn("dx=+10 dy=-5 wheel=+2 clicks=1", logs.output[0])
        self.assertEqual((sink.dx, sink.dy, sink.wheel, sink.clicks), (0, 0, 0, 0))

    def test_rejects_bad_button(self):
        with self.assertRaises(ValueError):
            pm.DryRunSink().button(4, True)


class PipelineSimulationTest(unittest.TestCase):
    """Upstream Controller -> SinkPointer -> our sinks, with synthetic and recorded sensor data."""

    def test_turning_head_right_moves_pointer_right(self):
        sink = NullSink()
        ctl = make_controller(SinkPointer(sink))
        feed_rates(ctl, (30, 0, 0), 0.5)
        moves = [c for c in sink.calls if c[0] == "move"]
        self.assertGreater(sum(c[1] for c in moves), 100)
        self.assertLessEqual(abs(sum(c[2] for c in moves)), 2)

    def test_looking_up_moves_pointer_up(self):
        sink = NullSink()
        ctl = make_controller(SinkPointer(sink))
        feed_rates(ctl, (0, 30, 0), 0.5)
        self.assertLess(sum(c[2] for c in sink.calls if c[0] == "move"), -100)

    def test_full_chain_to_hid_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            dev = pathlib.Path(tmp) / "hidg0"
            dev.touch()
            ptr = SinkPointer(HidSink(str(dev)))
            ctl = make_controller(ptr)
            feed_rates(ctl, (30, 0, 0), 0.5)
            ptr.close()
            reports = list(struct.iter_unpack("Bbbb", dev.read_bytes()))
        self.assertTrue(reports)
        self.assertTrue(all(-127 <= v <= 127 for r in reports for v in r[1:]))
        self.assertGreater(sum(r[1] for r in reports), 100)
        self.assertTrue(all(r[0] == 0 for r in reports))  # no buttons held

    @unittest.skipUnless(CAPTURE.exists(), "upstream capture missing")
    def test_replay_recorded_airpods3_capture(self):
        # Real sensor data recorded by upstream on AirPods 3, replayed through our output path.
        rows = json.loads(CAPTURE.read_text())
        sink = NullSink()
        ctl = make_controller(SinkPointer(sink))
        ctl.engine = UPSTREAM.MotionEngine(ctl.cfg["bias"])
        for r in rows:
            blk = make_block(r["ts"], r["gyr"], r["grav"], r["att"])
            ctl.on_block(blk, r["t"])
            ctl._last_render = r["t"] - 0.008
            ctl.render(r["t"])
        moves = [c for c in sink.calls if c[0] == "move"]
        self.assertTrue(moves)
        self.assertTrue(all(isinstance(c[1], int) and isinstance(c[2], int) for c in moves))


def make_block(ts_ns, w_lsb, g_raw, att=(0, 0, 0)):
    """Same 58-byte sensor block layout as upstream's tests."""
    b = bytearray(58)
    b[0] = 1
    struct.pack_into("<Q", b, 1, ts_ns)
    struct.pack_into("<hhh", b, 20, *att)
    struct.pack_into("<hhh", b, 26, *[int(round(c)) for c in w_lsb])
    struct.pack_into("<hhh", b, 44, *[int(round(c)) for c in g_raw])
    return bytes(b)


if __name__ == "__main__":
    unittest.main()
