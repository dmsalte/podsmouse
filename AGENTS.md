# PodsMouse – instructions for coding agents

This file is the single source of truth for every coding agent working on this
repository (OpenAI Codex, Claude Code and others). `CLAUDE.md` only imports this
file. Put shared rules here, never in an agent-specific file.

## Project

AirPods Pro 3 as a head-tracking mouse for Windows. A Raspberry Pi Zero 2 W
talks to the AirPods over Bluetooth (AACP, L2CAP PSM 0x1001) and presents
itself to the PC as a standard USB HID mouse. Windows needs no driver or software.

Based on starman-tech/mousepods (Apache-2.0), vendored in `upstream/` as a git subtree.
The full plan, phases and acceptance checks are in `docs/plan.md`.

## Ground rules
- Never edit files under `upstream/`. Extend via `podsmouse/` (sinks, model parsers).
  If upstream needs a change, write it as a small patch in `patches/` and explain why.
- Keep `LICENSE` and `NOTICE` intact. Attribute anything reused from upstream `docs/` or `captures/` (CC BY 4.0).
- Target: Raspberry Pi OS Lite (Bookworm, 64-bit), Python 3.11, BlueZ from the distro. No root at runtime
  except the gadget setup script; the service user needs access to the Bluetooth socket and `/dev/hidg0`.
- No new dependencies without asking the maintainer. Prefer stdlib.
- Hardware is the source of truth. Do not claim a feature works until it has been verified on the
  real AirPods Pro 3 + Pi + Windows PC. Say clearly what was tested in simulation only.
- All code, comments, docs and commit messages are in English.

## Architecture
AAPClient → MotionEngine → Controller → Sink
- `Sink` interface (`podsmouse/sinks/base.py`): `move(dx, dy)`, `button(btn, down)`, `scroll(n)`.
- `HidSink` writes 4-byte reports `[buttons, dx, dy, wheel]` (signed int8, clamp ±127, split larger moves)
  to `/dev/hidg0`. Report descriptor is in `gadget/hid-mouse.desc` and must match.
- HID byte 0 is bits 0/1/2 = left/right/middle plus five zero padding bits;
  bytes 1/2/3 are signed relative X/Y/wheel (-127..127), with no report ID.
  Y positive is down; wheel positive is up. The four-byte layout extends the
  boot-style mouse layout and requires report protocol (not strict boot protocol).
- `HidSink` splits both movement and scroll totals into bounded reports, keeps
  button state across reports, and releases held buttons when closed. It opens
  an existing device write-only in unbuffered binary mode and writes each report
  in one call; missing paths raise an error pointing to the gadget setup script.
- `NullSink` for tests and `--dry-run`.
- All sinks implement `close()` and support `with sink:` to close on exit.
- Button numbers are 1 = left, 2 = right, 3 = middle; other numbers raise `ValueError`.
- `NullSink.calls` records ordered tuples: `("move", dx, dy)`,
  `("button", btn, down)`, `("scroll", n)`, and `("close",)`.
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
- Tests (no hardware): `python -m unittest discover -s tests` (also runs the 37 upstream tests)
- Update upstream: `git subtree pull --prefix upstream https://github.com/starman-tech/mousepods main --squash`
  on its own branch, then update `docs/upstream.md`. See that file for how upstream fits in.
- Diagnostics on Pi: `python -m podsmouse.main --diag`
- Dry run: `python -m podsmouse.main --sink null`
- Run on the Pi: `python -m podsmouse.main --sink hid --config PATH` (also `--hid-device`, `--web-port`, `--no-web`, `-v`).
  These flags are a shared interface: `systemd/podsmouse.service` depends on `--sink` and `--config`.
- Desktop testing on a Linux PC: `python -m podsmouse.main --calibrate`, then `python -m podsmouse.main --sink uinput`
  (needs `python3-tk` and `python3-evdev`).
- Output language: upstream prints French; `podsmouse/english.py` translates terminal output, notifications and the
  calibration window at runtime (default `--lang en`). When upstream adds a log message, `tests/test_english.py`
  fails until the message is added to `english.LOG_TEMPLATES`. Never translate by editing `upstream/`.
- Web UI language: `podsmouse/web_english.py` builds an English page from `upstream/ui/index.html` at startup
  (written to `ui-en.html` next to the config file) and swaps the server's label tables. When upstream changes the
  page or adds server text, `tests/test_web_english.py` fails until `HTML_REPLACEMENTS`/`PHRASES` are updated.
- Gadget setup: `sudo gadget/setup-hid-gadget.sh` (idempotent; tears down and rebuilds)
- Gadget test (phase 2 check): `python -m podsmouse.square` draws a square on `/dev/hidg0` (`--sink null` for a dry run).

## Working together (multiple agents)

Several agents may work on this repository, often without seeing each other's sessions.
The repository is the only shared memory, so keep it current.

1. **Claim before you start.** Pick a task from `docs/TASKS.md`, set its owner to your agent name
   (`codex`, `claude`) and status to `in progress`, and commit that change on your branch first.
   Do not start a task someone else has claimed.
2. **One branch per task.** Name it `<agent>/<short-task>`, for example `codex/hid-sink` or
   `claude/pro3-parser`. Never commit directly to `main`. Merge through a pull request.
3. **Small, focused pull requests.** One task per PR. Fill in the PR template, including what was
   tested on hardware and what only in simulation.
4. **Stay in your lane.** Only touch files your task needs. If you must change a shared interface
   (`podsmouse/sinks/base.py`, the HID report format, CLI flags), say so in the PR title with
   `[interface]` and update this file and the tests in the same PR.
5. **Hand off in writing.** Before you stop, append a dated entry to `docs/progress.md`:
   what you did, what is left, and anything the next agent must know. Update `docs/TASKS.md`.
6. **Rebase, don't overwrite.** Rebase on `main` before opening a PR. If another agent's change
   conflicts with yours, keep theirs and adapt your change, then explain it in the PR.
   Exception: a branch that contains a `git subtree` commit for `upstream/` is updated by merging
   `main` into it, never rebased, and is merged on GitHub with "Create a merge commit" (a rebase or
   squash loses the subtree metadata that `git subtree pull` needs).
7. **Stacked PRs.** Prefer branching from `main`. If a PR must build on another unmerged PR, base it
   on that branch, say so in the description, and retarget it to `main` once the first PR is merged.
   Never merge a PR whose base is not `main`; it lands on the other branch, not on `main`.
8. **Tests must pass.** Run `python -m unittest discover -s tests` before every push.
9. **Attribution.** End commit messages with a trailer naming the agent, for example
   `Co-Authored-By: Codex <noreply@openai.com>` or `Co-Authored-By: Claude <noreply@anthropic.com>`.

## Phase order
0 Pro 3 mapping → 1 Pi setup → 2 HID gadget → 3 wire HidSink → 4 usability → 5 optional audio.
Each phase ends with its acceptance check run on hardware and a short note in `docs/progress.md`.
Write unit tests for every parser and sink using recorded captures, so they run without hardware.
