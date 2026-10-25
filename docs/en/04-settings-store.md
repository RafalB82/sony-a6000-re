# 04 — Settings store: `Backup.bin`

All of Sony's hidden settings live in one file on `nflasha2` (`/setting/Backup.bin`).
The camera's own service API reads and writes it — that is what *OpenMemories: Tweak*
does. This document covers the format, the IDs that are known, and an offline corpus
of 11 complete files shipped inside the firmware.

## 1. File format (revision `BK4`)

```
offset  field
0x00    magic (int32)
0x04    cookie (int32)
0x08    writeComp (int32)
0x0c    revision      — "BK2" or "BK4"            ← format version
0x10    numSubsystems
0x14    numProperties
0x18    dataOffset
0x1c    dataSize
0x20    checksum      (sum of bytes, excluding 0x20..0x23)
0x28    id1 (int32)   — protection flag
0x3c    version (0x20)
0xc0    region (0x20) — e.g. "CX77500_ALLLANG", "CX77500_J1"
```

- `BK2` → property table entries carry an **int8** `attr`
- `BK4` → **int16** `attr`
- Property ID = `subsystem << 16 | index`; `attr` bit 0 = read-only,
  bit 1 = protected from `Backup_protect`.

The parser used here is `pmca/backup/__init__.py` from Sony-PMCA-RE; the CLI in
`tools/backup.py` wraps it.

## 2. An offline corpus: 11 complete files per region

`0110_backup/SYSMUSASHI-DSLR/DM_UUD3/` (A6000) contains one file per region, each
852 647 bytes:

```
CX77500_ALLLANG  CX77500_E38  CX77500_J1  CX77500_KR2  CX77500_UC2
CX77501_ALLLANG  CX77501_AP2  CX77501_CEC  CX77501_CN2  CX77501_IN5  CX77501_JE3
```

Verified with the parser: `BK4`, `numSubsystems=403`, `numProperties=17167`
(16 102 actually present), `dataOffset=0x19ce0`, `dataSize=0xb65c7`.

**This means every property ID and its default value is available without a camera.**
Region files differ in only **37–46 properties** (ALLLANG vs J1: 37), so most of the
"regionality" is a handful of IDs.

Example values from `CX77500_ALLLANG.bin`:

```
0x003e0005 model_name      = "ILCE-6000"
0x003c0373 rec_limit H     = 0x00
0x003c0374 rec_limit M     = 0x1d      → 0h 29m 50s
0x003c0375 rec_limit S     = 0x32
0x010d008f..b1 language    = 0x01 (enabled) in all 35 slots
0x01070148 pal_ntsc        = 0x00
```

## 3. Known IDs

From `ma1co/OpenMemories-Platform/api/backup.cpp`:

| ID | Size | Meaning |
|---|---|---|
| `0x003c0373` / `74` / `75` | 1 B each | recording limit H / M / S |
| `0x003c04b6` | 2 B | 4K recording limit (RX100M4), seconds |
| `0x003e0005` | 16 B | model name |
| `0x00e70000` | 5 B | model code |
| `0x00e70003` | 4 B | serial number |
| `0x01070148` | 1 B | PAL/NTSC selector |
| `0x010d008f` … `0x010d00b1` | 1 B × 35 | language slots (1 = on, 2 = off) |
| `0x01640001` | 1 B | USB app installer |
| `0x01660024` | 8 B | Android platform version |

From the community (verified by menu diff, see `voxivoid/recipe-lab-sony-pmca`):

| Setting | ID |
|---|---|
| Creative Style | `0x01070175` (1 standard, 2 vivid, 3 neutral, 6 mono, 14 sepia) |
| Contrast / Saturation / Sharpness | `0x01070178` / `0x01070187` / `0x0107018a` |
| Picture Profile no. | `0x0107031c` |
| WB mode / Kelvin / A-B / G-M | `0x01070019` / `0x01070018` / `0x01070017` / `0x01070016` |
| WB per-mode copies | AWB `0x0107067f`/`0x0107067e`, colour temp `0x01070683`/`0x01070682` |
| Picture Effect | `0x010706f1` (+ `0x010709d8`, `0x010706f3`, `0x010706ee`, `0x010706ef`) |
| Exposure bias | `0x010700b8` + copy `0x01070c7f` |
| DRO | `0x01070104` + level `0x01070775` |
| Quality: format / JPEG level | `0x01070013` (+`0x01070aa9`) / `0x01070014` (+`0x01070aaa`) |
| **HDMI overlay (clean HDMI)** | **`0x01070a47`** — `01` = overlay on, `00` = clean |

The clean-HDMI ID came from a community write-up about the A5000
(`bk.elf w 0x01070a47 00`). It was verified locally: the property exists in the
A6000 defaults, `attr=0x40`, size 1, value `01`.

## 4. Protection

`is_enabled() == !Backup_get_protection()`, and the protection flag is `id1` at 0x28,
written through a dedicated camera command (`backup_senser_cmd_ID1`), not through the
normal property write path.

Details worth knowing (from the platform source):

- On Android 2 the `/setting` directory must exist for the flag to stick; OpenMemories
  creates it, writes `Backup.bin`, then removes the directory again.
- Region `J1` (Japan) can only *enable* protection, not disable it. The workaround
  temporarily patches the region field to `""` via `Backup_protect`, flips the flag,
  and restores the region.

## 5. Setting the region — through the official updater

`endupdate.sh` contains:

```sh
if [ -e /tmp_updater/updater/update/backup/*/*/*.bin ]; then
    echo "Backup.bin overwrite OK"
    cp /tmp_updater/updater/update/backup/*/*/*.bin /setting/Backup.bin
fi
```

So the region/language defaults are applied **at flash time from the update package**.
Repacking an update with `CX77500_ALLLANG.bin` inside is the "factory" way to get all
languages — no protection hack needed.

## 6. Tool

```bash
python tools/backup.py info  <file.bin>                  # header: region, counts, checksum
python tools/backup.py list  <file.bin> [--min-size N]   # every property
python tools/backup.py get   <file.bin> 0x010d008f       # one property
python tools/backup.py known <file.bin>                  # the table above
python tools/backup.py diff  <a.bin> <b.bin>             # e.g. ALLLANG vs J1
```

## 7. Open problem

The firmware contains **1058 distinct `BKID_*` names** (786 of them in
`libmprctrl.so`), i.e. the property *names* are in the binaries — but no public
mapping from name to numeric ID exists. Extracting it would give names to thousands of
the 16 102 properties. This is the single most valuable open item; see
[10-open-questions.md](10-open-questions.md).
