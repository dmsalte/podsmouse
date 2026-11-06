# PodsMouse – plan for using AirPods Pro 3 as a mouse on Windows

Last updated: 2026-11-06

## Goals and scope

The goal is for AirPods Pro 3 to control the mouse pointer on an ordinary Windows PC, with no driver or software installed on Windows. A Raspberry Pi Zero 2 W acts as a Bluetooth bridge and appears to the PC as a standard USB mouse. The starting point is [mousepods](https://github.com/starman-tech/mousepods) (Apache-2.0).

**Deliverables**

- A verified sensor stream from AirPods Pro 3, with a documented packet format
- Mouse mode, where head movement moves the pointer, with recentering
- Clicks by stem press, head nod or dwell (the pointer resting in place for a moment)
- The Pi appears as a USB HID mouse, so Windows needs no installation
- A simple web UI on the Pi for battery, calibration and raw data

**Out of scope for the first version**

- Audio through the Pi (USB sound card). Considered in phase 5.
- Pointer and Glide modes from mousepods
- AirPods models other than Pro 3 (Pro 2 and AirPods 3 should still work)
- A custom Windows driver or service

## Why a Pi bridge

Windows has no user-mode API for custom Bluetooth Classic L2CAP channels. AirPods send sensor data over AACP on PSM `0x1001`, and that channel can only be opened by a kernel-mode profile driver, which is what MagicPods ships. A Pi running BlueZ has no such limitation.

## Architecture

```
AirPods Pro 3 ──Bluetooth Classic, L2CAP PSM 0x1001──▶ Raspberry Pi Zero 2 W ──USB, HID mouse──▶ Windows PC
                                                       │
                                                       ├─ AAPClient     opens the AACP channel, reads sensor packets
                                                       ├─ MotionEngine  turns gravity and gyro into yaw and pitch
                                                       ├─ Controller    smoothing, acceleration, clicks, 120 Hz
                                                       └─ HidSink (new) 4-byte reports to /dev/hidg0
```

The only new code in the main path is `HidSink`, which replaces `/dev/uinput`. Windows sees the Pi as a standard HID mouse and uses its built-in driver, so it also works on locked-down machines where you cannot install anything.

## Hardware

| Part | Why | Note |
| --- | --- | --- |
| Raspberry Pi Zero 2 W | Bluetooth and USB OTG on one board | A version with pre-soldered headers is handy |
| microSD card, 16–32 GB | Raspberry Pi OS Lite (Bookworm, 64-bit) | A1/A2 class |
| Micro-USB data cable to USB-A/C | Powers the Pi and carries the HID connection to the PC | Must be a data cable, not charge-only. Use the *USB* port, not *PWR* |
| Simple case | Protects the board on the desk | Optional |
| (Phase 0) Linux PC or laptop with Bluetooth | Map the Pro 3 before the Pi is in place | A live USB with Ubuntu is enough |

## Phases

Phase 0 is the most important. It decides whether the Pro 3 delivers sensor data outside the Apple ecosystem at all, and it can be done on any Linux machine with Bluetooth before a Pi is bought. A phase is only done when its acceptance check passes on real hardware.

| Phase | Work | Acceptance check | Needs Pi |
| --- | --- | --- | --- |
| 0. Map the Pro 3 | Run mousepods `--diag` and the sensor explorer against the Pro 3. Save raw captures to `captures/pro3/`. Find out whether the Pro 3 uses SensorDataWX like the Pro 2, or something new. | Stable stream at a known rate (Hz) for at least 10 min. Axes identified. | No |
| 1. Pi setup | Pi OS Lite, BlueZ, PSM 0x1001 allowed, MTU 2582, pairing with the Pro 3 | `--diag` on the Pi gives the same stream as in phase 0 | Yes |
| 2. USB HID gadget | configfs gadget with a relative mouse (buttons, X/Y, wheel). A test script that draws a square. | Windows shows "HID-compliant mouse" with no driver, and the pointer draws the square | Yes |
| 3. Wiring | Replace the mousepods `uinput` output with a `HidSink` that writes to `/dev/hidg0` | Head movement moves the Windows pointer with under 30 ms latency | Yes |
| 4. Usability | Calibration, recentering, clicks, pause, and autostart as a systemd service | 15 min of normal use (opening apps, clicking buttons) without touching the mouse | Yes |
| 5. Optional | USB sound card through the Pi (A2DP to the AirPods) and Pointer mode | Audio and control at the same time over one cable | Yes |

## Repository layout and reuse

The repository builds on mousepods, so the protocol code and tests come along. New code lives in separate modules, which keeps it easy to pull in upstream changes. The upstream `LICENSE` and `NOTICE` must be kept unchanged. Anything reused from upstream `docs/` and `captures/` (CC BY 4.0) must be attributed.

```
podsmouse/
├── CLAUDE.md                 # instructions for Claude Code
├── upstream/                 # mousepods as a git subtree, do not edit
├── podsmouse/
│   ├── sinks/
│   │   ├── base.py           # Sink interface: move(dx,dy), button(b,down), scroll(n)
│   │   ├── hid_gadget.py     # writes 4-byte reports to /dev/hidg0
│   │   └── null.py           # for tests and --dry-run
│   ├── models/pro3.py        # Pro 3-specific parsing, if phase 0 requires it
│   └── main.py               # wires AAPClient → MotionEngine → Controller → Sink
├── gadget/
│   ├── setup-hid-gadget.sh   # configfs: VID/PID, HID descriptor, UDC binding
│   └── hid-mouse.desc        # report descriptor (relative mouse, 3 buttons, wheel)
├── systemd/
│   ├── podsmouse-gadget.service
│   └── podsmouse.service
├── captures/pro3/            # raw captures from phase 0
├── docs/pro3-findings.md     # packet format, axes and rate for the Pro 3
└── tests/                    # upstream tests + tests for sinks and the Pro 3 parser
```

**Reused as is:** `AAPClient`, `MotionEngine` (gravity and gyro bias), One-Euro smoothing, the web UI, and the 37 tests that need no hardware.

**Replaced:** the `/dev/uinput` output is replaced by `HidSink`. Linux desktop hotkeys are replaced by stem gestures and buttons in the web UI, since the Pi has no keyboard.

## Risks and open questions

The biggest risk is that the Pro 3 delivers no sensor data, or needs an unknown start packet. Phase 0 settles this before any money is spent on a Pi.

| Risk | Impact | Mitigation |
| --- | --- | --- |
| The Pro 3 uses a new or locked sensor format | The project stops at phase 0 | Try both known start packets (like HT_START in pods-head-tracker), compare with Pro 2 captures, and ask on the LibrePods Discord |
| Low sample rate (≈25 Hz like the Pro 2) | The pointer feels jerky | Run HID at 120 Hz with prediction/interpolation. Tune One-Euro. |
| AirPods connect to only one host at a time | No audio on the PC while the Pi holds the AirPods | Accept it in v1, and solve it with USB audio through the Pi in phase 5 |
| An Apple firmware update changes the protocol | The sensor stream stops | Keep captures per firmware version and log the version on connect |
| The Pi Zero 2 W is too slow | Latency or dropped packets | Measure CPU use in phase 3. A Pi 4 is the fallback. |

**Open questions**

- Which firmware are the Pro 3 on, and are they paired with an iPhone that can update them?
- Which click method should be the default: stem press, head nod or dwell?

## Sources

- [starman-tech/mousepods](https://github.com/starman-tech/mousepods)
- [pods-head-tracker (Pi bridge for OpenTrack)](https://github.com/batubozkan/pods-head-tracker/releases)
- [sony-head-tracker wiki: why AirPods cannot work directly on Windows](https://github.com/NicholasSlattery/sony-head-tracker/wiki)
- [LibrePods discussion #259](https://github.com/librepods-org/librepods/discussions/259)
