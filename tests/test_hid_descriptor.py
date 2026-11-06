"""Checks that gadget/hid-mouse.desc describes the 4-byte mouse report HidSink writes.

Runs without hardware: it parses the descriptor's short items the way a USB host would
and checks the resulting input report layout.
"""

import pathlib
import unittest

DESC_PATH = pathlib.Path(__file__).resolve().parent.parent / "gadget" / "hid-mouse.desc"

# HID short item tags (bTag | bType), size bits masked off.
INPUT = 0x80
COLLECTION = 0xA0
END_COLLECTION = 0xC0
USAGE_PAGE = 0x04
LOGICAL_MIN = 0x14
LOGICAL_MAX = 0x24
REPORT_SIZE = 0x74
REPORT_ID = 0x84
REPORT_COUNT = 0x94
USAGE = 0x08
USAGE_MIN = 0x18
USAGE_MAX = 0x28

GENERIC_DESKTOP = 0x01
BUTTON = 0x09
X, Y, WHEEL = 0x30, 0x31, 0x38


def load_descriptor(path=DESC_PATH):
    """Strip comments and whitespace, return the descriptor as bytes (same rules as the script)."""
    hex_digits = "".join(line.split("#", 1)[0] for line in path.read_text().splitlines())
    hex_digits = "".join(hex_digits.split())
    return bytes.fromhex(hex_digits)


def parse_items(desc):
    """Yield (tag, data, raw_value) for each short item."""
    i = 0
    while i < len(desc):
        prefix = desc[i]
        size = {0: 0, 1: 1, 2: 2, 3: 4}[prefix & 0x03]
        tag = prefix & 0xFC
        data = desc[i + 1 : i + 1 + size]
        if len(data) != size:
            raise ValueError(f"truncated item at offset {i}")
        yield tag, data
        i += 1 + size


def signed(data):
    return int.from_bytes(data, "little", signed=True) if data else 0


def unsigned(data):
    return int.from_bytes(data, "little", signed=False) if data else 0


def input_fields(desc):
    """Return the input fields in report order as dicts, and the final collection depth."""
    globals_ = {"page": 0, "lmin": 0, "lmax": 0, "size": 0, "count": 0}
    usages = []
    fields = []
    depth = 0
    for tag, data in parse_items(desc):
        if tag == USAGE_PAGE:
            globals_["page"] = unsigned(data)
        elif tag == LOGICAL_MIN:
            globals_["lmin"] = signed(data)
        elif tag == LOGICAL_MAX:
            globals_["lmax"] = signed(data)
        elif tag == REPORT_SIZE:
            globals_["size"] = unsigned(data)
        elif tag == REPORT_COUNT:
            globals_["count"] = unsigned(data)
        elif tag == REPORT_ID:
            raise AssertionError("descriptor must not use report IDs")
        elif tag == USAGE:
            usages.append((globals_["page"], unsigned(data)))
        elif tag == USAGE_MIN:
            umin = unsigned(data)
        elif tag == USAGE_MAX:
            usages.extend((globals_["page"], u) for u in range(umin, unsigned(data) + 1))
        elif tag == COLLECTION:
            depth += 1
            usages = []
        elif tag == END_COLLECTION:
            depth -= 1
        elif tag == INPUT:
            flags = unsigned(data)
            fields.append(
                {
                    "constant": bool(flags & 0x01),
                    "relative": bool(flags & 0x04),
                    "size": globals_["size"],
                    "count": globals_["count"],
                    "lmin": globals_["lmin"],
                    "lmax": globals_["lmax"],
                    "usages": usages,
                }
            )
            usages = []
    return fields, depth


class HidDescriptorTest(unittest.TestCase):
    def setUp(self):
        self.desc = load_descriptor()
        self.fields, self.depth = input_fields(self.desc)

    def test_collections_are_balanced(self):
        self.assertEqual(self.depth, 0)

    def test_report_is_four_bytes(self):
        bits = sum(f["size"] * f["count"] for f in self.fields)
        self.assertEqual(bits, 32)

    def test_byte0_is_three_buttons_and_padding(self):
        buttons, padding = self.fields[0], self.fields[1]
        self.assertEqual(buttons["usages"], [(BUTTON, 1), (BUTTON, 2), (BUTTON, 3)])
        self.assertEqual((buttons["size"], buttons["count"]), (1, 3))
        self.assertFalse(buttons["relative"])
        self.assertTrue(padding["constant"])
        self.assertEqual(padding["size"] * padding["count"], 5)

    def test_bytes1_to_3_are_relative_x_y_wheel(self):
        axes = self.fields[2]
        self.assertEqual(
            axes["usages"], [(GENERIC_DESKTOP, X), (GENERIC_DESKTOP, Y), (GENERIC_DESKTOP, WHEEL)]
        )
        self.assertEqual((axes["size"], axes["count"]), (8, 3))
        self.assertTrue(axes["relative"])
        self.assertEqual((axes["lmin"], axes["lmax"]), (-127, 127))

    def test_no_other_input_fields(self):
        self.assertEqual(len(self.fields), 3)


if __name__ == "__main__":
    unittest.main()
