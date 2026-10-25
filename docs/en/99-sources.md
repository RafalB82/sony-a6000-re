# 99 — Sources and credibility

Grades: **A** = primary source (code, official documentation, file we verified),
**B** = secondary but careful, **C** = community write-up, **D** = single unverified
source — treat as hypothesis.

## A — primary

| Source | Use |
|---|---|
| Sony firmware update `Update_ILCE6000V321` / `ILCE6300V201` | everything about partitions, settings defaults, DFE, DSP |
| Sony **SERVICE MANUAL LEVEL 3** — `ILCE-6000/6000L/6000Y`, `ILCE-6300/6300L/6300M` | chip identification (`IC6200 = CXD90027GF`, `IC9012 = CXD4236-1GG`, `IC5700 = MB9AF004BGL`) |
| `ma1co/fwtool.py` | unpack/pack, crypter definitions, `devices.yml` model database |
| `ma1co/Sony-PMCA-RE` | `Backup.bin` parser, updatershell, `usbshell.cpp`, `updaterbody.cpp` |
| `ma1co/OpenMemories-Platform` | `api/backup.cpp` (property IDs), `api/tweaks.cpp` (values) |
| `ma1co/OpenMemories-Docs/hardware.rst` | SoC/DFE/codec/power-IC families, µITRON note |
| `ma1co/SA-DSP` | Ghidra processor spec for `sabin` |
| `ma1co/qemu`, `ma1co/OpenMemories-CI` | firmware emulation infrastructure |
| `erik-smit/nex-hack` | C implementation of firmware repack/encrypt |

## B — secondary, careful

- **nex-hack wiki** (`personal-view.com/faqs/sony-hack/*`, read via Wayback):
  `fwtool`, `fwencryption`, `nex6-av-cam.bin-reversing`.
  First-hand by the tool authors, but incomplete.
- **Wikipedia "Bionz"** — chip pairings per model; the article carries maintenance
  warnings and mixes naming conventions ("CXD90027GF SoC" vs OpenMemories' CXD90014).
- **iFixit teardown, Sony a7R II** — `CXD4236-1GG` identification.
- **`voxivoid/recipe-lab-sony-pmca`** — verified A6000 setting-ID map, with the
  disassembly method documented; single author but methodologically transparent.

## C — community

- LinuxGameCast / Hackaday (2022-11-25) — A5000 clean HDMI via `bk.elf w 0x01070a47 00`.
  Verified locally against A6000 defaults.
- dpreview / EOSHD / DVXuser threads — context for XAVC S, 4K overheating, firmware history.

## D — single source, unverified

- `CliffVale/sony-a6000-firmware-research` — correct dump methodology and correct
  partition *start* offsets, but: the "byte-identical" table is computed from rounded
  MB figures, the region map confuses image size with partition size, "trailing
  187.47 MB" is wrong, and CXD90014 is called Qualcomm. Use as a checklist only.
- `docodethatmatters.com` "research" post (2026-08) — self-described as "mostly
  automated researched reviewed"; mixes A6000 and A6400.

## Artefacts referenced but not redistributed here

| Artefact | Where to get it |
|---|---|
| `Update_ILCE6000V321.dmg` | Sony support (ILCE-6000 downloads, v3.21) |
| `Update_ILCE6300V201.exe` | Sony support (ILCE-6300 downloads, v2.01) |
| Service manuals (LEVEL 2 / LEVEL 3) | iFixit document archive, photo-parts.com.ua |
| PlayMemories APKs | `archive.org/download/sony-playmemories-camera-apps` |
| E-mount logic-analyser dumps | `github.com/Entropy512/sigrok-dumps`, `lens_mounts/sony_emount/` |
| OpenMemories project site | `openmemories.github.io`, `openmemories.readthedocs.io` |

## Hashes of the files this work was based on

```
Update_ILCE6000V321.dmg
  844349ff7edddc294c0fddd90a454848eeda8987b6bf043c9757982b3a42ba3e

FirmwareData_ILCE6000V321.dat
  29aef21ab9b5c2e98388974ac9749c2cbfb1815273b444e62f2e41398aa8892f

dfe/dfe.bin (from the unpacked tree)
  fc4e314db24a72d584bd8795bd8f1144b003c97c390cb143d09b840b38bf9fcd

Update_ILCE6300V201.exe
  8c850f7d5cf6b6717f2e99ca6c7ff38ecbc59745ec0ebdea1833b63f9b76d1d1
```

These hashes let anyone confirm they are looking at the same inputs.
