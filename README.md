# PodsMouse

AirPods Pro 3 som hodestyrt mus i Windows, uten driver på PC-en.

En Raspberry Pi Zero 2 W kobler seg til AirPods over Bluetooth (AACP, L2CAP PSM `0x1001`), regner om hodebevegelser til musebevegelser og vises for Windows som en vanlig USB HID-mus.

**Status:** planlegging. Fase 0 (kartlegge sensorstrømmen fra Pro 3) er ikke gjort ennå.

- Plan: [docs/plan.md](docs/plan.md)
- Instrukser for Claude Code: [CLAUDE.md](CLAUDE.md)

Bygger på [starman-tech/mousepods](https://github.com/starman-tech/mousepods) (Apache-2.0). Se [NOTICE](NOTICE).
