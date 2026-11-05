# 13 — Darwin: the two bytes that stop the mechanical shutter

The "silent shutter" that works on a real A6000 is not a BIONZ patch. It is two bytes in
the firmware of **Darwin**, the power/mirror/shutter MCU (`IC5700`, `MB9AF004BGL`, a
Fujitsu FM3 Cortex-M3). This page reconstructs what those two bytes do and what they
leave alive.

> **Source and status.** From [`nicolvus/a6000-fw-decomp`](https://github.com/nicolvus/a6000-fw-decomp),
> reports E25 (mechanical deactivation), E24-05a/d, E25-02, E25-05 (packaging), plus
> T024/T040 camera tests. Their labels kept. The behaviour was confirmed on hardware
> (silent shot, no error); the *side effects* were not. **Not verified by us.**

## 1. The target

| Item | Value |
|---|---|
| File | `0640_darwin/darwin_core.bin`, 157 276 B |
| ROM base | `0x4200` — ROM address = file offset + `0x4200` |
| Own bootloader | `0x0–0x41ff` (separate from the application) |
| Version string | `VER0.78` at `0x25b3c` |

Darwin decides two things independently, and both read the **same cell**
`[0x20000050 + channel]` through `0x1b080`:

```
0x1b080   presence = [0x200002c0 + ch]; if 0 -> return 0
          byte = [0x20000050 + ch]
          high nibble (0..5, >=6 -> 0) = gate  : motor / re-cock allowed?
          low  nibble (bits 0..2)      = type  : coil drive P4D/P4E?
```

| Function | Reads | Controls |
|---|---|---|
| `0x20c74` | low nibble | coil type; four writers (`0x20c90/0x20cb2/0x20cd4/0x20d00`) consult it before touching P4D/P4E (`0x234`/`0x238`) |
| `0x1fe66` | high nibble | gate for the motor and the re-cock; **12 consumers** |

## 2. Why there is no "volatile" shortcut

The obvious idea — set that config byte at runtime instead of patching code — fails:

- **No static writer of `0x20000050` exists in `darwin_core`**: no literal for the
  address, no bit alias `0x22000a00`, and a scan for `str [rX,#0x50]` finds nothing real.
- `InitCom 0x12` writes a whole `0x78`-byte block from a `0x78`-aligned base; to reach
  `+0x50` you must send at least `0x51` bytes, including the watchdog fields at
  `+0x40..+0x43`.
- `InitCom 0x16` *would* do a 1-byte absolute write (`0x20000050`, length 1) — the only
  selective path in the code — but **no BIONZ sender of that frame is known**, and the
  COM task only exists during `Seton`, not during shooting.
- Darwin's SRAM is always powered: a normal power-off does not undo it.

## 3. Patch "type 0" — the coils

```text
0x20c74: ...            ; mechanism/coil type from the low nibble
0x20c78: 09 e0          b 0x20c8e        (was: bl 0x1b080 pattern)
0x20c7a: 00 bf          nop
0x20c7c: 00 bf          nop
0x20c7e: 00 bf          nop
```

`0x20c74` now always returns 0, which is an existing branch of the original code — the
"no coils" case. P4D/P4E are never driven. Installed as **3.22** (T024); the camera booted.

## 4. Patch "B1a" — the motor

```text
before:  0x1fe66: 70 b5        push {r4,r5,r6,lr}
         0x1fe68: 00 25        movs r5,#0
         0x1fe6a: 28 46        mov r0,r5        <- patched
         0x1fe6c: fb f7 08 f9  bl 0x1b080
         0x1fe70: 04 09        lsrs r4,r0,#4
         0x1fe72: 06 2c        cmp r4,#6
         0x1fe74: 05 d2        bhs 0x1fe82
         0x1fe76: df e8 04 f0  tbb [pc,r4]
         0x1fe82: 28 46        mov r0,r5
         0x1fe84: 70 bd        pop {r4,r5,r6,pc}

after:   0x1fe6a: 0a e0        b 0x1fe82        (2 bytes changed)
```

The branch jumps straight to the epilogue: the nibble is never read, `r5` stays 0, the
stack frame is intact. File offset `0x1b c6a` = 113770. Installed as **3.23** (T040):
the camera shot silently, without error, 36/36 frames.

## 5. What that changes downstream

The gate is consumed by 12 sites; with it returning 0:

| Site | Function | Effect |
|---|---|---|
| `0x1f5a2` | thunk of the three starters + 3 service pulses | all three pick list **L0** |
| `0x1f5a6` | direct re-cock | returns at `0x1f5ae`, motor never enabled |
| `0x1f4b6`, `0x1f4ce`, `0x1f572` | service pulse, cam check, cam read | skipped / return 0 |
| `0x1f88a`, `0x1f8fc`, `0x1fa3a`, `0x1fe86`, `0x201b0` | inner state machine, timeout, motor=2 | unreachable from L0, or no-op |

The three starters choose their state list from a table:

| Starter | Gate = 4 (normal) | Gate = 0 |
|---|---|---|
| `0x1fee2` (load) | `0x29cdd` = `[0,2,3,6,9,10]` (L1) | `0x29cd8` = `[0,7,8,9,10]` (**L0**) |
| `0x1ff72` (capture, state 4) | `0x29ce3` = `[0,4,5,6,9,10]` (L2) | L0 |
| `0x1ffce` (capture, state 5/0x1f) | `0x29ce9` = `[0,1,4,5,6,9,10]` (L3) | L0 |

L0 runs `0x20100` (mark busy, wait `0x8ca0`), `0x2014c` (calls `0x20c90`, wait `0x5dc0`),
`0x200e2` (wait/end), `0x200e6` (`0xd18e(0x1000000)`, releases occupancy) and `0x200fc`
(end). The inner 27-state machine is only started from outer states 2 and 4
(`0x20126`/`0x2013a`), which L0 does not contain.

**Type 0 is mandatory, not optional:** state 7 of L0 still calls `0x20c90`, i.e. it still
tries to write P4D — the gate does not filter coils, only the motor. Without type 0 that
write would land.

## 6. What stays alive

| Item | State | Comment |
|---|---|---|
| **Operation 5 (brake)** | active | `0x1f600 → 0x1fcb8 → 0x1feb6` writes P40=P41=1 (`PDOR4 0x51cc`, `r1=3`, `r2=0xfffc`), no gate. With the XOR gate the schematic actually has ([16](16-service-manual.md) §5.3), `1⊕1 = 0`, i.e. no drive — the word "brake" is an interpretation, not a reading of the schematic. Physical effect never measured |
| `P4B` (`0x22c`, bit 11) | active | occupancy signalling, mask `0x800` |
| `P4C` (`0x230`) | active | set/cleared per shot via `0x1ecec`; corrects an earlier claim that only zero was written |
| Error 6 at `0x1989c` | active | ADC position check; can queue operation 5, cannot move the motor by itself |

So the correct claim is narrower than "the shutter is dead": **no drive of the motor and
no coil pulse in capture and re-cock**, with an emergency brake still wired in.

## 7. Limits

- **No independent recovery** if a patched Darwin does not boot: the same MCU controls
  power. This is why the patch is only 2 bytes and why nothing else in Darwin is touched.
- The watchdog has not been shown to tolerate L0's duration (`0x8ca0 + 0x5dc0` ticks, tick
  unit unmeasured).
- Untested on hardware: flash, video, Live View under the patch; operation 5; P4B/P4C
  consumers (no local consumer located in the SoC).
- Everything above is reachability analysis plus the model of the service-manual circuit;
  the physical stillness is inferred from 36 silent shots and one RAW analysis, not from
  probing P40/P41.

## 8. Why it matters here

Our [01-hardware.md](01-hardware.md) lists `IC5700 = MB9AF004BGL` "Darwin" as the power IC
that boots the SoC. This is the same part, and the patch explains the shutter: the MCU is
a real controller with its own state machine, not a power sequencer only. It also gives
the concrete GPIO names (P40/P41 motor, P4D/P4E coils, P4B/P4C occupancy) that our
[01](01-hardware.md) and [02](02-firmware-layout.md) documents do not carry.

Reports: [E25](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-desactivacion-mecanica.md) (mechanism, 12 consumers, matrices),
[E25-05](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-05-preparacion-paquetes-323-324.md) (packaging 3.23/3.24),
[E24-05a](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e24-05a-captura-fin-bionz-darwin.md) (BIONZ↔Darwin protocol),
[darwin-shutter-entrypoints](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/darwin-shutter-entrypoints.md) (Ghidra base `0x4200`, ADC mapping).
