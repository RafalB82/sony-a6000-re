# 14 — The EFCS/Electronic selector: from a bricked camera to a working electronic shutter

This is the only attempt in the wild to *add a function* — a shutter-mode selector — and
it is also the one that first bricked a camera and then turned out to be the working route
to a silent shutter. The selector code in BIONZ did its job, but the signal was lost: the
real producer of the `pkt[0x0e]` byte turned out to be the **send** constructor
`0x438d0064`, not the capture constructor (R54). Once the send path was redirected, **the
electronic shutter works as of 3.30** (2026-11-04). The same cycle exposed a second fact:
**EFCS on comes out black from 1/1000 even on Sony's stock firmware** (R57 §5) — a defect
of the camera's EFCS path itself, later compensated with a calibration table in NVRAM
(R84–R86).

> **Source and status.** From [`nicolvus/a6000-fw-decomp`](https://github.com/nicolvus/a6000-fw-decomp),
> reports E25-24, E25-24b, E25-25, E25-26, E25-27, E26-R52, R53 (selector), R54–R57
> (electronic), R66–R68 (black EFCS), R84–R87 (Darwin v3, EFCS tables), with measurements
> on a real camera (SWD probe). Their labels kept. **Not verified by us.** Updated
> 2026-11-25.

## 1. The idea

The A6000 has no "Silent" menu entry. It does have an **EFCS on/off** setting, whose
value lands in a single field: `+0x210` of the block at `0x43edf684` (`0` = EFCS on,
`1` = EFCS off — measured in T012, the opposite of what an earlier test assumed). The
patch reuses that setting as a two-state mode selector:

| Menu | Model | `+0x210` | Mode | Rear curtain |
|---|---|---|---|---|
| EFCS on | `0x2b4` | 0 | EFCS | mechanical (Sony's route) |
| EFCS off | `0x2b5` | 1 | ELECTRONIC | none (Darwin suppresses coils and motor) |

No new menu entry, no reinterpretation of the stored byte: the new meaning is carried per
shot by a byte in the capture packet.

## 2. The chain, end to end

```
libObj (userland)  action 0x6896ac -> message 0x75fa -> parameter 0x9776
                   converter 0x68c24a: 1 -> 0x2b4, 2 -> 0x2b5
                   sequence 0x95a308 -> LIRO selector 0x4099 -> converter 0x99e968
                   9-byte buffer: [+0]=05, [+2..3]=99 40, [+8]=0/1
        | LIRO
        v
LIRO table entry 0x4099 (offset 0xabe954) -> handler 0x43802e4c
        ldrb r2,[r0,#8] ; str.w r2,[0x43edf684 + 0x210]
        v
0x43844e80   reads (*ctx)+0x210, stores a word into param6+0x41c
        v
0x43841070   capture constructor
   |- 0x43842158  reads [sb+0x41c], computes exposure class 0..7
   |- PATCH: pkt[0x0e] = [sb+0x41c]   (both branches)
   v  0x0c packet, 22 bytes, over CAIF
Darwin 0x17f8c: copies packet to S+0x30 (S = 0x200036d8)
       0x17ff8/0x17ffc: pkt[0x0e] -> S+0x3e (0x20003716)
        v
Darwin 0x20c74 / 0x1fe66 -> cave 0x4318 -> 0x1b080 (EFCS) or 0 (Electronic)
        v
P4D/P4E and motor: normal on EFCS, suppressed on Electronic
```

The rest of the capture path is untouched: `0x437f8a50` builds `cap+0x64c/0x6bc`,
`0x438c830c` calls `SetExposure`, `0x438c831e` `SetRead`, `0x438c8330` `Execute(1)`, and
`0x43901a8c` sends the `0x107` packet. The selector only decides whether Darwin may move
anything.

## 3. The two caves

**BIONZ, `av-cam.bin`** — 20 bytes at `0x43541800`, in the reserved LIRO header area
(zero in A6000 and A7S, no literals or branch targets there):

```
00 23          movs r3,#0            ; keeps r3=0 so pkt[1] stays 0x40
23 70          strb r3,[r4]          ; pkt[0] = 0
d9 f8 1c 24    ldr.w r2,[sb,#0x41c]  ; EFCS field
a2 73          strb r2,[r4,#0xe]     ; pkt[0x0e] = the mode
01 29          cmp r1,#1
01 d0          beq +2
ff f2 70 bd    b.w 0x43841576        ; second (original) branch
70 47          bx lr
```

Three sites around it are edited: `0x4384133e` (conditional branch → 2 × `nop`),
`0x43841342` (`→ bl 0x43541800`) and `0x43841476` (the later unconditional store → `nop`,
so it cannot overwrite the byte). An earlier placement at `0x43541a80` was rejected after
it turned out to be inside a 512-byte object with a GOT entry.

**Darwin, `darwin_core.bin`** — 14 bytes at `0x4318` plus a literal at `0x4330`:

```
ldr r2,[pc,#0x14]   ; -> 0x4330 = 0x20003716 (S+0x3e)
ldrb r2,[r2]
cbz r2, +2          ; 0 -> original route
movs r0,#0
bx lr               ; != 0 -> return 0 (no coils, no motor)
b.w 0x1b080
```

Two call sites are redirected: `0x20c78` (coil type, `0x20c74`) and `0x1fe6c` (motor gate,
`0x1fe66`). `0x4318..0x4327` and `0x4330..0x4333` were zero vector-table entries (70 and
76). This **replaces** the type-0/B1a patches: it starts from the original Darwin, so EFCS
gets the real mechanical route back and Electronic gets suppression per shot.

## 4. C3-B: the exposure side

Suppressing the mechanism is not enough — the sensor has to integrate and be read out
without a rear curtain, which is a separate patch (E25-26) hooked at `0x438c82fe`, gated
on the same `pkt[0x0e] == 1`, setting `ShutMode 0` and the start line `r5` instead of the
native producer `0x4383fa40`. Their measured model for the resulting exposure is
`T + ~7 ms + 15.2 µs × row` (readout ≈ 61 ms), i.e. shutter speed barely scales from
1/4000 to 1/500 without it.

Native `ShutMode` plumbing, for reference: class from `0x43842158` → `record+0x6d` →
`0x4383fd6c` copies 16 bytes (`record+0x64..0x73`) to the destination → class lands at
`cap+0x655` → `0x438c828c` calls `SetExposure` with `cap+0x64c` (skipped when
`cap+0x4b9c≠0`; device classes 2/3 overwrite the selector with 0) → slot `+0x28` →
IMX210 `0x436d6f6c` → register `0x4401ca2c` → P2S list `0x43fe995c`, index 1.

## 5. What the camera actually did

| Version | Result |
|---|---|
| 3.25 | **bricked.** The same payload also contained a recompressed `nflasha3`; see [12](12-partition-format.md). The cause was the partition format, not the selector |
| 3.25c / 3.27 | boots; first proof that a properly rebuilt `nflasha3` loads (`idt_cam.bin` where 3.25 gave −302) |
| 3.27, EFCS off | selector works *inside* BIONZ: `+0x210 = 1` → `cap+0x41c = 1` → cave writes `pkt[0x0e] = 1` → observed with a breakpoint (`r1=1`, `pc=0x43541800`); a write watchpoint confirmed the cave stores 1. The value lives **< 1 ms** in the constructor buffer, and the *sent* buffer reads 0 |
| 3.27, sampling | 1 seen once via AHB at the moment of capture, never in the outgoing buffer; a later report retracted one "send routine" (`0x4382fac8` is a µs conversion, not the sender) |
| 3.29 | cave rewritten to read the EFCS field live instead of `[sb+0x41c]`; **installed and measured**: capture packet carries 1, but 2 ms later the buffer is back to the idle packet (`pkt[0x0e]=0`), so something else restores it. Sound unchanged ("the fix does not work") |
| 3.30 | **the electronic shutter works.** The real producer of `pkt[0x0e]` is the send constructor `0x438d0064` (`strb.w r3,[r2,#0x4e]` at `0x438d01fa`), which overwrote the selector's 1 on every send (R54 §1). A new 16-byte cave at `0x43541820` hooks `0x438d01fa` and writes `pkt[0x0e]` = the EFCS setting on *every* send. A shot without the curtain confirmed by the user (EFCS off, MEDIDO). Exposure: only with the app RAM patch (ShutMode 0 + `r5`, calibrated at 1/250), see [13](13-darwin-shutter-patch.md) |
| 3.33–3.35 | **no caves, TPZL block 0 untouched** (only blocks 48 and 57 change): an inline patch inside `0x438d0064` (3.33), and from 3.34/3.35 also in the photo constructor `0x43841070`, covering both branches (R56). The adb hang from [11](11-swd-recovery.md) turned out to be caused by the modified block 0 — with it restored, adb works (R56 §4) |
| 3.36 / 3.37 | the Darwin `== 1` gate was not the cause of the black frames: on **official Sony content 3.37**, EFCS on comes out black from 1/1000, also with the mechanical shutter — a defect of the camera's EFCS path itself, not of the patch (R57 §5). The exposure reference is EFCS off on 3.37 (full mechanical) |
| 3.43 + NVRAM table | Darwin v3 (R82–R84): the same gate plus a compensation table read from **NVRAM** at `0x1850000+0x48`. With the test table (`c` = 2000 µs for all speeds) EFCS on **stops coming out black, including 1/4000** (MEDIDO) — the NVRAM write really reaches Darwin |
| 3.76 / 3.77 | three modes leveled (R85–R87): mechanical = reference; EFCS leveled by a calibrated NVRAM table (loss ≈ 1.0–1.25 ms); Silent in-image (hook `0x438c82fe`, the same site as C3-B: ShutMode 0 + `r5` from Tv, cap 4218 ≈ 1 delay line). CFW 3.76 installed 2026-11-11, EFCS table written via service mode |

Their latest measurements (R53 §7) locate the real emitter of event 1 at `0x436b8a50`
(copies `payload+0x40` → `0x43f91e32`); at a breakpoint there, the CPU view of the buffer
shows `pkt[0x0e]=0` while the AHB view of the same address shows 1 — a cache-coherence
artefact that makes part of the earlier sampling unreliable. (This paragraph is
historical: R54 resolved the puzzle more simply — the overwriting send.)

### 5a. After 04-11: black EFCS and the table fix

The black frames with EFCS on (on 3.35/3.36 and on stock Sony) have a measured timing
cause: a loss of ≈ **1.0–1.25 ms** in the EFCS loop (R85), plus a vertical gradient —
the top-to-bottom difference grows from ≈0.9 ms (1/350) to ≈1.8 ms (1/3000) (R83 §5).
The fix was not in BIONZ: Darwin reads a compensation table from **NVRAM**
(`0x1850000+0x48`, 56 bytes, checksum, synced to flash), and Darwin v3 (R82–R84,
in-situ at `0x18d6e..0x18e0f`) applies `c` per speed. The photo series DSC03749–03806
produced calibrated tables (R85, R86); predicted exposure is 0.985–1.015·T from 1/4000
to 1/30.

Limits (MEDIDO): the table cannot level the vertical gradient — EFCS is only uniform on
average; from ~1/1000 upward use mechanical or electronic (R85 §3.1). Fast Silent: above
~1/600 the model gives ≤ 0 lines, i.e. an exposure floor of ≈ 1.7 ms equivalent
(`r5` cap 4218); a sub-line patch for that limit exists only in emulation, without a CFW
(G38).

## 6. Why they did not make the Darwin gate "sticky"

The obvious next step — latch the 1 inside Darwin so it survives idle packets — does not
fit: only 2 bytes are free in the vector table next to the existing cave, the 80-byte "NOP
zone" at `0xdf06` is actually a function called from `0xdfbe`/`0xdfcc`, and there are no
zero gaps inside the code. So the change moved to the source of the data in BIONZ.

## 7. Limits

- **The electronic shutter works** — since 3.30 (R54), with calibrated exposure since 3.35
  (R56 §7) and in-image since 3.76 (R86). The first working step on hardware remains 3.23
  ([13](13-darwin-shutter-patch.md)).
- **EFCS on has a defect that predates the patch:** black from 1/1000 on official Sony
  3.37 (R57 §5). The physical cause is unknown (candidates: calibration lost during the
  recovery, sensor/curtain hardware — NO VERIFICADO); compensated by the NVRAM table with
  the limits in §5a.
- It is not known what Darwin receives at the moment of the shot, nor what gate `0x4318`
  sees; reading Darwin's RAM (`0x20003716`) needs a probe on `CN4906` pins 11/12 (which are
  the BIONZ SWD lines, not Darwin's).
- In BIONZ the delay in the task call chain means `S+0x30..0x47` is only cleared at task
  start (`0x196fa`, called once from `0x1815c`); 24 call sites read `0x1b080`, and only
  `0x20c78`/`0x1fe6c` go through the cave.
- **The cave approach was retired:** from 3.33 the BIONZ patches are inline, without
  caves, with TPZL block 0 untouched (blocks 48/57 change); this also fixed the adb hang
  (R56 §4). The remaining BIONZ caves (`0x43541800/1820/1840`) and the Darwin gate
  `0x4318` stay in the CFW builds.
- Three-state (MECHANICAL/EFCS/ELECTRONIC) was realized differently than designed: not
  via a third persistent menu value, but by composition — in-image Silent gated on its
  own byte (`cap+0x41d`), EFCS leveled by the NVRAM table, mechanical untouched (R86 §1).
- Repeating their run means flashing modified firmware (`pmca-console firmware` install,
  often a first `0x1063` to retry) — the risk is unchanged: **no independent recovery**
  (E24-04/E25-04); the way back is [11](11-swd-recovery.md).

## 8. Why it matters here

It answers, with code and measurements, the question our [10-open-questions.md](10-open-questions.md)
leaves open: the A6000's shutter mode is not a hidden enum waiting to be flipped. The body
has exactly two states in this path (EFCS on/off), the sensor takes its instructions from a
per-shot `ShutMode` field, and the mechanical suppression is a property of Darwin's own
configuration cell — which is why a 2-byte Darwin patch works. The BIONZ feature only
started working once the patch covered the real producer of the byte (the send
constructor, R54) and the exposure was calibrated separately — first as an app RAM patch,
then as an in-image hook (R86).

Reports: [E25-24](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-24-selector-efcs-electronico.md) (audit and blockers),
[E25-24b](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-24b-implementacion-selector.md) (implementation, caves, emulation),
[E25-26](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-26-c3b-exposicion-electronica.md) (C3-B),
[E25-27](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-27-construccion-firmware-integrado.md) (integrated build),
[R52](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r52-prueba-fisica-selector-327.md) / [R53](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r53-paquete-329-ajuste-efcs-en-vivo.md) (what the camera measured),
[R54](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r54-paquete-330-envio-pkt0e.md) (send path, first electronic shutter),
[R56](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r56-paquete-333-envio-inline.md) (inline, 3.33–3.35, calibration),
[R57](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r57-paquete-336-darwin-eq1.md) (==1 gate, EFCS black on stock Sony),
[R66](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r66-bloques-darwin-en-nvram-1850000.md) (Darwin blocks in NVRAM),
[R84](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r84-darwin-v3-en-camara.md) (Darwin v3 in camera),
[R85](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r85-calibracion-fotos-3749-3779.md) / [R86](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r86-cfw-376-tres-modos-nivelados.md) (EFCS tables, three modes).
