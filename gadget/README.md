# USB HID gadget

Makes the Raspberry Pi Zero 2 W appear to the PC as a standard USB mouse, using the Linux
configfs gadget framework. Windows uses its built-in "HID-compliant mouse" driver.

## One-time boot setup (Raspberry Pi OS Bookworm)

1. Enable the USB device controller. Add this line to `/boot/firmware/config.txt`
   (under `[all]`):

   ```
   dtoverlay=dwc2
   ```

2. Load the modules at boot:

   ```
   echo dwc2        | sudo tee -a /etc/modules
   echo libcomposite | sudo tee -a /etc/modules
   ```

3. Reboot.
4. Connect the Pi to the PC with a **data** cable on the port marked **USB**, not **PWR**.
   That one cable powers the Pi and carries the mouse connection.

Check that a controller is present:

```
ls /sys/class/udc    # should list something like 3f980000.usb
```

## Build the gadget

```
sudo gadget/setup-hid-gadget.sh                  # build and bind
sudo gadget/setup-hid-gadget.sh --group podsmouse # also give group podsmouse rw on /dev/hidg0
sudo gadget/setup-hid-gadget.sh --remove         # tear down
```

The script is idempotent: it removes any existing PodsMouse gadget before it builds a new one.

## Report format

Defined in `hid-mouse.desc` (annotated hex). Every report is 4 bytes, no report ID:

| Byte | Field | Values |
| --- | --- | --- |
| 0 | Buttons | bit0 left, bit1 right, bit2 middle, bits 3–7 zero |
| 1 | X | signed int8, -127..127, relative |
| 2 | Y | signed int8, -127..127, relative, positive = down |
| 3 | Wheel | signed int8, -127..127, relative, positive = up |

`HidSink` in `podsmouse/sinks/hid_gadget.py` must write exactly this format.
The interface uses subclass 0 / protocol 0 (no boot interface), so the host never switches
to the 3-byte boot mouse report. The mouse will therefore not work in BIOS/UEFI menus; that is
not a goal of this project.

## Quick manual test

With the gadget bound and the PC showing the mouse, this moves the pointer 100 px right:

```
printf '\x00\x64\x00\x00' | sudo tee /dev/hidg0 >/dev/null
```

## Square test (phase 2 acceptance check, T07)

Draws a square with smooth moves at 120 Hz and ends where it started. No AirPods needed.

```
python -m podsmouse.square                          # 3 s countdown, then one square on /dev/hidg0
python -m podsmouse.square --repeat 3 --click --scroll 3
python -m podsmouse.square --sink null --delay 0    # dry run on any machine
```

Run it as a user with write access to `/dev/hidg0` (see `--group` above) or with `sudo`.
Pass when: Device Manager shows "HID-compliant mouse" under *Mice and other pointing devices*
with no driver install, and the pointer traces a closed square. With *Enhance pointer precision*
on, the size depends on speed (try `--seconds 0.5` and `--seconds 2`), but the path should still close.
`--click` left-clicks at the start point, so put the pointer on an empty part of the desktop.

## Status

Written and checked in simulation only (syntax, descriptor parsing in `tests/test_hid_descriptor.py`,
square path and HID reports in `tests/test_square.py`). Not yet run on a Pi or seen by Windows. That is task T07.
