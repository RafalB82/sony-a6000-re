# Sony A6000 (ILCE-6000) — reverse-engineering notes

**Bilingual repository: [English](README.md) · [Polski](README.pl.md)**

Static-analysis notes on a 2014 Sony A6000: what is inside the firmware, what can be
changed, and what the hardware does not allow. Everything here was derived from
**files** — Sony firmware update packages, Sony service manuals, and the open-source
tooling from the *nex-hack* and *OpenMemories* projects.

> **Scope and disclaimer.** Documentation only. No Sony binaries, no firmware dumps,
> no personal data are published here. Nothing in this repository was validated on
> physical hardware by the author; statements are either *verified from files*
> (marked as such) or clearly flagged as hypotheses. Following anything here can
> damage your camera. **You break it, you keep both pieces.**

---

## What this is

A structured knowledge base about the ILCE-6000 platform:

| # | Document | What it answers |
|---|---|---|
| 01 | [Hardware](docs/en/01-hardware.md) | Which chips are on the board (confirmed by Sony service manuals) |
| 02 | [Firmware layout](docs/en/02-firmware-layout.md) | Real partition table, NAND map, what each partition holds |
| 03 | [Integrity and flashing](docs/en/03-integrity-and-flashing.md) | CRC32 manifests, no signatures, what can be rebuilt and flashed |
| 04 | [Settings store](docs/en/04-settings-store.md) | `Backup.bin`, known property IDs, the 11 per-region defaults |
| 05 | [DFE](docs/en/05-dfe.md) | The front-end MCU: firmware, register map, phase-detect AF, log channel |
| 06 | [AV DSP and scenarios](docs/en/06-av-dsp-scenario.md) | `sabin` programs, encoder variants, plug-in scenarios |
| 07 | [Lens](docs/en/07-lens.md) | Lens control layers, E-mount wire protocol, why manual lenses get no AF |
| 08 | [Sibling models](docs/en/08-sibling-models.md) | The 66 CXD90014 models, A6000 vs A6300, why 4K is impossible |
| 09 | [Prior art](docs/en/09-prior-art.md) | Who already walked this path, and where they stopped |
| 10 | [Open questions](docs/en/10-open-questions.md) | What is still unknown and how to attack it |
| — | [Sources](docs/en/99-sources.md) | References with a credibility grade per source |

Polish originals (working notes, longer and messier) live in
[`docs/pl/raw/`](docs/pl/raw/) and are the source material for both language sets.

## Key findings in one screen

| Finding | Evidence class |
|---|---|
| **No cryptographic signatures on CXD90014 firmware.** Integrity is CRC32 in `*.sum` manifests, recomputable by anyone | verified — recomputed all manifests |
| **A modified firmware can be repacked byte-identically.** `fwtool.py unpack` → `pack` reproduces Sony's file with the same SHA-256 | verified — `29aef21a…892f` |
| The real partition table is shipped **inside** the firmware (`0300_partconf/partinf.conf`); NAND is 463.75 MiB, 15 partitions, no gaps | verified |
| Only `nflasha3/5/7/15/16` are ever rewritten by an update. User data (`nflasha17`) and settings (`nflasha2`) survive | verified |
| The updater checks **only** CRC32 + main/sub LSI type + NAND capacity. No authorship, no version check | verified from update scripts |
| The firmware ships **11 complete `Backup.bin` files, one per region** → all 16 102 properties are available offline | verified |
| **DFE (`CXD90027GF`) is a real ARM MCU** with 83 procedures doing phase-detect AF (ZPD), defect correction (DFECAM0–5) and sensor timing (SSG) | verified — Ghidra 12.1.4 |
| DFE log output goes to a **RAM buffer at `0x0102D000`**, not a UART | verified |
| **4K is impossible on A6000** — the Beaune codec (`CXD4236`) is only on A6300's board | verified — service manuals + firmware |
| A6000 and A6300 share the **same DFE part** (`IC6200 = CXD90027GF`); only the firmware generation differs (2014 vs 2015) | verified — service manuals |
| Focus confirmation with a dumb manual lens is unreachable: the body gates AF on a capability message (`NID_LENS_INFORMATION`) sent by the lens | verified — strings in `libObj.so` |

## Repository contents

```
docs/en/            English documents (01–10, 99)
docs/pl/            Polish translations of the same set
docs/pl/raw/        original Polish working notes (source material)
tools/backup.py     CLI for Backup.bin: info / list / get / known / diff
tools/apply-dfe-names.py   Ghidra script that reproduces the DFE symbol names
data/dfe-names.txt  83 named procedures of dfe.bin
references/         machine-readable source list
```

## What is deliberately **not** here

- Sony firmware images, decrypted or otherwise
- NAND dumps (they contain device-specific and personal data)
- Service manual PDFs (third-party distribution; links are given instead)
- Extracted `dfe.bin`, `av-cam.bin`, `sabin` programs

All of those are reproducible from Sony's public update files with the tools listed
in [`99-sources.md`](docs/en/99-sources.md).

## Reproducing from scratch

```bash
# 1. Get an official updater (link in 99-sources.md), then:
pip install pycryptodomex pyyaml
git clone https://github.com/ma1co/fwtool.py
python fwtool.py/fwtool.py unpack -f FirmwareData_ILCE6000V321.dat -o fw

# 2. Settings store
python tools/backup.py info fw/firmware.tar_unpacked/0110_backup/SYSMUSASHI-DSLR/DM_UUD3/CX77500_ALLLANG.bin
python tools/backup.py known fw/firmware.tar_unpacked/0110_backup/SYSMUSASHI-DSLR/DM_UUD3/CX77500_ALLLANG.bin

# 3. DFE firmware (Ghidra): raw binary, ARM LE v7, base 0x01000000
#    then run tools/apply-dfe-names.py
```

## License

Documentation and scripts: MIT (see [LICENSE](LICENSE)).
Firmware, service manuals, and third-party tools remain the property of their
respective owners and are not redistributed here.
