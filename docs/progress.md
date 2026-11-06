# Progress log

Newest entry first. Every agent appends an entry before it stops working.
Format: date, agent, what was done, what is left, notes for the next agent.

## 2026-11-06 – claude (T10, branch claude/systemd)
- Added `systemd/podsmouse-gadget.service` (root oneshot: builds the gadget, `/dev/hidg0` to group
  `podsmouse`) and `systemd/podsmouse.service` (user `podsmouse`, sandboxed, restarts on failure).
- Added `systemd/README.md` with install steps for `/opt/podsmouse`.
- `podsmouse.service` expects T08 to provide `python3 -m podsmouse.main --sink hid --config PATH`.
  It fails to start until T08 lands; the gadget unit works on its own.
- Tested in simulation only: `systemd-analyze verify` passes with the repo at `/opt/podsmouse`.
  Not run on a Pi. The sandboxing may need loosening once tested on hardware.

## 2026-11-06 – claude (T06, branch claude/hid-gadget)
- Added `gadget/hid-mouse.desc`: annotated hex report descriptor, 52 bytes, 4-byte report
  `[buttons, X, Y, wheel]`, no report ID, X/Y/wheel signed int8 -127..127 relative.
- Added `gadget/setup-hid-gadget.sh`: idempotent configfs setup, `--remove`, `--group <name>`
  for non-root access to `/dev/hidg0`. No xxd needed; converts the hex with printf.
  Interface is subclass 0 / protocol 0 (no boot mouse), so hosts always use the 4-byte report.
- Added `gadget/README.md` (one-time dwc2 boot setup, usage, report table, manual test).
- Added `tests/test_hid_descriptor.py`: parses the descriptor like a host and checks the layout.
- Tested in simulation only: `bash -n`, the unit tests, and that the script's hex conversion gives
  the same 52 bytes as the Python parser. Not run on a Pi, not seen by Windows.
- For whoever does T05 (HidSink): the report layout above is fixed by this descriptor; Y positive
  is down, wheel positive is up.
- Next: T07 on real hardware (maintainer): bind the gadget, check Windows shows "HID-compliant mouse".

## 2026-11-06 – claude
- Created the repository: plan (`docs/plan.md`), `AGENTS.md`, `CLAUDE.md`, task list, this log.
- `AGENTS.md` is the shared instruction file for all agents; `CLAUDE.md` only imports it.
- Nothing is implemented yet and nothing has been tested on hardware.
- Next: T01 (maintainer, needs AirPods Pro 3 + Linux with Bluetooth). T03–T06 can start now without hardware.
