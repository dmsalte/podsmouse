# Progress log

Newest entry first. Every agent appends an entry before it stops working.
Format: date, agent, what was done, what is left, notes for the next agent.

## 2026-11-07 – claude (T07 script, branch claude/square-test)
- `podsmouse/square.py` (`python -m podsmouse.square`): draws a square through `HidSink` with even integer steps
  at 120 Hz (deadline pacing, so sleep overshoot does not add up), ends exactly at the start point. Options:
  `--side`, `--seconds`, `--rate`, `--repeat`, `--click` (left click after each square), `--scroll N`
  (N up, then N down), `--delay` (countdown, default 3 s), `--sink null` (dry run, prints net totals).
- `tests/test_square.py` (12 tests): exact side totals, direction order, pacing with a fake clock, valid int8
  HID reports written to a temporary file, CLI errors including a missing gadget.
- `gadget/README.md` has the pass criteria; `AGENTS.md` lists the command.
- Tested in simulation only (134 tests after rebasing on T13) plus a dry run. Not run on a Pi, not seen by Windows.
- Left (maintainer, hardware): bind the gadget on the Pi, run `python -m podsmouse.square --click --scroll 3`,
  check Device Manager shows "HID-compliant mouse" and the pointer closes the square. Note the result here
  and mark T07 done.

## 2026-11-07 – claude (T13, branch claude/web-english)
- `podsmouse/web_english.py`: English web UI at runtime, no upstream edits. The page is built from
  `upstream/ui/index.html` with an exact-match replacement table and written to `ui-en.html` next to the config file
  (rewritten on each start; first tried a temp file, but it leaked on SIGTERM). The server's label tables (models,
  battery, ear state, AAP controls, HID usages, sensor services, aim/glide calibration steps) are replaced, and a
  `WebUI` subclass translates the status line, calibration text and report kinds.
- The page's JavaScript compares server values (`"en charge"`, `"déconnecté"`, the `"Nom"` label); the English page
  compares the English values instead, and a test checks both sides match.
- `tests/test_web_english.py` fails if a replacement stops matching upstream, if accented French is left on the page
  (comments excluded), or if upstream adds French server text. The two web log messages are in `english.LOG_TEMPLATES`.
- Left in French on purpose: HTTP API error bodies (`introuvable`, `JSON invalide`); the page never shows them.
- Tested in simulation only (122 tests) plus a smoke run of `--sink null` without Bluetooth: the page and
  `/api/stream` status are English. Not checked with AirPods connected (battery, sensor and calibration views).

## 2026-11-06 – claude (T12, branch claude/english)
- Hardware result from the maintainer (not yet in captures/): the stream works on Linux (Ubuntu, Intel AX201)
  with AirPods **Pro 2 (USB-C)**, product ID `0x2024`, at roughly 96 Hz with upstream defaults. The maintainer
  also plans to use Pro 3; Pro 3 (`0x2027`) is still untested. Raw diag log and btsnoop exist on the maintainer's
  machine and should be committed (T01/T02).
- `podsmouse/english.py`: runtime English for upstream log lines, the `--diag` line, notifications and the
  calibration window. No upstream edits. `tests/test_english.py` fails if upstream adds an untranslated log message.
- `podsmouse.main`: new `--sink uinput` (moves the local Linux pointer, for desktop testing), `--calibrate`
  (creates the config file first; upstream's calibrate() fails if it is missing) and `--lang en|fr`.
- Tested in simulation only (112 tests) plus a smoke run of `--diag` without Bluetooth (English output confirmed).
- Next: T13 (English web UI), T01/T02 captures for Pro 2 (USB-C), Pro 3 when available.

## 2026-11-06 – claude (T08, branch claude/main-cli)
- Added `podsmouse/pointer.py` (`SinkPointer`: upstream Pointer interface over a Sink; keeps fractional
  remainders for move and scroll; `move_abs` is a no-op with a one-time warning) and `podsmouse/main.py`.
- `main` reuses upstream `run()` unchanged by replacing `upstream.Pointer` with our adapter. Flags:
  `--sink hid|null`, `--hid-device`, `--config`, `--diag`, `--web-port`, `--no-web`, `-v`.
  `--sink null` uses a bounded `DryRunSink` that logs totals once per second.
- Tests (96 total, all pass): CLI wiring with a fake upstream, plus the real upstream Controller driving
  `NullSink` and `HidSink` (head right -> pointer right, head up -> pointer up, valid int8 HID reports), and a
  replay of upstream's recorded AirPods 3 capture through our output path.
- Smoke test without Bluetooth: starts, web UI up, retries connection with backoff, Ctrl-C exits cleanly.
- Not run on a Pi, with AirPods, or with Windows. `podsmouse.service` (T10) should now start.
- Web UI is on 127.0.0.1 only; use an SSH tunnel from the PC (see `docs/upstream.md`). Relevant for T11.
- Next: T01 and T07 on hardware (maintainer), then T11.

## 2026-11-06 – claude (T10, branch claude/systemd)
- Added a rule to `AGENTS.md` on stacked PRs and on merging (not rebasing) branches that touch `upstream/`.
- Added `systemd/podsmouse-gadget.service` (root oneshot: builds the gadget, `/dev/hidg0` to group
  `podsmouse`) and `systemd/podsmouse.service` (user `podsmouse`, sandboxed, restarts on failure).
- Added `systemd/README.md` with install steps for `/opt/podsmouse`.
- `podsmouse.service` expects T08 to provide `python3 -m podsmouse.main --sink hid --config PATH`.
  It fails to start until T08 lands; the gadget unit works on its own.
- Tested in simulation only: `systemd-analyze verify` passes with the repo at `/opt/podsmouse`.
  Not run on a Pi. The sandboxing may need loosening once tested on hardware.

## 2026-11-06 – claude (landing T05, branch claude/land-t05)
- PR #3 (T05) was based on `codex/sinks`, so merging it put `HidSink` into `codex/sinks`, not `main`.
- Merged `codex/sinks` into `main` on `claude/land-t05` without changing Codex's code; only resolved
  conflicts in this log and `docs/TASKS.md`. T03, T04, T05 and T06 are now done.
- Lesson for stacked PRs: after the base PR merges, retarget the dependent PR to `main` before merging it.

## 2026-11-06 – codex – T05
- Added `HidSink`, exported it from `podsmouse.sinks`, and documented the shared
  four-byte report contract in its docstring and `AGENTS.md`.
- Writes each report in one unbuffered binary write, preserves held buttons,
  and splits large X/Y movements and wheel steps into -127..127 chunks without
  losing totals. Closing releases held buttons and closes even if release fails.
- Missing devices raise `FileNotFoundError` naming `gadget/setup-hid-gadget.sh`;
  opening never creates a regular file. Short writes fail without fragment retries.
- Simulation only: all 33 stdlib tests pass on Python 3.12.14, including 22 HID
  sink tests against temporary regular files, 6 NullSink/interface tests, and
  the 5 existing descriptor tests. Python 3.11 syntax checked; no 3.11 interpreter
  is installed here. Nothing has been run on a Pi or Windows, or real AirPods.
- Left: review T04 and T05, wire the sinks into the CLI (T08), and verify gadget
  behavior and the phase acceptance checks on real hardware (T07 and later).
- T04 is PR #2 (`codex/sinks` -> `main`). Following the one-task-per-PR rule,
  T05 is on `codex/hid-sink`, with a PR based on `codex/sinks`. Merge T04 first,
  then rebase/retarget T05 onto `main`; do not merge the dependency twice.
- The existing T06 descriptor and its tests match the reports. No changes were
  made to `gadget/`, `upstream/`, or `systemd/`.

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

## 2026-11-06 – codex – T04
- Added the abstract `Sink` interface, package initializers, and recording `NullSink`.
- Documented button numbering, invalid-button errors, context management, and the
  `NullSink.calls` tuple format in `AGENTS.md` for consumers of the new interface.
- Simulation only: all 11 stdlib unit tests pass on Python 3.12.14; Python 3.11
  syntax was checked, but a Python 3.11 interpreter is unavailable here.
  Nothing has been run on a Pi or Windows, or against real AirPods.
- Left: review T04, implement T05, wire sinks into the CLI in T08, and run the
  phase acceptance checks on hardware. `NullSink` records close calls too.
- Following `AGENTS.md`, T04 uses `codex/sinks`; T05 will use its own dependent
  branch and PR so each PR contains one task. Merge T04 before T05.

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
