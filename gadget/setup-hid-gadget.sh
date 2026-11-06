#!/usr/bin/env bash
# Create (or remove) the PodsMouse USB HID mouse gadget through configfs.
#
# Idempotent: an existing PodsMouse gadget is torn down and rebuilt on every run.
# Requires root, a USB device controller (dwc2 on the Pi Zero 2 W) and libcomposite.
# See gadget/README.md for the one-time boot configuration.
#
# Usage:
#   sudo gadget/setup-hid-gadget.sh             # build the gadget and bind it
#   sudo gadget/setup-hid-gadget.sh --remove    # tear it down
#   sudo gadget/setup-hid-gadget.sh --group podsmouse   # give this group rw on /dev/hidg0
#
# Environment overrides: PODSMOUSE_UDC (controller name), PODSMOUSE_DESC (descriptor file).

set -euo pipefail

GADGET_NAME="podsmouse"
CONFIGFS="/sys/kernel/config"
G="${CONFIGFS}/usb_gadget/${GADGET_NAME}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESC_FILE="${PODSMOUSE_DESC:-${SCRIPT_DIR}/hid-mouse.desc}"
REPORT_LENGTH=4

# Linux Foundation "Multifunction Composite Gadget" IDs, common for hobby gadgets.
ID_VENDOR="0x1d6b"
ID_PRODUCT="0x0104"

DEV_GROUP=""
ACTION="setup"

log()  { echo "setup-hid-gadget: $*"; }
die()  { echo "setup-hid-gadget: error: $*" >&2; exit 1; }

usage() {
    sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
    exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --remove)   ACTION="remove"; shift ;;
        --group)    [[ $# -ge 2 ]] || die "--group needs a value"; DEV_GROUP="$2"; shift 2 ;;
        -h|--help)  usage 0 ;;
        *)          echo "unknown argument: $1" >&2; usage 1 ;;
    esac
done

# Convert the annotated hex descriptor to raw bytes on stdout. No xxd needed.
descriptor_bytes() {
    local hex
    hex="$(sed 's/#.*//' "$DESC_FILE" | tr -d ' \t\r\n')"
    [[ -n "$hex" ]]                     || die "descriptor $DESC_FILE is empty"
    [[ "$hex" =~ ^[0-9A-Fa-f]+$ ]]      || die "descriptor $DESC_FILE has non-hex characters"
    (( ${#hex} % 2 == 0 ))              || die "descriptor $DESC_FILE has an odd number of hex digits"
    # shellcheck disable=SC2059
    printf "$(sed 's/../\\x&/g' <<<"$hex")"
}

teardown() {
    [[ -d "$G" ]] || return 0
    log "removing existing gadget"
    if [[ -n "$(cat "$G/UDC" 2>/dev/null || true)" ]]; then
        echo "" > "$G/UDC"
    fi
    rm -f  "$G/configs/c.1/hid.usb0"
    rmdir  "$G/configs/c.1/strings/0x409" 2>/dev/null || true
    rmdir  "$G/configs/c.1"               2>/dev/null || true
    rmdir  "$G/functions/hid.usb0"        2>/dev/null || true
    rmdir  "$G/strings/0x409"             2>/dev/null || true
    rmdir  "$G"
}

serial_number() {
    local s=""
    if [[ -r /proc/device-tree/serial-number ]]; then
        s="$(tr -d '\0' < /proc/device-tree/serial-number)"
    fi
    if [[ -z "$s" ]]; then
        s="$(awk '/^Serial/ {print $3}' /proc/cpuinfo 2>/dev/null || true)"
    fi
    echo "${s:-0000000000000001}"
}

find_udc() {
    if [[ -n "${PODSMOUSE_UDC:-}" ]]; then
        echo "$PODSMOUSE_UDC"; return
    fi
    local udc
    udc="$(ls /sys/class/udc 2>/dev/null | head -n 1 || true)"
    [[ -n "$udc" ]] || die "no USB device controller found in /sys/class/udc.
  Enable dwc2 (see gadget/README.md), reboot, and use the Pi's USB data port, not PWR."
    echo "$udc"
}

setup() {
    [[ -r "$DESC_FILE" ]] || die "descriptor not found: $DESC_FILE"

    modprobe libcomposite
    if ! mountpoint -q "$CONFIGFS"; then
        mount -t configfs none "$CONFIGFS"
    fi

    teardown

    local udc
    udc="$(find_udc)"

    log "creating gadget $GADGET_NAME"
    mkdir -p "$G"
    echo "$ID_VENDOR"  > "$G/idVendor"
    echo "$ID_PRODUCT" > "$G/idProduct"
    echo 0x0100        > "$G/bcdDevice"
    echo 0x0200        > "$G/bcdUSB"

    mkdir -p "$G/strings/0x409"
    serial_number          > "$G/strings/0x409/serialnumber"
    echo "PodsMouse"       > "$G/strings/0x409/manufacturer"
    echo "PodsMouse HID"   > "$G/strings/0x409/product"

    # HID function. subclass 0 / protocol 0 (no boot interface): the host always uses
    # our 4-byte report format instead of the 3-byte boot mouse report.
    mkdir -p "$G/functions/hid.usb0"
    echo 0                 > "$G/functions/hid.usb0/protocol"
    echo 0                 > "$G/functions/hid.usb0/subclass"
    echo "$REPORT_LENGTH"  > "$G/functions/hid.usb0/report_length"
    descriptor_bytes       > "$G/functions/hid.usb0/report_desc"

    mkdir -p "$G/configs/c.1/strings/0x409"
    echo "PodsMouse mouse" > "$G/configs/c.1/strings/0x409/configuration"
    echo 0x80              > "$G/configs/c.1/bmAttributes"   # bus powered
    echo 100               > "$G/configs/c.1/MaxPower"       # mA declared to the host
    ln -s "$G/functions/hid.usb0" "$G/configs/c.1/"

    log "binding to UDC $udc"
    echo "$udc" > "$G/UDC"

    # Wait for the device node, then fix permissions so the service runs without root.
    local i
    for i in $(seq 1 50); do
        [[ -c /dev/hidg0 ]] && break
        sleep 0.1
    done
    [[ -c /dev/hidg0 ]] || die "/dev/hidg0 did not appear after binding"

    if [[ -n "$DEV_GROUP" ]]; then
        getent group "$DEV_GROUP" >/dev/null || die "group $DEV_GROUP does not exist"
        chgrp "$DEV_GROUP" /dev/hidg0
        chmod 660 /dev/hidg0
        log "/dev/hidg0 is rw for group $DEV_GROUP"
    fi

    log "done: /dev/hidg0 is ready (host should now see 'HID-compliant mouse')"
}

[[ $EUID -eq 0 ]] || die "must run as root (sudo)"

case "$ACTION" in
    setup)  setup ;;
    remove) teardown; log "gadget removed" ;;
esac
