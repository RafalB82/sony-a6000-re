# 08 — Sibling models and the 4K question

The A6000 is not alone: **66 models** in `fwtool.py/devices.yml` are built on the same
CXD90014 platform. Comparing with the closest sibling, the A6300, settles the 4K
question from Sony's own schematics.

## 1. The family (selected)

| Model | Model code | PMCA API | 4K? |
|---|---|---|---|
| **ILCE-6000** | `0x41030035` | 2.4 | ❌ |
| ILCE-5100 | `0x42030036` | 2.7 | ❌ |
| ILCE-5000 | `0x41030012` | 2.3 | ❌ |
| **ILCE-6300** | `0x61030034` | 2.15 | ✅ |
| ILCE-6500 | `0x61030035` | 2.17 | ✅ |
| ILCE-7 / 7R / 7S | `0x41030013` / `0x41030034` / `0x42030032` | 2.3 / 2.3 / 2.6 | ❌ |
| ILCE-7M2 / 7RM2 / 7SM2 | `0x51030031` / `0x51030034` / `0x51030041` | 2.10 / 2.14 / 2.14 | RM2 ✅ |
| DSC-RX100M3 / M4 / M5 | `0x41020022` / `0x51020034` / `0x61020023` | 2.6 / 2.14 / 2.16 | M4/M5 ✅ |
| DSC-RX10M2 / M3, RX1RM2, RX0 | `0x51020038` / `0x61020032` / `0x51020035` / `0x61020010` | 2.14 / 2.15 / 2.14 | some ✅ |

Same SoC, different sensors and different auxiliary chips — gated per model by
configuration and by what is populated on the board.

## 2. A6000 vs A6300, from the service manuals

| | A6000 | A6300 |
|---|---|---|
| SoC package | `MHZ4G8G01A` | `MCZ4G8G21A` |
| **DFE `IC6200`** | **`CXD90027GF`** | **`CXD90027GF`** — identical |
| **Codec `IC9012`** | **absent** | **`CXD4236-1GG`** — "Beaune" |
| Power IC `IC5700` | `MB9AF004BGL` | `MB9AF004BGL` |
| Sensor | 24.3 MP | 24.2 MP, copper wiring (new part) |
| `/usr/dfe/dfe.bin` | ✅ 64 KiB | ❌ (front-end firmware is embedded in `av-cam.bin` at `0xC1EB00`) |
| `/usr/beaune/{ipl,firmware}.bin` | ❌ | ✅ 18 KB + 2.9 MB |
| `beaune_drv.ko` | ❌ | ✅ |
| DSP programs in `/usr/sabin` | 69 files | 79 files (A6000 ⊂ A6300) |
| Partition offsets | nflasha15 @ `0x08B40000` | nflasha15 @ `0x08640000` |

**4K is impossible on the A6000 because the Beaune codec chip is not on the board.**
Three independent confirmations:

1. Sony's schematic: `CXD4236` appears 14× in the A6300 manual, 0× in the A6000 manual.
2. Firmware: `/usr/beaune/` and `beaune_drv.ko` exist only in A6300.
3. Documentation: OpenMemories' hardware notes state "CXD90014 + Beaune → 4K (30 fps)".

The A6000's AV firmware still contains the 4K code path (see
[06-av-dsp-scenario.md](06-av-dsp-scenario.md)) — it simply has nothing to encode with.

## 3. Shared sensor assumptions

`dcv_psf_table_movie.bin` and `dcv_psf_table_still.bin` are **byte-identical** between
A6000 and A6300, and both are tagged `IMX210` — even though the A6300's sensor is a
different part. So the PSF tables are *processing* tables, not per-sensor calibration.
A6300 additionally ships `dcv_psf_table_movie_4k.bin` (same 10 728-byte size).

## 4. Can the A6300's newer DFE firmware run on an A6000?

A reasonable question given that the chip is the same part.

| Property | A6000 (2014) | A6300 (2015) |
|---|---|---|
| size | 65 536 B | 65 536 B |
| load base / vector layout | `0x01000000`, identical | identical |
| embedded build tag | `20140123_0000_REGULUS` | `20151222_00_1971_REGULUS` |
| reset handler | `0x01005870` | `0x0100C000` |
| strings shared | 94 of 97 | |
| MMU | no traces | `ICACHE,DCACHE and MMU Enable`, 7 CP15 ops vs 2 |
| MMIO blocks (aligned) | 18 | 22 (+`0x01013100`, `0x01014000`, `0x01014B00`, `0x01016000`, `0x01016D00`) |
| byte similarity (16-byte blocks) | Jaccard 0.178 | |

Both images target the same chip (`REGULUS`) and are drop-in compatible in size and
base address; the file lives in `/usr`, so replacing it is reversible by reflashing.

Blockers:

1. **MMU** — the 2015 build sets up an MMU; if the A6000's silicon revision differs,
   it faults before initialising anything.
2. **Five extra register blocks** — may not exist on the older revision; writes are
   either ignored or fault.
3. **Coupling with SoC code** — the A6000's `av-cam.bin` contains `SHD::Regulus` and
   `Camera::ZPD::Control`, which program Regulus registers assuming the 2014 map.
4. **Different load path** — A6300 uses `DfeCamAif` / `DFE Acquire`, not a file load.

Expected outcome: camera boots but may not initialise the sensor or AF. Brick risk is
low because the file is in `/usr`.

**Before trying:** establish whether the A6000 boots the DFE from `/usr/dfe/dfe.bin` or
from the copy embedded in `av-cam.bin` at `0xA67F00`. A cheap A/B test decides it:
replace `/usr/dfe/dfe.bin` with a deliberately broken copy (and fix the CRC32); if the
camera behaves identically, the embedded copy is what matters.

## 5. What does not transfer

- Partition layout differs (nflasha3 is 30 MiB on A6000 vs 20 MiB on A6300, nflasha15
  and nflasha17 are shifted), so whole images are not interchangeable.
- `av-cam.bin` differs in size (11.4 MB vs 13.4 MB) and content.
- The DSP set differs (A6000 is a strict subset).
