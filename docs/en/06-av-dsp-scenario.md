# 06 — AV DSP programs and scenario plug-ins

Two independent extension mechanisms live in `/usr`:

- **`sabin/`** — 44 programs for the on-chip "SA DSP" plus 24 data tables
- **`scenario/`** — 35 plug-in shared objects (`.so`) that drive AV operations

Both are plain files in the `nflasha15` (`/usr`) image, so both are replaceable by
reflashing that partition.

## 1. `sabin/` — DSP programs

68 files. 44 of them are programs in a Sony container with magic `aa 0a 13 91`;
24 are data (PSF tables, "tap step" coefficient sets, kernel parameters).

### Container format

```
0x00  magic     aa 0a 13 91
0x04  version   04 00 00 02
0x08  variant ID  e.g. 0x0200c001
0x0c  class     e.g. 0x010083
0x14  name      "SA_ZM_AVCEP…"
```

The name encodes engine + module: `SA_` + engine (`ZM` = Zima, `MN` = Minna) +
module (`AVCEP`, `AVCEQ`, `SPICA`, …).

### Classes

| Class | Contents |
|---|---|
| `0x010083` | **AVC family: 3 encoders + 2 decoders** |
| `0x010002` | audio codecs (AAC, AC3, Dolby 5.1, LPCM) + JPEG |
| `0x01000f` | AV utilities: **`SA_FRC2`** (frame-rate converter), CECIL, SHAPE, TBOX |
| `0x010001`/`0x010004`/`0x010008` | noise reduction (LFNR) for Zima / Minna 0 / Minna 1 + startups |
| `0x03000d` | **SPICA** — main image processing block |
| `0x01000c` | `SABT` — Bayes tracker (AF) |

Note: `sa_integenc.bin` (394 KB) is an **audio** encoder (class `0x010002`), not a
"integrated video encoder" — an easy misreading.

### The AVC family

| File | Internal name | ID |
|---|---|---|
| `sa_avce_performance_zma.bin` | `SA_ZM_AVCEP` | `0x0200c001` |
| `sa_avce_quality_zma.bin` | `SA_ZM_AVCEQ` | `0x0200c101` |
| `sa_avce_performance_plus_zma.bin` | `SA_ZMAVCEPP` | `0x0200c401` |
| `sa_avcd_performance_zma.bin` | `SA_ZM_AVCDP` | — |
| `sa_avcd_compatible_zma.bin` | `SA_ZM_AVCDC` | — |

Three encoder variants of the same state machine, differing by one byte of ID and by
a few kilobytes. **Which variant the A6000 uses is not established.** The AV firmware
(`av-cam.bin`) is position-independent and does not reference the variant names; a
naive search for the ID in `av-cam.bin` produces false positives because the pattern
straddles adjacent 32-bit table entries. This needs either proper disassembly or a
swap experiment.

### 4K: the path exists, two tables are missing

`av-cam.bin` references 27 files under `/usr/sabin/`. 25 exist. Missing:

```
dcv_psf_table_movie_4k.bin
dcv_psf_table_dualrec.bin
```

Yet **all** 4K "tap step" coefficient sets are shipped
(`spica_musashi_mov_4k_{c,y}_tap_step*`, `dualrec_4k_*`). So the 4K code path is
compiled in and mostly provisioned — what is missing is a per-mode PSF table and,
fatally, the Beaune codec chip (see [08-sibling-models.md](08-sibling-models.md)).

For comparison, the A6300 ships `dcv_psf_table_movie_4k.bin` and 10 extra DSP programs
(`sa_bayes_tracker_edge`, `sa_integdec`, `sa_motionshot`, `sa_nlg`, `sa_seg`,
`sa_zoom_nr`, …). Its DSP set is a strict superset of the A6000's.

## 2. `scenario/` — plug-ins

35 shared objects, ARM EABI5, not stripped, each exporting `scenario_run` and
communicating through the `osal_*` message layer (`DataflowInfra*` C++ classes).
Several read `Backup_read` directly, i.e. a scenario can read settings.

Three families:

| Prefix | Role | Examples |
|---|---|---|
| `AVBB_SCN_*` | AV baseband: HDMI, audio, mic, EVF panels, recording | `START_VIDEO`, `START_HDMI`, `START_MIC`, `L_R_SETTING` |
| `CAMERA_SCN_*` | camera operations | `EE_START_STOP`, `MOVIE_REC_START`, `FACE_REC_DATA`, `SET_ZOOM_DRV`, `EXTERNAL_RAW_RECORD` |
| `MPR_SCN_*` | main-processor / service | `FORMAT`, `GET_TOTAL_LOG`, `GET_CONTENT_COUNT`, `**EXEC_FACTORY_MODE**`, `EXEC_WIFI_TEST`, `FLASH_BACKUP_INIT` |

Factory functions (`EXEC_FACTORY_MODE`, `EXEC_WIFI_TEST`, `FLASH_BACKUP_INIT`) are
present in retail firmware.

### Table vs shipped files

`lib/libsencore.so` holds a table of **27** scenario names; **35** files are shipped.
In the table but not shipped: `AVBB_SCN_*_HDMI_SDI*` (SDI output — the A6000 has no SDI
connector) and `HMPR_SCN_GET_TOTAL_LOG` / `GET_CONTENT_COUNT`.

That pattern repeats across the whole firmware: **code and tables are a platform-wide
superset, files are a per-model subset, and hardware is the final limit.**

### Running a single scenario

`/usr/bin/scenario.elf` is a ready-made harness:

```
<options> [scenario_name] [size]:[data] ...
    specified scenario name like below
        /usr/scenario/xxxx.so
```

with binary I/O helpers (`cmdline_get_ifile`, `cmdline_read_bindata_to_stdout`,
`cmdline_write_bindata_to_obfile`). Combined with a root shell
(OpenMemories-Tweak exposes telnet/adb) this is the most "programmer-like" interface
to the camera available without reflashing.

### Writing your own plug-in

Since a scenario is just an ELF exporting `scenario_run` and speaking `osal_*`, a
custom plug-in can be dropped into `/usr/scenario/` in a reflashed `/usr`. That is a
real code change at the AV-control layer — deeper than an APK, shallower than patching
`av-cam.bin` — and it only affects runtime state, not flash.

## 3. Boot-time subset

`nflasha3/sabin/` (inside `/system`) holds a small subset loaded at boot:
`idt_cam.bin`, `sa_dfdet.bin`, `ssboot.bin`, `ssboot_any.bin` — identical in A6000 and
A6300.

## 4. Open items

- Which AVC encoder variant is active, and whether `quality`/`performance_plus` would
  improve image quality on this body.
- Whether the 5 extra register blocks and the extra DSP programs on A6300 can be
  exploited at all without the Beaune chip.
- Nobody has publicly analysed a single `sabin` program, even though a Ghidra
  processor specification exists (`ma1co/SA-DSP`).
