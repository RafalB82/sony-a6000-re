# 01 — Hardware

Everything here comes from Sony's own *SERVICE MANUAL LEVEL 3* for both cameras
(`ILCE-6000` and `ILCE-6300`) and from strings inside the firmware. No teardown
photos were needed.

## Chip inventory (A6000)

| Role | Board ref | Part | Notes |
|---|---|---|---|
| SoC ("BIONZ X") | `IC6000` | package `MHZ4G8G01A` = **CXD90014** | 4× ARM Cortex-A5, runs Linux + µITRON |
| **DFE (front-end)** | **`IC6200`** | **`CXD90027GF`** — "CAMERA SIGNAL PROCESS" | 4 schematic sheets; marked "not supplied" as spare |
| Power IC | `IC5700` | `MB9AF004BGL` ("Darwin", Cortex-M3) | boots the SoC, manages RTC |
| Misc | — | `CXD9950AK` ×2 | role not established |

Image sensor: **IMX210** — the firmware contains the driver classes
`C_ImagerCtrl_IMX210E` and `ImagerDrvParam_IMX210E` in `av-cam.bin` (the AV firmware).

> A widely repeated claim that CXD90014 is a *Qualcomm* part is wrong. `CXD` is Sony's
> prefix; OpenMemories' hardware notes list CXD90014 as Sony's own "BIONZ X",
> 4× Cortex-A5, codename *Musashi / Kojiro?*.

## A6300 next to it

| Role | Board ref | A6000 | A6300 |
|---|---|---|---|
| SoC | `IC6000` | `MHZ4G8G01A` | `MCZ4G8G21A` (newer package) |
| **DFE** | `IC6200` | **`CXD90027GF`** | **`CXD90027GF`** — *same part* |
| Codec ("Beaune") | `IC9012` | **absent** | **`CXD4236-1GG`** (13 schematic sheets) |
| Power IC | `IC5700` | `MB9AF004BGL` | `MB9AF004BGL` |

This single table explains the whole 4K question — see
[08-sibling-models.md](08-sibling-models.md).

## What runs where

```
sensor ──► DFE CXD90027GF ──► SoC CXD90014 ──► (A6300 only: codec CXD4236 "Beaune")
              ARM MCU           4× Cortex-A5         MIPS, eSOL eBinder
              dfe.bin           Linux + µITRON        beaune/ipl.bin + firmware.bin
                                + Android userland
```

- The **DFE** owns sensor readout: phase-detect AF data (ZPD), defect correction
  (DFECAM0–5), timing generation (SSG) and the link to the SoC (DFELINK).
  Details: [05-dfe.md](05-dfe.md).
- The **SoC** runs two worlds at once: a Linux userland (with the Android 2.3.7
  userland that hosts PlayMemories apps) and a real-time OS for the AV pipeline.
- The **codec chip** (Beaune) is optional; only models with it can encode 4K.

## Storage

NAND is a single device of **463.75 MiB** (`0x00000000`–`0x1BAC0000`), split into
15 partitions with no gaps. Table and details: [02-firmware-layout.md](02-firmware-layout.md).

## Sources for this document

- Sony `ILCE-6000/6000L/6000Y` SERVICE MANUAL LEVEL 3 (5 sheets) — chip references above.
- Sony `ILCE-6300/6300L/6300M` SERVICE MANUAL LEVEL 3 (65 pages) — comparison.
- `ma1co/OpenMemories-Docs` → `hardware.rst` — SoC/DFE/codec families, µITRON note.
- Firmware strings: `C_ImagerCtrl_IMX210E`, `SHD::Regulus`, `Hello Regulus`.
