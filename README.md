# PodsMouse

Use AirPods Pro 3 as a head-tracking mouse on Windows, with no driver or software on the PC.

A Raspberry Pi Zero 2 W connects to the AirPods over Bluetooth (AACP, L2CAP PSM `0x1001`), turns head movement into mouse movement, and shows up on Windows as a standard USB HID mouse.

**Status:** planning. Phase 0 (mapping the AirPods Pro 3 sensor stream) has not been done yet.

- Plan: [docs/plan.md](docs/plan.md)
- Instructions for Claude Code: [CLAUDE.md](CLAUDE.md)

Builds on [starman-tech/mousepods](https://github.com/starman-tech/mousepods) (Apache-2.0). See [NOTICE](NOTICE).
