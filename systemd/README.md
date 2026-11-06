# systemd units

Two units start PodsMouse on boot, with no one logged in:

| Unit | Runs as | Does |
| --- | --- | --- |
| `podsmouse-gadget.service` | root, oneshot | Builds the USB HID gadget with `gadget/setup-hid-gadget.sh --group podsmouse`, so `/dev/hidg0` belongs to group `podsmouse`. Removes the gadget on stop. |
| `podsmouse.service` | user `podsmouse` | Runs `python3 -m podsmouse.main --sink hid --config /var/lib/podsmouse/config.json`. Starts after the gadget and BlueZ, restarts on failure. |

Both expect the repository at `/opt/podsmouse`.

## Install (Raspberry Pi OS Bookworm)

Do the one-time boot setup in `gadget/README.md` first (dwc2, libcomposite, reboot).

```
sudo git clone https://github.com/dmsalte/podsmouse /opt/podsmouse
sudo useradd --system --no-create-home --shell /usr/sbin/nologin podsmouse
sudo usermod -aG bluetooth podsmouse

sudo cp /opt/podsmouse/systemd/podsmouse-gadget.service /etc/systemd/system/
sudo cp /opt/podsmouse/systemd/podsmouse.service        /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now podsmouse-gadget.service podsmouse.service
```

Pair the AirPods once with `bluetoothctl` (buds in your ears, case open) before you start the service.

## Check and debug

```
systemctl status podsmouse-gadget podsmouse
journalctl -u podsmouse -f
ls -l /dev/hidg0          # should be crw-rw---- root podsmouse
```

## Notes

- The service needs no root. Upstream opens the L2CAP channel (PSM 0x1001, MTU 2582) as a
  normal user; `/dev/hidg0` access comes from the group set by the gadget unit.
- `podsmouse.service` is sandboxed (`ProtectSystem=strict`, `DevicePolicy=closed` with only
  `/dev/hidg0` allowed, limited address families). If something on the Pi is blocked by this,
  loosen the one setting that blocks it and note it here.
- Config and calibration live in `/var/lib/podsmouse` (`StateDirectory`), the control socket in
  `/run/podsmouse` (`RuntimeDirectory`, exported as `XDG_RUNTIME_DIR`).

## Depends on T08

`podsmouse.main` does not exist yet. T08 must provide at least these flags, which the unit uses:

- `--sink hid|null` – which output to use
- `--config PATH` – writable config and calibration file

Until then `podsmouse.service` fails to start; the gadget unit works on its own.

## Status

Written and checked in simulation only (`systemd-analyze verify` where available). Not run on a Pi.
