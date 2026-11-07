# Tasks

Claim a task by setting **Owner** to your agent name and **Status** to `in progress`
before you start. See "Working together" in `AGENTS.md`.

Status values: `todo`, `in progress`, `review`, `done`, `blocked`.
`HW` = needs real hardware (AirPods Pro 3, Pi or Windows PC) to finish.

| ID | Phase | Task | HW | Owner | Status | Branch / PR |
| --- | --- | --- | --- | --- | --- | --- |
| T01 | 0 | Run mousepods `--diag` against AirPods Pro 3, save raw captures to `captures/pro3/` | yes | maintainer | todo | |
| T02 | 0 | Write `docs/pro3-findings.md` from the captures (packet layout, axes, rate, start packet) | no | | blocked (T01) | |
| T03 | 1 | Vendor mousepods into `upstream/` as a git subtree | no | claude | done | #4 |
| T04 | 2 | `Sink` interface, `NullSink` and unit tests | no | codex | done | #2 |
| T05 | 2 | `HidSink` (4-byte reports, clamp and split) and unit tests against a fake device file | no | codex | done | #3, landed via claude/land-t05 |
| T06 | 2 | `gadget/hid-mouse.desc` and idempotent `gadget/setup-hid-gadget.sh` (configfs) | no | claude | done | #1 |
| T07 | 2 | Square-drawing test script; verify on Windows | yes | | todo | |
| T08 | 3 | `podsmouse/main.py` wiring upstream pipeline to a Sink, with `--sink` and `--diag` | no | claude | done | #7 |
| T09 | 3 | Pro 3 parser in `podsmouse/models/pro3.py`, if T02 shows it differs from Pro 2 | no | | blocked (T02) | |
| T10 | 4 | systemd units for gadget and service, autostart on boot | no | claude | done | #5 |
| T11 | 4 | Calibration, recenter and click methods tuned on hardware | yes | | todo | |
| T12 | 4 | English for terminal output and calibration window (runtime translation, no upstream edits); `--sink uinput` and `--calibrate` in `podsmouse.main` | no | claude | done | claude/english |
| T13 | 4 | English web UI (translated copy or upstream contribution) | no | claude | review | claude/web-english |
