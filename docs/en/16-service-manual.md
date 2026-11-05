# 16 — The service manual: sheet map, debug access, shutter wiring

The Level 3 service manual is the only source for the electrical layer the firmware cannot
show: which ball of the SoC the debug port sits on, which parts are not fitted, and how the
two curtain magnets and the re-cock motor are actually driven. This page is a working map of
it, not a copy.

> **Source.** *SERVICE MANUAL LEVEL 3, ILCE-6000/6000L/6000Y*, rev 1.1, 54 pages, created
> 2014-02-17, SHA-256 `4ab1630bffdba4aff01fa5934b8a1f3fe4bb54f4fefd6a7c19192836bda31aa5`
> (iFixit archive; a hash-identical copy at photo-parts.com.ua). **Not redistributed here** —
> the page numbers below are the map. Every pin table here was re-read from the PDF with
> `pdftotext -bbox` (word coordinates), not from OCR of a screenshot.

## 1. How to read it

- Schematic sheets carry a sheet id `6-N` in the title block; **PDF page = N + 12**
  (sheet `6-11` is page 23). Chapter 4 (pages 7–12) holds the block diagrams.
- The title block (bottom right) gives board, sheet fraction and function, e.g.
  `SY-1028 BOARD (8/23) / POWER CONTROL, MECHANISM CONTROL / 6-11`.
- **`pdftotext -layout` silently drops whole blocks** on dense sheets — the JTAG/eFuse block
  of page 26 and the net `XRESET_CR` of page 24 are absent from such a dump. Use
  `pdftotext -bbox` (coordinates), `pdftocairo -svg`, or `pdftoppm -r 600`, and pair pins with
  nets by row and column position.
- `XX` in the notes means **not fitted** in this board variant (`XX MARK: NO MOUNT`). It is a
  variant statement, not a statement about a specific camera.

## 2. Sheet map

| Pages | Sheet | Board / function |
|---|---|---|
| 1–2 | — | cover, safety check-out |
| 3–6 | — | parts list (BOM), including the board-level assemblies |
| 7–12 | 4-1 … 4-4 | **block diagrams**: overall (p7), boards, video/audio and power distribution |
| 13 | 6-1 | chapter 6 divider |
| 14 | 6-2 | `IS-095` — CMOS imager board |
| 15 | 6-3 | IS↔SY connection (printed wiring omitted) |
| 16–38 | 6-4 … 6-26 | **`SY-1028` main board, 23 sheets** (see below) |
| 39–41 | 6-27 … 6-29 | `ST-1018` flex — flash drive, battery terminal, connectors |
| 42 | 6-30 | `FP-2045` / `MIS-2000` — multi-interface shoe |
| 43–46 | 6-31 … 6-34 | **`CN-1027` shutter board, 4 sheets**: connector, card slot, **shutter drive**, DC/DC |
| 47 | 6-35 | `LC-1018` — LCD |
| 48 | 6-36 | `RL-1024` — control keys |
| 49–54 | 6-37 … 6-41 | board layouts / printed wiring views |

`SY-1028` in detail: 1 connectors · 2–4 DC/DC · 5 connectors · 6 B+ switch · 7 USB power ·
**8 power control, mechanism control (Darwin)** · 9–12 CPU, camera DSP, AV signal process,
lens control, HDMI (IC6000 is drawn here across 7 blocks, `(1/7)`…`(7/7)`) · 13 signal
process · 14 lens interface · **15 charge motor drive, anti-dust drive** · 16 WLAN · 17 NFC ·
18 LED drive, slant sensor · 19 connectors · 20 audio processor · 21 not used · 22 HDMI, multi
terminal · 23 connectors.

The four pages that matter for firmware work: **23** (Darwin), **26** (IC6000 debug block),
**37** (Multi terminal), **38** (CN4906), **45** (shutter drive), **30** (charge motor).

## 3. Debug access

### 3.1 IC6000 (BIONZ X) — sheet 6-14, page 26, block `(4/7)`

| Signal | Ball | Connection |
|---|---|---|
| TDI | G25 | tied to `D_3.15V_MSS` |
| TCK | H25 | tied to `D_3.15V_MSS` |
| TMS | F26 | tied to `D_3.15V_MSS` |
| TDO | F25 | no service trace |
| RTCK | G26 | no service trace |
| NTRST | H26 | net `XRESET_CR` — the same net as the chip's own reset input (`XRESET`, ball K6, via `R6000` = XX) |
| FUSE_EN | T12 | tied to `D_3.15V` (normal: the chip reads its fuses at boot) |
| FUSE_CLK | R12 | no net on this sheet |
| **SWCLK** | **W25** | free, reaches the service footprint through `R4911` (XX) |
| **SWDIO** | **W26** | free, reaches it through `R4912` (XX) |

Reading: classic JTAG is unusable (three of five lines strapped high), and there is no
JTAG-only reset — `NTRST` is the SoC reset. Only SWD is left, and only through two pads.

### 3.2 CN4906 — service footprint, 18 pins, sheet 6-26, page 38

| Pin | Net | Pin | Net |
|---|---|---|---|
| 1 | REG_GND | 10 | RTCK (no net) |
| 2 | BOOT_MODE_1 | 11 | **TCK(SWCLK)** — BIONZ `SWCLK` + Darwin `TCK_DWN` |
| 3 | EVER_3.15V | 12 | **TMS(SWDIO)** — BIONZ `SWDIO` + Darwin `TMS_DWN` |
| 4 | UART_RXD_MSS (BIONZ UART0) | 13 | TDI (Darwin `TDI_DWN`) |
| 5 | UART_TXD_MSS | 14 | NTRST (Darwin `TRST_DWN`) |
| 6 | UART_RXD_DWN (Darwin) | 15 | DEBUG_MODE — `VIO_FLD` + Darwin `XDWN_RESET` |
| 7 | UART_TXD_DWN | 16–18 | REG_GND |
| 8 | NSRST (Darwin `MD0_DWN`) | | |
| 9 | TDO (Darwin `TDO_DWN`) | | |

`CN4906` itself is marked **XX** (footprint only), and the Darwin-side signals reach it
through unpopulated islets `CL701`–`CL707` on sheet 6-11. So this footprint is not a BIONZ
port: it is a combined BIONZ + Darwin debug header, and pins 11/12 are a **shared node**
between the BIONZ SWD pads and Darwin's `TCK`/`TMS` — which is why probing SWD can disturb
the power MCU.

### 3.3 CN4001 — Multi terminal, 15 + 4 pins, sheet 6-25, page 37

1 `USB_VBUS` · 2 `USB_D-` · 3 `USB_D+` · 4 `USB_ID` · 5 `GND` · 6 `D_3.1V/LANC_DC`
(`R4001` XX) · 7 `XRESET_REQ` (`R4008` XX) · 8 `UART_TX/LANC_SIG` (`CM4008` fitted) ·
9 `UART_RX/BOOT_IN` (`R4002`/`R4003` XX, bridged to pin 10 by `CM4002` fitted) ·
10 `AD_JACK_IN` (`CM4003` fitted) · 11 `ROUT/XAELOCK` · 12 `LOUT/XSHUT` (`R4004` XX) ·
13 `VIDEO` · 14 `AV_GND` · 15 `XPWR_ON` · 16–19 shield/`REG_GND`.

So the BootROM serial line does reach the Multi terminal as a *documented intention* only:
both series resistors are not fitted.

## 4. BIONZ ↔ Darwin: the links that carry the shutter protocol

Nets on sheet 6-11 (`IC5700`, `MB9AF004BGL-G-103-ERE1`):

| Net | Direction | Role |
|---|---|---|
| `MSS_SCK_DWN`, `MSS_SI_DWN`, `MSS_SO_DWN` | BIONZ → Darwin | **SPI clock / data** — this is the physical transport of the 22-byte `0x0c` packet that carries `pkt[0x0e]` |
| `DWN_CSREQ_MSS`, `DWN_CSDIR_MSS` | both | chip-select / direction handshake |
| `CA_1ST_CURTAIN_START` | BIONZ → Darwin | "start the sequence" command |
| `CA_RELEASE_LOCK_MSS` | BIONZ → Darwin | release lock |
| `CA_XRESET_OUT_MSS` | BIONZ → Darwin | resets Darwin |
| `DWN_USB_SEL`, `USB_D+_DWN`, `USB_D-_DWN` | both | Darwin's own USB (the `054c:0994` charger interface) |
| `UART_RXD_DWN` / `UART_TXD_DWN` | both | Darwin console, only on CN4906 6/7 |

Consequence for the electronic-shutter work: the mode byte never reaches Darwin because of
what happens on the **SPI** link, not a UART. A logic-analyser tap for that question belongs
on `MSS_SCK_DWN`/`MSS_SI_DWN`, i.e. on the SY-1028 board, not on the service footprint.

## 5. The shutter wiring

### 5.1 Path

```
Darwin IC5700 (SY-1028, sheet 6-11)
   1ST_CURTAIN_MG / 2ND_CURTAIN_MG / SHUTTER_PI_ON ─┐
   SHUTTER_PI (ADC) / SHUTTER_ID ◄──────────────────┤
                                                    ▼
                        CN4900 (61-pin flex) on SY-1028, sheet 6-26
                        pins 9 / 11 / 10 · 8 / 4 · 7 · 12–15 (SHUTTER_5.5V)
                                                    ▼
                        CN-1027 board, sheet 6-33 "SHUTTER DRIVE"
                        Q6830 / Q6831 (RN1102MFV) · Q6832 (MTM765200LBF, XX)
                        D6830 / D6831 (zeners) · R6830/R6831 100k · R6832 4.7k · R6834 100
                                                    ▼
                        CN302 (10-pin) → shutter unit
```

### 5.2 CN302 to the shutter unit (sheet 6-33)

| Pin | Net | Meaning |
|---|---|---|
| 1 | 1C | first-curtain magnet |
| 2, 3 | COMMON | `SHUTTER_5.5V` |
| 4 | 2C | second-curtain magnet |
| 5 | PI-A | photo-interrupter LED anode |
| 6 | PI-K | LED cathode |
| 7 | PI-E | phototransistor emitter |
| 8 | PI-C | phototransistor collector |
| 9 | ID | `SHUTTER_ID` — identity resistor read by Darwin |
| 10 | GND | ground |

The shutter is therefore **two electromagnets at 5.5 V** plus a 4-wire optical position
sensor, all driven from a small board (`CN-1027`) that is separate from the main board.

### 5.3 The re-cock motor (sheet 6-18, page 30)

`SC_M_1` / `SC_M_2` from Darwin feed `IC6800 = TC7SH86FU`, a **2-input XOR**. Its output
`OUT_Y` drives `Q6800` (`RN1102MFV`) and `Q6801` (`US6M2GTR`, XX) into `CN1800` (16-pin)
`CM+` / `CM-`, i.e. the charge (re-cock) motor inside the `MB CHARGE UNIT`, with
`CM_TEMP` brought back on `CHARGE_MOTOR_TEMP`.

This is worth stating precisely, because it corrects a reading of the firmware work: with an
XOR, `P40 = P41 = 1` gives `OUT_Y = 0`, i.e. **no drive**, not a commanded brake. Whether the
motor is shorted (braking) depends on the driver stage, not on the gate; nothing in the
schematic says the emergency operation 5 applies a brake.

## 6. What the manual does not give

- **The debug-lock eFuse value.** `FUSE_EN` strapped high is the normal "read my fuses" wiring;
  what is programmed into the fuse is not in any file.
- **A full CXD90014 pin table.** Ports that are multiplexed are named by function
  (`GPIO_S_0..16`, `GPIO_SB_0..6` only); the ball for e.g. port 14 does not exist in the
  document.
- **A separate NAND chip.** `IC6000` is a package with stacked memory (page 27 shows
  POP/LPDDR2 connections); there is no discrete NAND with a part number and pinout, which is
  why an external NAND dump means lifting the SoC.
- **Population per unit.** `XX` describes the variant. Whether a given camera has `R4911`
  fitted, or `CN4906` present, is a continuity measurement.
- **Firmware semantics.** Nothing about `ShutMode`, `r5`, `pkt[0x0e]`.

## 7. What it is good for

1. **Choosing a probe point.** Re-cock motor current at `CN1800 CM+/CM-`; curtain magnets at
   `CN302` pins 1/4; the PI at pins 5–8; `SHUTTER_5.5V` at pin 3.
2. **Answering "is the mechanism moving?"** without guessing from sound: the magnets are
   driven by two digital transistors, so a scope on `1ST/2ND_CURTAIN_MG` shows intent and
   `CN302` shows the load.
3. **Explaining the software map**: `P4D`/`P4E` (the writers at `0x234`/`0x238` in Darwin) line
   up with the two curtain magnets; `P40`/`P41` with the charge motor through the XOR; the ADC
   channel read from `SHUTTER_PI` is the mechanism position the firmware calls `ShutPIAdValue`.
4. **Repair/BOM**: `IC5700 MB9AF004BGL-G-103-ERE1`, `IC6200 CXD90027GF`, `IC6000 MHZ4G8G01A`,
   `IC6800 TC7SH86FU`, `Q6800/Q6830/Q6831 RN1102MFV`, `Q6801 US6M2GTR`, `Q6832 MTM765200LBF`.

## 8. Corrections to our own notes

- [01-hardware.md](01-hardware.md) says the manual has "5 sheets" — it has **54 pages**, and
  the relevant part is 23 sheets of `SY-1028` plus 4 of `CN-1027`.
- The Darwin part is `MB9AF004BGL-G-103-ERE1` (ordering code), and its sheet is 6-11, not the
  power-supply pages where our note places it.
- Our note that the shutter is "Darwin + coils" can now be specific: two 5.5 V magnets on a
  separate board, a 4-wire PI, and a re-cock motor behind an XOR gate.

Source records: page text extracted with `pdftotext -bbox` from the hash-verified PDF;
cross-checked against the pinout work published in `nicolvus/a6000-fw-decomp`
(E26-R29 for CN4001/CN4906, E26-R42 for the ball map), which agrees on every pin compared.
