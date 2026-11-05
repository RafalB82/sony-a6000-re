# 11 — SWD: the debug port and how a bricked A6000 was recovered

The A6000 has a live ARM CoreSight debug port that nothing in Sony's boot chain
locks. It was used in November 2026 to recover a camera bricked by a modified
firmware: `r0` was forced at one instruction during boot, the factory updater ran,
and Sony's own firmware was installed over USB. **Nothing was written to NAND.**

> **Source and status.** Everything on this page is second-hand, taken from the
> reports of [`nicolvus/a6000-fw-decomp`](https://github.com/nicolvus/a6000-fw-decomp)
> (E26-R40, R46, R47, R48, R49, R51; 2026-10-31 … 11-03). Their evidence labels
> (`MEDIDO` = measured, `LEÍDO` = read from the binary, `INFERENCIA` = inferred,
> `NO VERIFICADO` = not verified) are preserved below. **Nothing here was verified
> on hardware by us.** Addresses are for the Loader3 shipped with 3.21/3.26 and
> move with the bootloader.

## 1. The port exists, on two 0402 pads

| Item | Value | Provenance |
|---|---|---|
| Target | SoC `IC6000` = CXD90014 (BIONZ X), balls **W25 = SWCLK**, **W26 = SWDIO** | service manual schematic |
| Route to the service connector | `R4911` / `R4912` → `CN4906` pins 11/12 | schematic |
| Population | `R4911`, `R4912`, `R4915`, `R4916` and `CN4906` are **not fitted** (footprints only) | schematic marked `XX`, confirmed visually |
| Classic JTAG | TDI/TCK/TMS tied to `D_3.15V_MSS` → unusable | schematic |
| `FUSE_EN` (T12) | also tied to 3.15 V; debug-disable eFuse never observed | schematic |
| Alternative reset | `NTRST` = `XRESET_CR` (ball H26) | schematic |
| Line voltage, camera running | 3.09 V on both pads (3.15 V logic) | measured |

Practical route used: a 0.1–0.2 mm enamelled wire soldered **directly to the
BIONZ-side pad of R4911/R4912**, plus ground. No 0 Ω resistors and no `CN4906`
needed. This is irreversible work on the board; the alternative (fitting 0 Ω and
using `CN4906`) needs more soldering on finer pads.

## 2. What answers on the wire

```
DPIDR   0x3ba02477
AP0     IDR 0x44770001  AHB-AP   CSW=0x02800062   physical memory
AP1     IDR 0x24770002  APB-AP   CSW=0x80000042   CoreSight, BASE=0x80000000
AP2     IDR 0x14760010  JTAG-AP
AP3–AP5 empty
```

- ROM table `0x80000000` → nested `0x80100000` → **four Cortex-A5** (`part 0xc05`),
  debug bases `0x80110000/12000/14000/16000`, each with PMU/CTI/ETM. All work was
  done on core 0.
- **No read lock.** AP0 and AP1 answer; an eFuse blocking debug reads is ruled out.
  Write access through the DAP was never tested beyond `halt` and `set_reg` of CPU
  registers.
- Two ways to read memory: through AP0 (`TAR` = `0x04`, `DRW` = `0x0c`, 32-bit
  words), or through the core (`target create … cortex_a -ap-num 1 -dbgbase
  0x80110000`, `read_memory` — respects MMU and caches).

This independently confirms what our [01-hardware.md](01-hardware.md) says from the
service manual: CXD90014 is a 4× Cortex-A5.

## 3. Halt without a target object

Used to stop the CPU before the boot chain finishes:

```tcl
apreg 1 0x04 0x80110fb0 ; apreg 1 0x0c 0xc5acce55   ; DBGLAR   = unlock
apreg 1 0x04 0x80110300 ; apreg 1 0x0c 0            ; DBGOSLAR = 0
apreg 1 0x04 0x80110090 ; apreg 1 0x0c 1            ; DBGDRCR  = halt request
```

That is the standard external-debug sequence for Cortex-A. It writes CPU debug
registers only — no application memory, no NAND.

## 4. Taking control of boot

The whole chain (BootROM → Loader2 → Loader3) runs in under a second, so the
technique is: halt as early as possible, then chain breakpoints — one on the
Loader3 entry (`0xc01f0000`), and at every hit remove all breakpoints, `step` once,
re-arm the next ones, resume.

Four traps, each of which cost them a session:

1. **Breakpoints armed during Loader2 do not survive into Loader3.** A report was
   published on the strength of one that "never fired" — and had to be retracted.
2. **Without the `step`, a breakpoint fires on itself dozens of times.** One run
   recorded "39 hits" that were not 39 calls.
3. **The generic `sp`/`lr` aliases read 0 for banked registers.** `sp_svc`/`lr_svc`
   must be requested explicitly; the generic aliases once made a healthy stack look
   like a `mov pc,lr` to NULL.
4. **"It boots twice" was wrong.** With the battery inserted and the switch OFF the
   camera runs Loader2/Loader3 for ~0.87 s and then powers itself off
   (`XPWR_OFF`, `b .` at `c01f5e50`, BootMode branch 7/8/9/13/14). Turning the
   switch gives **one** continuous boot (~2.7 s) that ends in the LED loop
   (BootMode 11). A script that waited for a "second boot" simply timed out and
   changed nothing.

## 5. Where the −302 comes from, measured

The LED error code is computed in `c01f3b74` as `r4 = -code`, `LDR2 = r4/1000`,
`LNG = (r4%1000)/100`, `SHT = r4%100`. Registers read `0/3/2` → **−302**, matching
the 3-long + 2-short blink.

With breakpoints on the real (switch) boot:

| Stop | Value |
|---|---|
| Entry of P2, `0xc01f2f24` (`CFG_E:Load file`) | `r0 = 0xc005c000` — CFG entry 0 |
| Return of P2 | **`r0 = 0xfffffed2` (−302)** |
| LED routine `c01f3b74` | same −302, `lr = 0xc01f1269` |

The CFG table sits at `0xc005c000`, stride `0x90`, mode mask at `+0xc`:

| File | Destination | Partition |
|---|---|---|
| `\sabin\idt_cam.bin` | `0x83501000–0x83540fff` | 3 |
| `\sabin\sa_dfdet.bin` | `0x96800000–0x9682ffff` | 3 |
| `\av-cam.bin` | `0x83541000–0x84140fff` | 3 |
| `\kemco.txt` | `0x80033000–0x80033fff` | 2 |
| `\initrd.img` | `0x80628000–0x80e27fff` | 3 |

The first file from partition 3 fails and the loader stops there — so `nflasha3`
really is unreadable, and the format hypothesis in their R36 is confirmed by
measurement.

## 6. The injection: make `\updater\mode` "exist" without writing anything

`chk updater` at `0xc01f15c0` calls `c01f44c6("\updater\mode")` and then does
`cmp r0,#0` / `bge`. If `r0 >= 0` (file exists) Loader3 picks **BootMode 3** and
loads the factory updater from `nflasha1`, which no firmware update ever rewrites.

So forcing `r0 = 0` at that one instruction is equivalent to the file existing:

```
BP_HIT k=0 pc=0xc01f0000                    Loader3 entry
BP_HIT k=1 pc=0xc01f15c0 -> r0 forced to 0   chk updater
BP_HIT k=2 pc=0xc01f1e16                    BootMode 3 selected
BP_HIT k=3 pc=0xc01f15c0 -> r0 forced to 0   second call
BP_HIT k=4 pc=0xc01f1378                    updater entry
```

Entry of Loader3 to entry of the updater: **696 ms**. `chk updater` has 8 call
sites; the script forces all of them and re-reads `r0` after each write to prove
`set_reg` took effect. The Tcl script is
[`analysis/e26-recovery/r48_updater_swd.cfg`](https://github.com/nicolvus/a6000-fw-decomp/blob/main/analysis/e26-recovery/r48_updater_swd.cfg).

Why not simply patch NAND: **Loader3 cannot write blocks.** In `muminblk_request`
(`c01fd5a4`) a read calls `muminblk_transfer`; a write jumps to `c01fd66a` and
returns success **without transferring anything** (the trace literal says `"write"`
instead of `"read"`). The MuMin write functions are in RAM but the block layer never
uses them. That is why both "create the file by hand" and "reflash `nflasha3` over
SWD" were dropped — no mechanism, not just risk.

## 7. The recovery run

- Camera in updater mode: `054c:03e2`; `pmca-console firmware -f` with a 3.26
  package (official 3.24 content, version bumped — legal because the guard checks
  only CRC32, LSI type and version; see [03-integrity-and-flashing.md](03-integrity-and-flashing.md)).
- **First attempt stopped at 45 % with `Response error: 0x1063`.** Decoded their
  way: `ErrorConverter::Convert` in `sauu` (`0xe9b0`) returns the LED code with
  `| 0x1000`, so `0x1063` = LED **`0x63`** = "Darwin did not answer over SIO / never
  reached state 5". After it the protocol channel answered `0x1063` to everything,
  but the updater's Linux kernel was not hung (banked `sp_svc`/`lr_svc` sane) and
  the version was still 3.25 (`CompleteUpdate` never ran).
- Power cycle: the camera came back into updater mode **on its own**, because
  `StartUpdate` had already created `\updater\mode`.
- **Second attempt: 100 %, `Done`.** `pmca info` → firmware 3.26, normal Mass
  Storage. The cause of `0x63` was never explained; interference from the probe on
  Darwin's lines is one of their hypotheses.

## 8. What else the port gave them

- **BootROM serial key from `nflasha0`**: the BootROM copies block 0 into SRAM on
  every boot; at `0xc0000600` there is `EXBL` plus pointers to `Loader2.bin`
  (`0xc01f0000`) and `DiagUni.bin` (`0xc0038000`), and at `0xc0001200` the key
  **`0x5bc022a5`**, followed by `0xa8840468` = `~crc32(key)` — CRC-32 of the first
  8 bytes is `0xffffffff`, i.e. the format is valid. Read through `mem_ap` **with
  the camera running, no halt**.
- Full NVRAM backup on 3.26 (852 647 B, BK4) and a 3.28 rollback package.
- An unrelated finding: enabling adb on 3.27 hits `LDEC ERR -10003` on page
  `0x02c3` of `nflasha0p17` (`/android/data`) → `NULL pointer dereference at 0x6`
  → `WARMBOOT`. A bad page in the data partition, not the firmware patch.

## 9. Limits, and what does not add up

- **Debug write path untested.** They halted and changed CPU registers; they never
  loaded code into RAM. Sony's own `cxd90014_ice_*` defconfigs exist precisely for
  loading a kernel from a debugger, which would bypass the whole Loader3 chain —
  nobody tried it.
- **`0x1063` (Darwin NG) unexplained.** Not investigated because the retry worked.
- **The probe is still soldered** (state as of their last report).
- **Contradiction in their own documentation:** R48 §8 says the updater was entered
  "by another route" and that P1 was never executed, while R49 §7.2 shows the
  successful injection and calls it "the route that worked"; `PENDIENTES.md` carries
  both versions. The *mechanism* is proven by the register log (BootMode 3 selected,
  entry at `c01f1378`), but which attempt actually used it cannot be reconstructed
  from the reports.
- **Not verified by them:** `CTRL/STAT` of the debug port, whether `CN4906` pads are
  reachable, whether the eFuse blocks *writing* through the port, and any external
  NAND dump.

## 10. Why it matters for this repository

- It is the only documented way back from a bad `nflasha3`, and it depends on
  exactly the property we established in
  [03-integrity-and-flashing.md](03-integrity-and-flashing.md): no signatures, only
  CRC32 and a version guard.
- It confirms from silicon what we had from the service manual (4× Cortex-A5).
- It adds addresses we did not have: Loader3 base `0xc01f0000` (88 064 B, identical
  in `bootloader.bin` at `0x22800`), `chk updater`, the CFG table, the LED code
  routine.
- It also sets the real cost of experimentation: the way out is **soldering to the
  SoC**, not a USB trick. Any plan that modifies `nflasha3` should assume that.

Their reports, in order: [R40](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r40-jtag-swd-bionz.md) (static case for SWD),
[R46](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r46-procedimiento-fisico-swd.md) (procedure),
[R47](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r47-primer-contacto-swd-lectura-ram.md) (first contact, RAM dump, −302 measured),
[R48](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r48-plan-recuperacion-actualizador-swd.md) (injection plan),
[R49](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r49-cierre-recuperacion-326.md) (closure),
[R51](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r51-respaldo-clave-nflasha0-nvram-326.md) (key, NVRAM).
A readable narrative version is their [wiki page 15](https://github.com/nicolvus/a6000-fw-decomp/wiki/en-15-SWD-recovery-experimental).
