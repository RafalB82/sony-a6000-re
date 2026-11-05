# 12 — Partition images: TPZL and the rules for changing one

[03](03-integrity-and-flashing.md) shows that a *unedited* Sony package can be
repacked byte-identically. This page is about the next step: changing the **content**
of a partition image. The format is undocumented, the decompressor is hardware, and
getting it wrong bricks the camera in a way no software check detects.

> **Source and status.** Reconstructed by
> [`nicolvus/a6000-fw-decomp`](https://github.com/nicolvus/a6000-fw-decomp) from
> `bootloader.bin` (Loader3 + ARM7 "BossFirm"), from Sony's GPL `cmpr.c`, and from a
> corpus of 16 Sony images (reports E26-R15, R16, R17, R30, R36, R39, R45; October–November 2026).
> Their labels are kept. **Not verified by us on hardware.** The only hardware
> confirmation in existence is indirect: a camera booted from an image rebuilt with these rules.

## 1. What TPZL is

Sony's compressed container for partition images (`nflasha3`, `nflasha15`, …).
There is no public specification and no sample outside Sony's own updates.

```
TOC (e.g. 369 blocks)  →  block  →  16 records × 4096 B
                                   ├─ stored:  0F 00 <u16 4096> + 4096 B
                                   └─ LZ77:    F0 …
```

## 2. The rules

| Rule | Value | Evidence |
|---|---|---|
| Block offset alignment | **512 B** (residue 0) | `cmpr_demand_wlen`, whole Sony corpus |
| Records per block | **always 16 × 4096 B** | ARM7 passes `block >> 12` to the LDEC |
| Max compressed block size | `(block/4096) × 4112 + 8` → **65 800 B** for 64 KiB | `cmpr.c` |
| Padding between blocks | `0x00`, not `0xFF` | Sony corpus |
| Sectors per read | **≤ 126** in `nflasha3`; > 128 makes the ARM7 split the read into two batches | Sony; Linux exercises the split in `nflasha15/16`, Loader3 never does |
| TOC entry sizes | multiples of 512 | Sony corpus |

## 3. The hardware path nobody models

```
Loader3 (BIONZ)  →  request structure  →  ARM7 (op 0)  →  LDEC (hardware decompressor)
```

- `c01fdd8e`: `residuo = offset & 0x1ff`. If it is non-zero Loader3 **only prints a
  warning** and reads whole sectors from `offset >> 9`, count
  `(residuo + size + 0x1ff) >> 9`.
- The work structure carries `{n, sector list, residuo (+8), registros = block>>12 = 16
  (+0xc), destino (+0x10), size}`.
- The ARM7 handler (`0x1338`, `0x3f4`) copies **`+0xc` (record count) and `+0x10`
  (destination)**. The residue field at `+8` is read by **no instruction**.

So with a 256-byte residue the stream handed to the LDEC starts 256 bytes *before* the
block, and nothing tells the hardware to skip them. Earlier reports treated "what the
silicon does with the residue" as undecidable; the decisive point is that **the residue
never reaches the silicon**.

## 4. How this bricked a camera

The 3.25 package differed from the working 3.23 in exactly one thing Loader3 reads:
`nflasha3`, rebuilt by their own encoder.

| Defect | Scale | Effect |
|---|---|---|
| Builder aligned to **256 B** | **359 of 369 blocks** with 256 B residue | 256 bytes of the previous block enter the LDEC stream |
| Blocks 0, 48, 57 emitted as **one 64 KiB record** (73 732 B) | 3 blocks | LDEC is programmed for 16 × 4096; the 65 800 B cap is exceeded |
| `0xFF` padding | 4 blocks | not what Sony emits |
| Blocks of **129 sectors** (> 128) in the first 3.25c attempt | 3 blocks | ARM7 splits the read in two — a path Linux uses in `nflasha15/16`, Loader3 never |

And every normal boot path hits a bad block: block 0 is the FAT boot sector; block 240
is the first RAMCFG entry (`\sabin`); `idt_cam.bin` 4/4 blocks, `sa_dfdet.bin` 4/4,
`av-cam.bin` 166/176, `initrd.img` 63/63, `vmlinux.bin` 55/55.

## 5. Why the offline checks passed

- Software decoders (`fwtool`, their own `tpzl.py`) **concatenate records** and ignore
  alignment and record geometry — the image "decompressed fine".
- The builder verified its output with **its own decoder** (a circular check).
- No verifier modelled `Loader3 → ARM7 → LDEC`. Only emulation with the real Loader3 and
  ARM7 code and a modelled LDEC reproduced the failure: **361/369 blocks** (Sony and the
  fixed image: 0).

## 6. What a valid image looks like

Corpus: **16 Sony TPZL images** (A6000 3.21, α7S 3.20, α6300 2.01, dumps from the
camera itself) = **19 489 blocks, 311 824 records**: every block is 16 × 4096 B and every
offset has residue 0, checked by two independent parsers. Stored records are used 4 556
times in `nflasha15`, where 162 blocks consist only of them (129 sectors) and Linux reads
them on every boot.

## 7. The safe way to change a partition

From their `scripts/e25_27/tpzl.py` (the fixed version):

1. Align to 512.
2. Touch as few 4096-byte pages as possible; for each affected block keep Sony's
   **original compressed records** for the pages you did not change and emit the changed
   page as a single stored record (`_splice`).
3. Pad with `0x00`; keep every block ≤ 126 sectors.
4. Recompute the CRC32 and size in `part_image.sum`.
5. Gate the build on a `hardware_violations()` check (residue ≠ 0, records ≠ 16 × 4096,
   size cap, sector cap) and refuse to emit an image that fails it.

Result in their case: 369/369 blocks clean, 30/30 checks, emulation 0/369 failures,
image 11 493 888 B against Sony's 11 489 040 B (partition 30 MiB). Then the hardware
confirmed it: firmware 3.27 (same payload, different version) booted, and Loader3 loaded
`\sabin\idt_cam.bin` where 3.25 had returned −302.

## 8. Limits

- **No UART confirmation is possible**: Loader3's console is muted by
  `Backup[0x510015]=0`, so `LD3_E`/`FAT_E`/`CFG_E` never leave the chip.
- The LDEC's behaviour with a residue was declared undecidable (R16/R17) and then
  irrelevant (R36) — but nobody measured what it does with the **last** block when the
  file does not end on a sector boundary.
- No TPZL sample exists outside Sony updates, so all format knowledge is inductive.
- A correct format does not make the payload work: 3.25c/3.27 boot, but their shutter
  patch still has no effect.

## 9. What it means for this repository

[03](03-integrity-and-flashing.md) answers "can a package be rebuilt" — yes, bit for bit,
as long as you do not change content. This page answers "can content be changed" — yes,
under the constraints in §2, and the cost of getting one of them wrong is exactly the
brick described in [11](11-swd-recovery.md), where the only way back was soldering to
the SoC.

Reports, in order: [R15](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r15-tpzl-custom-fw325.md) (Loader3 accepts the residue, warning only),
[R16](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r16-ldec-hardware-audit.md) / [R17](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r17-arm7-ldec-segment-analysis.md) (LDEC and ARM7),
[R36](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r36-causa-fallo-325.md) (root cause, corpus),
[R39](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r39-estatico-profundo.md) (emulation),
[R45](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r45-firmware-325c-experimental.md) (fixed builder, sector limit).
