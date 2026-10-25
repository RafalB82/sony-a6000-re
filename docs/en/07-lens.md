# 07 — Lens control

Two questions are covered here: what the firmware does with a lens, and why a manual
lens with no electronics gets no autofocus — and therefore no focus confirmation.

## 1. Three layers in the firmware

### Logic — `Camera::Lens`

Symbols in `av-cam.bin` (`/system`):

| Symbol / string | Meaning |
|---|---|
| `Camera::Lens::Initialize(UPM_BOOT_FACTOR*)` | lens subsystem init at boot |
| `ConnectLens`, `LENS_MOUNT`, `LENS_BARRIER` | detection / mount state / shutter barrier |
| `LensPowerState` | lens power state machine |
| `LensTempAD` | lens temperature via ADC |
| `"Wait E-MountLens ReduceVoltage Wait(%d ms)"` | **voltage negotiation with the lens** |
| `[LENS_PDR]: BonoboDSP_Send/Recv [ch0/ch1] paritycheck_error` | data transport |
| `"this lens is not permitted"` | lens gating |
| `"Scanless NG because of CenterOnlyLens"` | lens constrains sensor readout mode |

`LENS_PDR` is the packet layer that corresponds to the wire frames (see §3). Traffic
is relayed through `BonoboDSP` channels 0/1 with a parity check. Bonobo is the
stabiliser chip `R2J30503LG` — **A6000 does not ship `bonobo.bin`** (A6300 does), so
this code may be shared-but-inactive on this body. Unverified.

### Optical data — `Camera::Lens::ODL`

```
ODL::Alloc / Free / Load
ODL::AllocLensAberrationData / LoadLensAberrationData / FreeLensAberrationData
```

ODL is the optical data library: the body loads aberration data for the attached lens
and feeds it into the image pipeline:

```
[CAMERA_MAIN_YC]: DCV::job_YC_CalcParam: FocusPos/IrisPos/ZoomPos (Private/Public)
[CAMERA_MAIN_YC]: SHD::CalcLensShdGain, JudgeShdOn (LensShdOn, PzShdOn)
```

So lens positions are not only used to drive mechanics — they feed shading and
aberration correction in the DSP.

### Data files

| Where | What | Size |
|---|---|---|
| `0800_appli/lens/VX9101..VX9130_lensfile.bin` | 18 per-lens data files | 2–13 KB each |
| `nflasha3/lensbin_lensproperty/LensAberrationData.bin` | aberration database | 161 766 B |
| partition `nflasha18` = `/lens` | 20 MiB vfat | runtime lens data |

The `VX91xx` numbers are lens identifiers; the mapping to commercial model names is
not stored in the files.

## 2. A service tool that is already on the camera

`/usr/bin/adjstctl.elf` is an adjustment CLI:

```
<options> [adjust_block] [adjust_code] [size]:[data] ...
```

**~290 commands**, grouped by prefix: `A_` (138), `C_` (55), `S_` (102). Lens-related:

| Command | Effect |
|---|---|
| `S_LENS_INI`, `S_LENS_END`, `S_LENS_BARRIER` | start/stop lens subsystem |
| `S_LC_GET_ALENS_INFO` | **read lens information** |
| `S_LC_GET_ALENS_PINT_ADJ`, `S_LC_SET_ALENS_PINT_ADJ` | read/write lens adjustment points |
| `S_LC_SET_MOUNT_AORI` | mount orientation |
| `S_IRIS_INIT`, `S_IRIS_OPEN`, `S_IRIS_CLOSE_STDG`, `S_IRIS_CLOSE_MAXG`, `S_IRIS_MANU`, `S_IRIS_MANU_CMP` | **direct iris control** |
| `S_ZOOM_MOVIEREC`, `S_HYB_ZOOM_ONOFF` | zoom, hybrid zoom |
| `C_LENS_BARREL_STATUS`, `C_LM_LENS_TYPE` | barrel status, lens type |
| `A_TB_SET_LENS_INFO`, `A_TB_WRITE_LENS_QR_INFO`, `A_TB_LENS_POS_2E`, `A_LENS_TB`, `A_LENS_MR_RING_FC/ZM` | service data writes, MR rings |
| `A_SET_ZPD_LENS` | ZPD (AF) calibration with lens |
| `C_AF_ILUMI_ON/OFF`, `S_AF_ACT` | AF illuminator, AF activation |

It talks over `libosal_uipc.so` + `libtestcmd.so`, so it is usable from a root shell
(the telnet daemon that OpenMemories-Tweak can start).

⚠️ This is a **service/factory** tool. `A_*` commands write calibration data
(`WRITE_LENS_QR_INFO`, `SET_ALENS_PINT_ADJ`) and can ruin a calibration. `S_*` and
`C_*` look operational.

`/usr/scenario/CAMERA_SCN_SET_ZOOM_DRV.so` provides a second entry point to zoom.

## 3. The E-mount wire protocol (from logic-analyser dumps)

Source: `github.com/Entropy512/sigrok-dumps`, `lens_mounts/sony_emount/README`.
The captures were taken **on a Sony ILCE-A6000** — the same model.

### Contacts (viewed from the rear of a lens, 1 → 10)

| Pin | Signal | Function |
|---|---|---|
| 1 | `LENS_GND` | motor ground |
| 2 | `LENS_POWER` | motor power: **5.0 V or unregulated Vbat (7.4 V)**, negotiated |
| 3 | `LOGIC_GND` | logic ground |
| 4 | `BODY_VD_LENS` | unknown body→lens signalling; normally high, low pulses at ~60 Hz |
| 5 | `LOGIC_VCC` | **3.15 V** logic supply |
| 6 | `LENS_CS_BODY` | handshake; high while RXD transfers |
| 7 | `RXD` | data lens → body |
| 8 | `TXD` | data body → lens |
| 9 | `BODY_CS_LENS` | handshake; high while TXD transfers |
| 10 | `LENS_XDETECT` | lens presence; grounded by the lens. Body supplies power only when grounded |

### Frames

```
0xF0 | command ID | payload | CRC16 (LSB first) | 0x55
```

- 8N1, LSB first, **750 kbaud, negotiated up to 1.5 Mbaud** during init.
- One frame per CS-high period; frame length is fixed for a given command ID.
- `0x55` inside a frame is **not** escaped.
- At idle, a low pulse on `BODY_VD_LENS` triggers two status frames from the lens,
  then two from the body.

### Mapping to firmware

| Wire protocol | Firmware counterpart |
|---|---|
| 5 V vs Vbat negotiation | `LensPowerState`, `"Wait E-MountLens ReduceVoltage"` |
| `LENS_XDETECT` | `ConnectLens`, `LENS_MOUNT` |
| `0xF0…0x55` frames | `[LENS_PDR]` via `BonoboDSP` |
| lens capability reporting | `NID_LENS_INFORMATION` (see §4) |
| optical data | `ODL::LoadLensAberrationData` |

**Command IDs are not recoverable from strings.** Sony kept no names, and the public
dump documentation gives only the frame format. Recovering them requires disassembling
the `LENS_PDR` layer or making new captures with a custom decoder.

## 4. Manual lens (no electronics): what is required, what is possible

The decision point is in `lib/libObj.so` (`CamUser`/`CamMgr`). The body receives a
capability structure `NID_LENS_INFORMATION` from the lens and gates AF on its fields:

```
uc_AF_POSSIBLE / uc_AF_Impossible
uc_AF_A_Support, uc_AF_C_Support
uc_ContrastAF_Support
uc_DMF_Support, uc_Lens_DMF_sw_Support
uc_AFMF_sw_Support, uc_AFMF_sw_State
uc_PreAF_Support
uc_AF_AreaCenterOnly
uc_Lens_AFMFDMF_sw_Priority
```

Diagnostics confirm this is a live path:

```
[CAMUSER]: CamMgr) ##### NID_LENS_AF_POSSIBLE uc_AF_Impossible error[%d] #####
[CAMUSER]: CamMgr) ##### NID_LENS_INFORMATION uc_ContrastAF_Support error[%d] #####
```

The structure has **123 `uc_*` fields** and only `libObj.so` consumes it. **No lens →
no message → `uc_AF_Impossible`.**

### Conditions table

| # | Condition | Satisfiable without electronics? |
|---|---|---|
| 1 | lens detected (`LENS_XDETECT` → `ConnectLens`) | partially — the adapter grounds pin 10 |
| 2 | `NID_LENS_INFORMATION` received | ❌ nothing to send it |
| 3 | `uc_AF_POSSIBLE` + `uc_ContrastAF_Support` | ❌ |
| 4 | ability to drive the focus motor | ❌ |
| 5 | **`Release w/o Lens` = Enable** | ✅ the only user setting involved |

### What does work

These live in the view layer (`viewUnified2.so`), not in lens logic:

- **Focus Peaking** (`ACT_Peaking`, `…CustomPeakingLevel/Color`)
- **Focus Magnifier** (`…CustomFocusMagnifier`)
- **MF Assist**
- shooting — after `Release w/o Lens` is enabled

UI strings spell out the limits:

```
"Release w/o Lens" → Enable / Disable
"Makes shooting unavailable when the lens is not attached."
"Check that a lens is mounted."
"For an unsupported lens, set \"Release w/o Lens\" in the menu to \"Enable\"."
"Invalid because lens not attached."
"Focus Check Live View unavailable without lens attached."
```

### Why grounding XDETECT is not enough

Pin 10 only gates power. After power-up the body sends `0xF0…0x55` frames on `TXD` and
waits for answers on `RXD`. Without answers there is no `NID_LENS_INFORMATION`.

Adapters with a "chip" emulate a lens and report a fixed set of capabilities; that
unlocks exposure, metadata and sometimes stabilisation — but AF still cannot work,
because nothing can move the focus group (unless the adapter itself drives a motor, as
EF→E adapters do).

**Conclusion: focus confirmation with a fully manual lens cannot be enabled by any
setting or firmware patch.** It requires a closed AF loop, which requires a lens with a
motor and a protocol. The practical substitute is Focus Peaking plus the magnifier.
