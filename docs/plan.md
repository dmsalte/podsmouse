# PodsMouse – plan for AirPods Pro 3 som mus i Windows

Sist oppdatert: 2026-11-06

## Mål og avgrensning

Målet er at AirPods Pro 3 styrer musepekeren på en vanlig Windows-PC. Windows skal ikke trenge noen driver eller programvare. En Raspberry Pi Zero 2 W gjør jobben som Bluetooth-bro og dukker opp som en vanlig USB-mus. Utgangspunktet er [mousepods](https://github.com/starman-tech/mousepods) (Apache-2.0).

**Leveres**

- Bekreftet sensorstrøm fra AirPods Pro 3 med dokumentert pakkeformat
- Musemodus der hodebevegelse flytter pekeren, med rekalibrering
- Klikk ved trykk på stilken, hodenikk eller dwell (pekeren hviler en stund)
- Pi-en vises som USB HID-mus, slik at Windows trenger null installasjon
- Enkelt webgrensesnitt på Pi-en for batteri, kalibrering og rådata

**Utenfor første versjon**

- Lyd via Pi-en (USB-lydkort). Vurderes i fase 5.
- Pointer- og Glide-modus fra mousepods
- Andre AirPods-modeller enn Pro 3 (Pro 2 og AirPods 3 bør likevel virke)
- Egen Windows-driver eller tjeneste

## Hvorfor en Pi-bro

Windows har ikke noe API i brukermodus for egne Bluetooth Classic L2CAP-kanaler. AirPods sender sensordata over AACP på PSM `0x1001`, og den kanalen kan bare åpnes av en profildriver i kjernemodus, slik MagicPods gjør. En Pi med BlueZ har ikke den begrensningen.

## Arkitektur

```
AirPods Pro 3 ──Bluetooth Classic, L2CAP PSM 0x1001──▶ Raspberry Pi Zero 2 W ──USB, HID-mus──▶ Windows-PC
                                                       │
                                                       ├─ AAPClient     åpner AACP-kanalen, leser sensorpakker
                                                       ├─ MotionEngine  gravitasjon og gyro blir yaw og pitch
                                                       ├─ Controller    glatting, akselerasjon, klikk, 120 Hz
                                                       └─ HidSink (ny)  4-byte rapporter til /dev/hidg0
```

Det eneste som må skrives nytt i hovedløpet er `HidSink`, som erstatter `/dev/uinput`. Windows ser Pi-en som en standard HID-mus og bruker den innebygde driveren. Derfor fungerer det også på låste maskiner der du ikke kan installere noe.

## Maskinvare og innkjøp

| Del | Hvorfor | Merknad |
| --- | --- | --- |
| Raspberry Pi Zero 2 W | Bluetooth og USB OTG på ett kort | Velg gjerne en versjon med loddede pinner |
| microSD 16–32 GB | Raspberry Pi OS Lite (Bookworm, 64-bit) | A1/A2-klasse |
| Micro-USB-datakabel til USB-A/C | Gir strøm og HID-forbindelse til PC-en | Må være en datakabel, ikke bare ladekabel. Bruk *USB*-porten, ikke *PWR* |
| Enkelt kabinett | Beskytter kortet på pulten | Valgfritt |
| (Fase 0) Linux-PC eller laptop med Bluetooth | Kartlegge Pro 3 før Pi-en er på plass | Live-USB med Ubuntu holder |

## Faser

Fase 0 er den viktigste. Den avgjør om Pro 3 i det hele tatt gir sensordata utenfor Apple-økosystemet, og den kan gjøres på en hvilken som helst Linux-maskin med Bluetooth før Pi-en er kjøpt. Hver fase er ferdig først når akseptkriteriet er oppfylt på ekte maskinvare.

| Fase | Innhold | Akseptkriterium | Trenger Pi |
| --- | --- | --- | --- |
| 0. Kartlegging av Pro 3 | Kjør mousepods `--diag` og sensorutforskeren mot Pro 3. Lagre råfangster i `captures/pro3/`. Finn ut om Pro 3 bruker SensorDataWX som Pro 2, eller noe nytt. | Stabil strøm med kjent frekvens (Hz) i minst 10 min. Akser identifisert. | Nei |
| 1. Pi-oppsett | Pi OS Lite, BlueZ, PSM 0x1001 tillatt, MTU 2582, paring med Pro 3 | `--diag` gir samme strøm på Pi-en som i fase 0 | Ja |
| 2. USB HID-gadget | configfs-gadget med relativ mus (knapper, X/Y, hjul). Et testskript som tegner en firkant. | Windows ser «HID-compliant mouse» uten driver, og pekeren tegner firkanten | Ja |
| 3. Kobling | Bytt mousepods sin `uinput`-utgang mot en `HidSink` som skriver til `/dev/hidg0` | Hodebevegelse flytter pekeren i Windows med under 30 ms forsinkelse | Ja |
| 4. Brukbarhet | Kalibrering, rekalibrering, klikk, pause og autostart som systemd-tjeneste | 15 min vanlig bruk (åpne apper, klikke knapper) uten at du må ta i musa | Ja |
| 5. Valgfritt | USB-lydkort via Pi-en (A2DP til AirPods) og Pointer-modus | Lyd og styring samtidig over én kabel | Ja |

## Repostruktur og gjenbruk

Repoet bygger på mousepods, slik at protokollkoden og testene følger med. Den nye koden holdes i egne moduler, slik at det er enkelt å hente inn endringer fra upstream. `LICENSE` og `NOTICE` fra upstream må beholdes uendret. Alt fra upstream `docs/` og `captures/` (CC BY 4.0) som brukes, må krediteres.

```
podsmouse/
├── CLAUDE.md                 # instrukser for Claude Code
├── upstream/                 # mousepods som git subtree, ikke rediger her
├── podsmouse/
│   ├── sinks/
│   │   ├── base.py           # Sink-grensesnitt: move(dx,dy), button(b,down), scroll(n)
│   │   ├── hid_gadget.py     # skriver 4-byte rapporter til /dev/hidg0
│   │   └── null.py           # for tester og --dry-run
│   ├── models/pro3.py        # Pro 3-spesifikk parsing hvis fase 0 krever det
│   └── main.py               # starter AAPClient → MotionEngine → Controller → Sink
├── gadget/
│   ├── setup-hid-gadget.sh   # configfs: VID/PID, HID-deskriptor, UDC-binding
│   └── hid-mouse.desc        # rapportdeskriptor (relativ mus, 3 knapper, hjul)
├── systemd/
│   ├── podsmouse-gadget.service
│   └── podsmouse.service
├── captures/pro3/            # råfangster fra fase 0
├── docs/pro3-findings.md     # pakkeformat, akser og frekvens for Pro 3
└── tests/                    # upstream-testene + tester av sinks og Pro 3-parser
```

**Gjenbrukes direkte:** `AAPClient`, `MotionEngine` (gravitasjon og gyro-bias), One-Euro-glatting, webgrensesnittet og de 37 testene som ikke krever maskinvare.

**Byttes ut:** utgangen til `/dev/uinput` erstattes av `HidSink`. Hurtigtaster på Linux-skrivebordet erstattes av stilk-gester og knapper i webgrensesnittet, siden Pi-en ikke har tastatur.

## Risikoer og åpne spørsmål

Den største risikoen er at Pro 3 ikke gir sensordata eller krever en ukjent startpakke. Det avklares i fase 0 før det brukes penger på Pi.

| Risiko | Konsekvens | Tiltak |
| --- | --- | --- |
| Pro 3 bruker et nytt eller låst sensorformat | Prosjektet stopper i fase 0 | Prøv begge kjente startpakker (som HT_START i pods-head-tracker), sammenlign med Pro 2-fangster, og spør i LibrePods-Discord |
| Lav frekvens (≈25 Hz som Pro 2) | Pekeren føles hakkete | Kjør HID på 120 Hz med prediksjon/interpolering. Juster One-Euro. |
| AirPods kobles bare til én vert om gangen | Ingen lyd på PC-en mens Pi-en har AirPods | Godta det i v1, og løs det med USB-lyd via Pi-en i fase 5 |
| Firmware-oppdatering fra Apple endrer protokollen | Sensorstrømmen stopper | Lagre fangster per firmware og logg versjonen ved oppkobling |
| Pi Zero 2 W blir for svak | Forsinkelse eller tap av pakker | Mål CPU-bruk i fase 3. Pi 4 er reserve. |

**Åpne spørsmål**

- Hvilken firmware har Pro 3-ene, og er de paret med en iPhone som kan oppdatere dem?
- Hvilken klikkmetode skal være standard: trykk på stilken, hodenikk eller dwell?

## Kilder

- [starman-tech/mousepods](https://github.com/starman-tech/mousepods)
- [pods-head-tracker (Pi-bro for OpenTrack)](https://github.com/batubozkan/pods-head-tracker/releases)
- [sony-head-tracker wiki: hvorfor AirPods ikke fungerer direkte på Windows](https://github.com/NicholasSlattery/sony-head-tracker/wiki)
- [LibrePods discussion #259](https://github.com/librepods-org/librepods/discussions/259)
