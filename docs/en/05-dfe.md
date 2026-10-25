# 05 — DFE: the front-end MCU

`/usr/dfe/dfe.bin` is the firmware of the **CXD90027GF** front-end chip — the part that
reads the sensor. It is small, unobfuscated and, as far as this research could tell,
never analysed publicly before.

## 1. Loading it into a disassembler

```
file:  dfe/dfe.bin
size:  65 536 bytes
sha256 fc4e314db24a72d584bd8795bd8f1144b003c97c390cb143d09b840b38bf9fcd
```

Raw blob, no header. The load address is derivable from the code:

```
00000000: 18 f0 9f e5    ← vector 0: LDR PC,[PC,#0x18]  → reads (A+8)+0x18 = A+0x20
00000020: 70 58 00 01    ← value 0x01005870 = reset handler
```

Since the literal sits at offset 0x20 and holds `0x01005870`, **file offset 0 maps to
`0x01000000`**. Further literals (`0x01005834`, `0x01005838`, `0x0100584C`) confirm it.

Load as **ARM little-endian v7** at `0x01000000`. Analysis finds **83 procedures** and
**94 strings**.

## 2. What it does

| Function | Role |
|---|---|
| `dfe_entry` / `dfe_reset_handler` (`0x1005870`) | reset vector chain |
| `dfe_apb_selftest` (`0x1000c8c`) | writes/reads min & max address of every peripheral block over APB, prints OK/NG |
| `dfe_irq_selftest` (`0x1000a94`) | walks every interrupt line (ZPD0/1, DFECAM0/1, SiMISC0/1, SSG0/1, DFELINK) |
| **`dfe_zpd_af_detect`** (`0x1001da4`) | **phase-detect autofocus** |
| `dfe_zpd_init`, `dfe_zpd_scc_end`, `dfe_scc_mode_start` | ZPD init / mode sequencing |
| `dfe_print`, `dfe_puts_emit`, `dfe_flush` | log output (see §4) |

The strongest identification is a single string inside the ZPD handler:

```
"Hello Regulus: apl_zpd_af_det"
```

*Regulus* is the codename of CXD90027; `zpd` is the phase-detect block. A6000 has
179 phase-detect AF points — this is the firmware that produces them.

A large fraction of the binary is self-test, not runtime: APB access tests per block,
interrupt tests, and strings such as `>>> ICache: Enable`, `>>> DCache: Enable`,
`>>> Main...`, `>>> Simulation Finished...`. Any deeper analysis must first separate
bring-up code from runtime code.

## 3. Register map (recovered from literals)

Sony left the block names in the diagnostic strings; the base addresses come from
literal pools.

| Block | Base | Notes |
|---|---|---|
| **ZPD** (AF) | `0x01010000` | main block; status at `+0xfc`, control at `+0xf8`, `+0xe010`, `+0xe014`, `+0x88908` |
| ZPD_APB0 | `0x0109828C` … `0x01099F54` | APB access test bounds |
| ZPD_APB1 | `0x0102B808` … `0x0102B9B0` | |
| **SSG** (timing generator) | `0x01080020` … `0x010800FC`, IRQ `0x01080100`/`0x0108010C` | sensor timing |
| SiMISC | `0x01088200` … `0x0108853C`, IRQ `0x01088900`/`0x01089900` | |
| **DFECAM0** | `0x010A0108` … `0x010A781C`, IRQ `0x010A0010` | defect correction |
| DFECAM1 | `0x010A800C` … `0x010A8B38`, IRQ `0x010A001C` | |
| DFECAM2 | `0x010B0000` … `0x010B5000` | |
| DFECAM3 | `0x010B8000` … `0x010BA000` | |
| DFECAM4 | `0x010C7000` … `0x010C8000` | |
| DFECAM5 | `0x010CF000` … `0x010F0050` | |
| **DFELINK** (to SoC) | `0x010F0000`, `0x010F11C4` | host link |
| unassigned | `0x01011000`, `0x01012000`, `0x01013000`, `0x0101D000`, `0x0101E000`, `0x01020000`, `0x01022000`, `0x01026000`, `0x01029000`, `0x0102D000` | `0x0102D000` is the log buffer, see §4 |

These addresses are read from literal pools; they were **not** verified against live
hardware. Block names come from Sony's own diagnostic strings.

## 4. The log channel is RAM, not a UART

Call chain:

```
dfe_print (0x1006070)
  ├─ dfe_lock
  ├─ dfe_critical_enter
  ├─ dfe_puts_emit(arg)        ← writes the string byte by byte
  ├─ dfe_puts_emit(terminator)
  ├─ dfe_flush                 ← resets a counter
  └─ dfe_critical_exit
```

`dfe_puts_emit` writes each character through a pointer literal:

| Literal | Value | Meaning |
|---|---|---|
| `0x01005ce4` | **`0x0102D000`** | **output buffer pointer** |
| `0x01005ce0` | `0x0100639C` | counter/flag reset by `dfe_flush` |

There is no UART-like register anywhere in the image. **DFE diagnostics are written to
a RAM buffer at `0x0102D000`**, which must be readable from outside — plausibly via
DFELINK or as a window into DFE memory. Closing that loop is an open item.

## 5. The firmware ships twice

`dfe.bin` exists as a standalone file **and** byte-identically embedded inside
`av-cam.bin` at offset **`0xA67F00`** (preceded by zero padding, aligned to 0x100).

Which copy the SoC actually uploads is **not established** — `av-cam.bin` is
position-independent code with no literal pointing at the path string, and Ghidra's
startup budget (330 s) was not enough for the 11 MB module. This matters: if the
embedded copy wins, replacing `/usr/dfe/dfe.bin` changes nothing.

## 6. Symbol names

All 83 procedures are named in `data/dfe-names.txt`; `tools/apply-dfe-names.py`
reproduces the names in a fresh Ghidra project. Two naming passes were used:

1. **Manual (15)** — from decompilation: `dfe_print`, `dfe_puts_emit`, `dfe_flush`,
   `dfe_lock`, `dfe_critical_enter/exit`, `dfe_irq_selftest`, `dfe_irq_probe`,
   `dfe_apb_selftest`, `dfe_zpd_af_detect`, `dfe_zpd_init`, `dfe_zpd_scc_end`,
   `dfe_scc_mode_start`, `dfe_entry`, `dfe_reset_handler`.
2. **Heuristic (68)** — every `DAT_xxxxxxxx` literal in the decompiled body is resolved
   against the register map; the function inherits the block it touches
   (`dfe_zpd_apb0_NN`, `dfe_ssg_NN`, `dfe_defcamN_NN`, `dfe_dflink_NN`,
   `dfe_logbuf_NN`), otherwise `dfe_util_NN`.

Result: ~43 functions attributed to peripherals, 33 generic helpers. The largest
groups are `zpd_apb0` (14) and `zpd_apb1` (10) — most of the code serves the AF block,
which matches the DFE's profile.

## 7. Why this matters

The DFE owns **sensor readout**: `SSG` (timing) and `DFECAM0–5` (defect correction).
If this camera has unused sensor modes anywhere — binning, line-skipping, alternative
readout windows — they are here, not in `av-cam.bin` and not in `sabin/`.

The file is also unusually approachable: 64 KiB, plain ARM, no compression, and a
simple interrupt model.
