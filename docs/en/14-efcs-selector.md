# 14 — The EFCS/Electronic selector: why the menu works and the shutter does not

This is the only attempt in the wild to *add a function* — a shutter-mode selector — and
it is also the one that bricked a camera. The code is in place and does what it was
designed to do inside BIONZ; the signal it produces never reaches Darwin reliably. As of
2026-11-04 the electronic shutter does not work.

> **Source and status.** From [`nicolvus/a6000-fw-decomp`](https://github.com/nicolvus/a6000-fw-decomp),
> reports E25-24, E25-24b, E25-25, E25-26, E25-27, E26-R52, E26-R53, with measurements on
> a real camera (SWD probe). Their labels kept. **Not verified by us.**

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

Their latest measurements (R53 §7) locate the real emitter of event 1 at `0x436b8a50`
(copies `payload+0x40` → `0x43f91e32`); at a breakpoint there, the CPU view of the buffer
shows `pkt[0x0e]=0` while the AHB view of the same address shows 1 — a cache-coherence
artefact that makes part of the earlier sampling unreliable.

## 6. Why they did not make the Darwin gate "sticky"

The obvious next step — latch the 1 inside Darwin so it survives idle packets — does not
fit: only 2 bytes are free in the vector table next to the existing cave, the 80-byte "NOP
zone" at `0xdf06` is actually a function called from `0xdfbe`/`0xdfcc`, and there are no
zero gaps inside the code. So the change moved to the source of the data in BIONZ.

## 7. Limits

- **The electronic shutter does not work.** Working result on hardware remains 3.23 (the
  2-byte Darwin patch in [13](13-darwin-shutter-patch.md)).
- It is not known what Darwin receives at the moment of the shot, nor what gate `0x4318`
  sees; reading Darwin's RAM (`0x20003716`) needs a probe on `CN4906` pins 11/12 (which are
  the BIONZ SWD lines, not Darwin's).
- In BIONZ the delay in the task call chain means `S+0x30..0x47` is only cleared at task
  start (`0x196fa`, called once from `0x1815c`); 24 call sites read `0x1b080`, and only
  `0x20c78`/`0x1fe6c` go through the cave.
- Three-state (MECHANICAL/EFCS/ELECTRONIC) was designed but not implemented: it would need
  a third persistent value, and the A6000 does not expose the Silent setting in the menu.
- Repeating their run means flashing a modified `nflasha3` — see [12](12-partition-format.md)
  for what that costs and [11](11-swd-recovery.md) for the way back.

## 8. Why it matters here

It answers, with code and measurements, the question our [10-open-questions.md](10-open-questions.md)
leaves open: the A6000's shutter mode is not a hidden enum waiting to be flipped. The body
has exactly two states in this path (EFCS on/off), the sensor takes its instructions from a
per-shot `ShutMode` field, and the mechanical suppression is a property of Darwin's own
configuration cell — which is why a 2-byte Darwin patch works and a 100-byte BIONZ feature
does not yet.

Reports: [E25-24](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-24-selector-efcs-electronico.md) (audit and blockers),
[E25-24b](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-24b-implementacion-selector.md) (implementation, caves, emulation),
[E25-26](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-26-c3b-exposicion-electronica.md) (C3-B),
[E25-27](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-27-construccion-firmware-integrado.md) (integrated build),
[R52](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r52-prueba-fisica-selector-327.md) / [R53](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r53-paquete-329-ajuste-efcs-en-vivo.md) (what the camera measured).
