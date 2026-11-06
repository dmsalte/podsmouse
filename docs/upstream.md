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

So T08 needs a small adapter (`SinkPointer`) that exposes this interface on top of any `Sink`,
keeps the fractional remainders, and is passed to `Controller` instead of `Pointer`.
`Controller.__init__` takes the pointer as an argument (`self.ptr = pointer`), but `run()` builds it
itself: `ptr = NullPointer() if diag else Pointer()`. T08 must therefore either reimplement the
small `run()` loop in `podsmouse/main.py` around `AAPClient`, `Controller` and our adapter, or
monkeypatch `Pointer` before calling `run()`. Reimplementing is cleaner and keeps `upstream/` untouched.
`move_abs(0.5, 0.5)` is also called on recenter in mouse mode, so the adapter must accept it as a no-op.

Upstream comments and log messages are mostly in French.
