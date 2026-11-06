# PodsMouse

AirPods Pro 3 as a head-tracking mouse for Windows. A Raspberry Pi Zero 2 W
talks to the AirPods over Bluetooth (AACP, L2CAP PSM 0x1001) and presents
itself to the PC as a standard USB HID mouse. Windows needs no driver or software.

Based on starman-tech/mousepods (Apache-2.0), vendored in `upstream/` as a git subtree.

## Ground rules
- Never edit files under `upstream/`. Extend via `podsmouse/` (sinks, model parsers).
  If upstream needs a change, write it as a small patch in `patches/` and explain why.
- Keep `LICENSE` and `NOTICE` intact. Attribute anything reused from upstream `docs/` or `captures/` (CC BY 4.0).
- Target: Raspberry Pi OS Lite (Bookworm, 64-bit), Python 3.11, BlueZ from the distro. No root at runtime
  except the gadget setup script; the service user needs access to the Bluetooth socket and `/dev/hidg0`.
- No new dependencies without asking. Prefer stdlib.
- Hardware is the source of truth. Do not claim a feature works until it has been verified on the
  real AirPods Pro 3 + Pi + Windows PC. Say clearly what was tested in simulation only.

## Architecture
AAPClient → MotionEngine → Controller → Sink
- `Sink` interface (`podsmouse/sinks/base.py`): `move(dx, dy)`, `button(btn, down)`, `scroll(n)`.
- `HidSink` writes 4-byte reports `[buttons, dx, dy, wheel]` (signed int8, clamp ±127, split larger moves)
  to `/dev/hidg0`. Report descriptor is in `gadget/hid-mouse.desc` and must match.
- `NullSink` for tests and `--dry-run`.
- Report rate target: 120 Hz from the Controller, independent of sensor rate.

## Pro 3 specifics
- Protocol for Pro 3 is unverified upstream. Findings go in `docs/pro3-findings.md`
  (packet layout, axes, sample rate, start packet) and raw captures in `captures/pro3/`.
- If Pro 3 differs from Pro 2 (SensorDataWX), put the parser in `podsmouse/models/pro3.py`
  and select it by model ID from the AAP handshake.
- Pro 2 streams at about 25 Hz. If Pro 3 is similar, expect to need prediction or extra smoothing.

## Bluetooth notes
- PSM 0x1001 must be allowed by the kernel; receive MTU must be 2582 (default 672 hides sensors).
- Buds in the case have sensors powered off. Test with buds in ears.

## Commands
- Tests (no hardware): `python -m unittest discover -s tests`
- Diagnostics on Pi: `python -m podsmouse.main --diag`
- Dry run: `python -m podsmouse.main --sink null`
- Gadget setup: `sudo gadget/setup-hid-gadget.sh` (idempotent; tears down and rebuilds)

## Workflow
- Work in the phase order from the plan: 0 Pro 3 mapping → 1 Pi setup → 2 HID gadget →
  3 wire HidSink → 4 usability → 5 optional audio.
- Each phase ends with its acceptance check run on hardware and a short note in `docs/progress.md`.
- Write unit tests for every parser and sink using recorded captures, so they run without hardware.
