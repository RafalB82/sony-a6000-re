# 09 — Prior art

Who already walked this path, how far they got, and where the last mile was never
walked.

## 1. nex-hack (2012–2014) — the enabling work

Documentation lives on `personal-view.com/faqs/sony-hack/*` (a DokuWiki, still readable
through the Wayback Machine). Authors: oz_paulb, kenan, Vitaliy Kiselev.

| Achievement | Detail |
|---|---|
| Firmware decryption | generation 1 = SHA1, generation 2 = AES |
| **Repack + re-encrypt** | `fwtool -c` re-encrypts `FDAT.dec` → `FDAT.reenc` and rebuilds `FirmwareData_NexHack.dat`: "*This is a valid firmware update file and running FirmwareUpdater.exe will update the device*" |
| v06final | "Complete Repack from level3 to loadable firmware update file" |
| **Never finished** | `-m Modify firmware (not implemented yet)`; v0.8 (cramfs/fatfs) never shipped |
| `av-cam.bin` | NEX-6: identified as **ARM code on T-Kernel RTOS**, mostly JPEG/video; IDA script plus a note about switching between ARM32 and Thumb16; rebased to `0xC3421000` for NEX-5N |
| Code | `erik-smit/nex-hack` (C: `fwt_util.c`, `fdat_cipher_aes.c`, `fdat_cipher_sha1.c`), `steelcnn/nex-hack` (IDA `.idc`) |

**This is the key point:** the concept "modified Sony firmware flashed by the official
updater" was demonstrated as feasible a decade ago. There is no trace of anyone
actually putting a modified image onto a camera.

## 2. ma1co (2015–2024) — the living project

| Repository | What it gives | Relevance |
|---|---|---|
| **fwtool.py** | unpack **and pack**, CXD90014 supported | the tool that makes repacking possible |
| **Sony-PMCA-RE** | USB: app install, `updatershell`, `serviceshell` | camera access |
| **OpenMemories-Tweak** | edits `Backup.bin` | settings layer |
| **OpenMemories-Platform** | native C/C++ on the camera (backup, tweaks, usbcmd) | base for custom payloads |
| **OpenMemories-Framework** | SDK for PMCA apps (322 `com.sony.*` classes) | app layer |
| **SA-DSP** | **Ghidra processor spec that decompiles `sabin`** (2021) | key to the DSP programs |
| **qemu** | QEMU fork for BIONZ | emulation |
| **OpenMemories-CI** | emulates cameras in QEMU on GitHub Actions (NEX-3, RX100M5, HX99, QX10, W90) | testing without hardware |
| **OpenMemories-Symbols** | `bin2elf.py` + symbol database for 11 **old** models | method, but no A6000 |

## 3. Community — settings and single-property hacks

- **A5000 clean HDMI**: `bk.elf w 0x01070a47 00` (LinuxGameCast / Hackaday, 2022-11).
  Verified here against the A6000 defaults: the property exists, `attr=0x40`, default
  `01` — so the trick should apply to the A6000 too.
- **OpenMemories-Tweak**: recording limit, languages, NTSC nag.
- **`voxivoid/recipe-lab-sony-pmca`** — actively maintained app for A6000/A6300/A6500/
  A5100/A7 II/A7S II. Its `docs/DEVELOPMENT.md` publishes the **first verified map of
  A6000 setting IDs**, obtained by "disassembling the camera app's parameter
  registration in `libObj.so`" — the same file that contains 786 `BKID_*` names.
- **PlayMemories Camera Apps** died on 2025-08-31; APKs are preserved on the Internet
  Archive and can still be installed with `pmca-console install`.

## 4. Analogues from other brands

- **Canon — Magic Lantern**: large-scale firmware augmentation; a proven model.
- **Panasonic — PTool** (by the same Vitaliy Kiselev): patches **bitrate and encoding
  parameters** in compact-camera firmware — exactly the class of change contemplated
  here for the ZIMA encoders.

So "change encoder parameters in camera firmware" has been done elsewhere. For Sony,
it has not.

## 5. What nobody has done publicly

| Topic | Status |
|---|---|
| **Flashing a modified partition image onto a real camera** | **no public report** — the last mile |
| Which AVC encoder variant the A6000 uses | unknown |
| Any analysis of `sabin` programs beyond the Ghidra spec | none |
| `/usr/scenario` plug-ins (35 `.so` + `scenario.elf`) | zero published work |
| `BKID_*` name → numeric ID table (1058 names exist in the binaries) | no public mapping |
| `dfe.bin` analysis | none before this work |
| Emulating the A6000 in QEMU | not done (other models are) |

## 6. Claims that turned out to be wrong

- `CliffVale/sony-a6000-firmware-research` — real dump methodology and correct
  partition start offsets, but its "byte-identical verification" table is computed from
  rounded megabyte figures rather than measured, its region map conflates image size
  with partition size, its "trailing 187.47 MB" is wrong, and it calls CXD90014 a
  Qualcomm part. Useful as a checklist, not as a source of facts.
- "A6300 has no DFE firmware" — incomplete: it has one, embedded in `av-cam.bin`.
