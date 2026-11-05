# 15 — What the silent shutter actually gives: row-by-row exposure

The 2-byte Darwin patch in [13](13-darwin-shutter-patch.md) stops the mechanism, but it does
not make the exposure uniform. Without a rear curtain each row keeps integrating light
until it is read, so the bottom of the frame gets more light than the top. This was
measured — twice, with two independent methods — and then corrected in RAM.

> **Source and status.** From [`nicolvus/a6000-fw-decomp`](https://github.com/nicolvus/a6000-fw-decomp):
> E25-10 (row-by-row fit on 19 ARW files), E25-17 (speed matrix, long exposure),
> T044/T046/T047/T050 camera tests, wiki page 6. Their labels kept. **Not verified by us.**

## 1. The measurement

Camera on 3.23, ISO 100, RAW 6024×4024, mode M, 10 shutter speeds × 2. Each frame was cut
into 32 row bands of ≈126 rows and fitted per band:

```
linear_b(T) = s_b · (T + τ_b)
```

`s_b` is the scene brightness (unknown per band, which removes the scene from the problem),
`T` the set shutter speed, and `τ_b` the exposure the speed does **not** control.

| Result | Value |
|---|---|
| Additive fit `T + τ` per band | R² ≥ 0.988 in all 32 bands; max error 17 % (top bands, low signal), 7 % elsewhere |
| τ, top band | **7.3 ms** (8.1 ms measured once) |
| τ, bottom band | **66.6 ms** |
| Ramp of τ with row | **linear, ≈15.2 µs per row** (1.91 ms per band, ≈59 ms top to bottom) |
| Alternative model "effective time = max(T, floor)" | residual 6.9× larger — **rejected** |

So the exposure of row *i* is:

```
E_i = T + 7 ms + 15.2 µs · i          readout ≈ 61 ms (15.2 µs × 4024 rows; ≈64 ms with 4243 lines)
```

At fast speeds that is why the frame barely darkens with shutter speed: between 1/4000 and
1/500 the constant dominates, and the bottom receives 3.7× the light of the top (0.095 →
0.350 relative to 1/8).

**It is not a bug of the patch.** T025 (3.22, before B1a, JPEG) already showed the same flat
floor between 1/4000 and 1/250 and the rise from 1/125. B1a only stops the mechanism; the
gradient is what a rolling readout looks like with no curtain to cut it.

## 2. The fix, measured in RAM

T046 forced two fields in BIONZ RAM (`ShutMode` at `0x836d6fb6`, `r5` at `0x836d7000`) and
kept three unpatched references to calibrate the scene. Exposure = 1000·RAW/scene, at 1/250:

| `r5` | Mean exposure | Across eighths |
|---|---|---|
| unforced | 64.9 ms | 65.0 … 65.0 |
| 0 | ≈0 (black) | — |
| 1000 | 49.1 ms | 49.2 … 49.2 |
| 2000 | 33.8 ms | 33.9 … 33.8 |
| 3000 | 18.5 ms | 18.7 … 18.5 |
| 3500 | 10.9 ms | 11.1 … 11.0 |
| 4000 | 3.3 ms | 3.4 … 3.4 |
| 4100 | 1.8 ms | 1.9 … 1.8 |
| 4200 | 0.3 ms | 0.3 … 0.3 |
| 4300 | 64.9 ms | no effect |

Three things follow, all measured:

1. **`ShutMode 0` exposes every row for the same time** (±0.2 ms across eighths): it is a
   per-row reset, not a global reset followed by a readout.
2. **`r5` sets the exposure in lines: `E = (4219 − r5) × 15.2 µs`.** The measured slope
   (−15.2 µs per unit) is the same 15.2 µs/row found independently in §1 — which is the
   strongest evidence that `r5` is a distance between reset and readout, not an arbitrary
   register.
3. At 1/30 the same `r5` values give the same exposures as at 1/250: **with `ShutMode 0` the
   set shutter speed does not take part.**

T047 then predicted `r5` from the target speed (4219 − T/15.2 µs) and checked it:
4203 → 0.24 ms, 4153 → 0.99 ms, 3956 → 4.03 ms, 3122 → 16.75 ms. Linearity holds within 3 %;
the absolute scale carries ±20 % (≈±25 % against a single reference), which is a calibration
problem, not a law problem.

## 3. What that means in practice

| Use | With 3.23 alone | With layer 2 (RAM) |
|---|---|---|
| 1/4000 – 1/500 | gradient up to 3.7× top-to-bottom | uniform, 0.25–4 ms |
| 1/250 – 1/60 | still noticeable | uniform, 4–16.7 ms |
| 1/30 and slower | gradient small relative to T | uniform down to 1/30; **from 1/15 the camera falls back to normal shooting** |
| 1/8000 | — | emulated only |
| Moving subjects | skewed (≈61 ms readout) | skewed the same way |
| BULB / >1/8 | not available | not implemented |

So "silent shutter works" is true and conditional: static subject, moderate shutter speeds,
or the RAM patch with a PC attached. The rolling effect is inherent — 61 ms of readout is
three to four times slower than a mechanical curtain.

## 4. Layer 2 as it is actually used

- It is a **RAM patch only**: `ShutMode` and `r5` are written over telnet (OpenMemories
  Tweak → telnetd on port 23) before each shot or burst, and reverted after. Nothing touches
  NVRAM, `nflasha3` or flash; a reboot clears it.
- A **watchdog on the camera** reverts the bytes after 25 s if the PC stops responding.
- T050: 12 shots plus a burst of 4, between 1/4000 and 1/30, always reverted correctly.
- **The camera-side version failed for process reasons, not logic:** in T049 the app patched
  and reverted correctly on 6 shots, but `RandomAccessFile` cannot address `/dev/mem` above
  2 GiB, and `Runtime.exec("dd")` from a ~100 MB process with ~8 MB free hung the `fork`
  **between the two writes**, leaving `ShutMode 0` forced. Their conclusion: never call
  `Runtime.exec` from the app during a shot; talk to the local telnetd instead, and apply
  both writes in one command.

## 5. Long exposure is a different problem

The ~65 ms ceiling belongs to the **manual `r5` route**, not to the firmware: the native
producer `0x4383fa40` already plans 1/15 s … 30 s by returning `shd = 1` (the floor),
`svd = N−1` extra whole frames and an extended VTS for the remainder frame (1 s → `svd 14`,
30 s → `svd 472`). BULB is timed by the host in one-frame slices (`0x438c74b0`,
`bulbFrameCount = cap+0x72c`). What is missing is a mechanical-shutter-free long exposure
that ends correctly, not the arithmetic — so this remains unimplemented in the r5 design.

## 6. Limits of the evidence

- One scene, one framing, ISO 100, mode M, 1/4000–1/8; RAW not corrected for vignetting or
  lens falloff (assumed constant and absorbed by `s_b`).
- No moving-subject measurement: the skew is inferred from the readout time, not from
  images of fast objects.
- Absolute exposure scale ±20–25 %; the *ratios* between speeds are good to ~3 %.
- Flash, video and Live View with the patch active were never measured.

## 7. Why it matters here

It converts "silent shutter" from a claim into a spec: **no rear curtain, 7 ms fixed
latency, 15.2 µs per row, ≈61 ms readout**, uniform only if BIONZ is told to do a per-row
reset. Any comparison with a camera that has a real electronic shutter should start from
those four numbers, and any experiment that expects a uniform frame from the Darwin patch
alone will measure a 3.7× gradient and think the patch failed.

Reports: [E25-10](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-10-exposicion-por-fila.md) (32-band fit, T044),
[E25-17](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-17-bulb-exposicion-electronica-larga.md) (1/8000…30 s, BULB),
[E25-18](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-18-integracion-silent-todas-velocidades.md) (C3-B),
[T046/T047](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-19-verificacion-fisica-exposicion-larga.md) (r5 law, prediction check),
[wiki 6](https://github.com/nicolvus/a6000-fw-decomp/wiki/en-6-Layer-2-uniform-exposure) (layer 2 recipe).
