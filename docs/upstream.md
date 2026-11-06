# Upstream: mousepods

`upstream/` holds [starman-tech/mousepods](https://github.com/starman-tech/mousepods) as a
squashed git subtree. Do not edit files there (see `AGENTS.md`). Changes we need go in
`podsmouse/`, or as a small patch in `patches/` with a reason.

| | |
| --- | --- |
| Vendored commit | `79736c79ae5f86d62a137e5747b658431b8c3d9e` (2026-11-06) |
| License | Apache-2.0 for code, CC BY 4.0 for `docs/` and `captures/` |
| Python dependency | `evdev` (only imported by upstream `Pointer`, which we replace) |
| Upstream tests | 37, run through `tests/test_upstream_suite.py`, no hardware needed |

## Updating

```
git subtree pull --prefix upstream https://github.com/starman-tech/mousepods main --squash
python -m unittest discover -s tests
```

Do it on its own branch and PR, and update the commit hash above.

## Notes for wiring (T08)

Everything lives in one module, `upstream/airpods_mouse_controller.py`:

- `AAPClient` – AACP connection over L2CAP PSM 0x1001
- `MotionEngine`, `GlideEngine` – orientation from gravity and gyro
- `OneEuro` – smoothing
- `Controller` – turns motion into pointer actions
- `Pointer` – output through `/dev/uinput` with python-evdev. This is what we replace.
- `NullPointer` – does nothing, accepts any call

`Controller` calls the pointer object with this interface (duck typed, not an ABC):

| Upstream `Pointer` method | Meaning | Maps to our `Sink` |
| --- | --- | --- |
| `move_rel(dx, dy)` | relative move, floats; `Pointer` keeps the fractional remainder | `move(int dx, int dy)` after accumulating fractions |
| `move_abs(fx, fy)` | absolute position, 0..1 (Pointer mode) | not possible on a relative HID mouse; out of scope for v1 |
| `click(button)` | `"left"`, `"right"`, `"middle"`; press, ~15 ms, release | `button(n, True)`, wait, `button(n, False)` |
| `scroll(lines)` | float lines; fractional remainder kept | `scroll(int n)` after accumulating fractions |
| `close()` | release devices | `close()` |

## How T08 wires it (done)

- `podsmouse/pointer.py` – `SinkPointer` implements the table above on top of any `Sink`.
- `podsmouse/main.py` – imports upstream, sets `upstream.Pointer = lambda: SinkPointer(sink)` and then calls
  upstream `run()` unchanged. That reuses all of upstream's run loop (reconnect with backoff, stem gestures,
  stuck-sensor recovery, config hot reload, web UI) instead of copying ~120 lines of it.
  Trade-off: if upstream renames `Pointer` or changes how `run()` builds it, `tests/test_main.py` will not
  catch it (it uses a fake upstream for the CLI tests). Check `run()` when updating the subtree.
- In `--diag` mode upstream uses its own `NullPointer` and no sink is opened.
- Mode `pointeur` (absolute positioning) cannot work over a relative HID mouse; `main` warns about it.

## Web UI on the Pi

Upstream's web UI binds to `127.0.0.1:8737` only. On a headless Pi, reach it from your PC with an SSH tunnel:

```
ssh -L 8737:127.0.0.1:8737 <user>@<pi-address>
```

then open http://127.0.0.1:8737 on the PC. Calibration also runs from there.

## Language

Upstream comments, log messages and UI text are in French. `podsmouse/english.py` translates what the user sees
(log lines, the `--diag` status line, notifications, the calibration window) at runtime when started through
`podsmouse.main` (default `--lang en`). The web UI is still French (T13). Running `upstream/airpods_mouse_controller.py`
directly gives the original French output.
