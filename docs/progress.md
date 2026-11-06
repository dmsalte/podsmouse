# Progress log

Newest entry first. Every agent appends an entry before it stops working.
Format: date, agent, what was done, what is left, notes for the next agent.

## 2026-11-06 – claude (T03, branch claude/vendor-upstream)
- Vendored starman-tech/mousepods at `79736c7` into `upstream/` with `git subtree add --squash`.
  Upstream files are unchanged; its LICENSE and NOTICE are kept.
- Root `NOTICE` now carries the attribution text the MousePods NOTICE requires.
- `tests/test_upstream_suite.py` runs the 37 upstream tests as part of our test run (42 total, all pass).
- `docs/upstream.md`: how to update the subtree, and the upstream `Pointer` interface that T08 must adapt
  (`move_rel`, `move_abs`, `click`, `scroll`, `close`). `run()` builds `Pointer()` itself, so T08 should
  reimplement the run loop in `podsmouse/main.py` instead of patching upstream.
- Upstream depends on `evdev`, but only inside `Pointer`, which we replace. No new dependency for us.
- Tested in simulation only.

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
