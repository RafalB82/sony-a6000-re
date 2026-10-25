# 10 — Open questions and method

## 1. Open questions, ordered by value

1. **`BKID_*` name → numeric ID.** The firmware contains 1058 distinct `BKID_*` names
   (786 in `libmprctrl.so`), but nobody has published the mapping. Decoding it would
   name thousands of the 16 102 `Backup.bin` properties. Method: disassemble
   `libmprctrl.so` around `Backup_read` and the descriptor tables. A first attempt by
   pointer-scanning produced 1430 candidates but **none of the known IDs**, i.e. noise —
   the table layout is different.
2. **Which DFE image the SoC uploads** — `/usr/dfe/dfe.bin` or the copy embedded in
   `av-cam.bin` at `0xA67F00`. Decidable by an A/B test, and it gates the whole
   "swap in A6300's newer DFE firmware" experiment.
3. **Which AVC encoder variant the A6000 uses** (`performance` / `quality` /
   `performance_plus`), and whether the others improve image quality.
4. **How to read the DFE log buffer** (`0x0102D000`) from the SoC side — would give live
   visibility into sensor initialisation.
5. **What the remaining ~16 000 properties do.**
6. **Whether the DFE's `SSG`/`DFECAM` blocks expose unused sensor readout modes**
   (binning, line-skipping, alternative windows). This is the one place such modes
   could live.
7. **Command IDs of the E-mount lens protocol** — needed to build a lens emulator.
8. **Emulating the A6000 in QEMU** so that firmware experiments need no hardware
   (ma1co's fork already emulates five other bodies).

## 2. Method used

Everything here came from static analysis of files:

| Source | What was done with it |
|---|---|
| Official Sony updater (`Update_ILCE6000V321.dmg`) | unpacked with `fwtool.py` (crypter CXD90014) |
| A6300 updater (`Update_ILCE6300V201.exe`) | unpacked for comparison |
| Sony service manuals (LEVEL 3, both models) | chip identification from schematics |
| `Backup.bin` defaults (11 files) | parsed with Sony-PMCA-RE's parser |
| `dfe.bin` | Ghidra 12.1.4 via REA, ARM LE v7 @ `0x01000000` |
| `av-cam.bin`, libs, `.so` | string analysis, RTTI, literal-pool scanning, `capstone` |
| Public repositories | read, not copied (licences respected) |

Verification style used throughout: recompute a checksum rather than trust a number;
compare two models rather than trust a table; mark each claim as verified, inferred or
hypothesis.

## 3. What was **not** done

- No experiment on physical hardware. Every "works" in these documents means
  "implemented and publicly reported", not "verified by the author".
- No modified firmware was flashed.
- No lens protocol was captured or replayed.
- No emulation was attempted.

## 4. Claims corrected during the work

Recorded so that future readers can calibrate:

1. "Qualcomm CXD90014" — wrong; it is Sony's own BIONZ X, 4× Cortex-A5.
2. "A6300 has no DFE firmware" — incomplete; it is embedded in `av-cam.bin`.
3. "A6000 and A6300 share the same sensor" — overstated; the PSF tables are identical
   but the sensors are different parts, so the tables are processing tables.
4. "A6000 uses only the `performance` encoder variant, the others are dead" — based on
   a byte-pattern match that straddled two adjacent 32-bit table entries. Not
   established at all.

## 5. If you want to continue

Suggested order, cheapest first, all requiring the camera plus a fully charged battery:

1. Install OpenMemories-Tweak, enable Wi-Fi + telnet, confirm root shell.
2. `bk.elf w 0x01070a47 00` (or the Tweak equivalent) for clean HDMI — reversible.
3. Run `scenario.elf` with `MPR_SCN_GET_TOTAL_LOG.so` — read-only, proves the harness.
4. A/B test on `/usr/dfe/dfe.bin` to learn whether the file is used at all.
5. Only then consider swapping in the A6300 DFE firmware, and only with a recovery plan.
