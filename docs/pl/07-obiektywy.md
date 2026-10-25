# 07 — Sterowanie obiektywem

Dwa pytania: co firmware robi z obiektywem oraz dlaczego obiektyw manualny bez
elektroniki nie dostaje autofokusa — a więc i potwierdzenia ostrości.

## 1. Trzy warstwy w firmware

### Logika — `Camera::Lens`

Symbole w `av-cam.bin` (`/system`):

| Symbol / string | Znaczenie |
|---|---|
| `Camera::Lens::Initialize(UPM_BOOT_FACTOR*)` | inicjalizacja podsystemu przy starcie |
| `ConnectLens`, `LENS_MOUNT`, `LENS_BARRIER` | wykrycie / stan gniazda / bariera spustu |
| `LensPowerState` | maszyna stanów zasilania obiektywu |
| `LensTempAD` | temperatura obiektywu przez ADC |
| `"Wait E-MountLens ReduceVoltage Wait(%d ms)"` | **negocjacja napięcia z obiektywem** |
| `[LENS_PDR]: BonoboDSP_Send/Recv [ch0/ch1] paritycheck_error` | transport danych |
| `"this lens is not permitted"` | gating obiektywów |
| `"Scanless NG because of CenterOnlyLens"` | obiektyw ogranicza tryb odczytu matrycy |

`LENS_PDR` to warstwa pakietów odpowiadająca ramkom przewodowym (patrz §3). Ruch jest
przekazywany przez kanały 0/1 `BonoboDSP` z kontrolą parzystości. Bonobo to układ
stabilizacji `R2J30503LG` — **A6000 nie dostarcza `bonobo.bin`** (A6300 tak), więc ten
kod może być wspólny, ale nieaktywny na tym korpusie. Niesprawdzone.

### Dane optyczne — `Camera::Lens::ODL`

```
ODL::Alloc / Free / Load
ODL::AllocLensAberrationData / LoadLensAberrationData / FreeLensAberrationData
```

ODL to biblioteka danych optycznych: aparat ładuje dane aberracji dla podłączonego
obiektywu i podaje je do potoku obrazu:

```
[CAMERA_MAIN_YC]: DCV::job_YC_CalcParam: FocusPos/IrisPos/ZoomPos (Private/Public)
[CAMERA_MAIN_YC]: SHD::CalcLensShdGain, JudgeShdOn (LensShdOn, PzShdOn)
```

Czyli pozycje obiektywu nie tylko napędzają mechanikę — zasilają korekcję vignetowania
i aberracji w DSP.

### Pliki danych

| Gdzie | Co | Rozmiar |
|---|---|---|
| `0800_appli/lens/VX9101..VX9130_lensfile.bin` | 18 plików per-obiektyw | 2–13 KB każdy |
| `nflasha3/lensbin_lensproperty/LensAberrationData.bin` | baza aberracji | 161 766 B |
| partycja `nflasha18` = `/lens` | 20 MiB vfat | dane obiektywów w runtime |

Numery `VX91xx` to identyfikatory obiektywów; mapowanie na nazwy handlowe nie jest
zapisane w plikach.

## 2. Narzędzie serwisowe, które jest już w aparacie

`/usr/bin/adjstctl.elf` to CLI adjustacyjne:

```
<options> [adjust_block] [adjust_code] [size]:[data] ...
```

**~290 komend**, grupowanych prefiksami: `A_` (138), `C_` (55), `S_` (102).
Z obiektywem związane:

| Komenda | Efekt |
|---|---|
| `S_LENS_INI`, `S_LENS_END`, `S_LENS_BARRIER` | start/stop podsystemu obiektywu |
| `S_LC_GET_ALENS_INFO` | **odczyt informacji z obiektywu** |
| `S_LC_GET_ALENS_PINT_ADJ`, `S_LC_SET_ALENS_PINT_ADJ` | odczyt/zapis punktów adjustacji |
| `S_LC_SET_MOUNT_AORI` | orientacja gniazda |
| `S_IRIS_INIT`, `S_IRIS_OPEN`, `S_IRIS_CLOSE_STDG`, `S_IRIS_CLOSE_MAXG`, `S_IRIS_MANU`, `S_IRIS_MANU_CMP` | **bezpośrednie sterowanie przysłoną** |
| `S_ZOOM_MOVIEREC`, `S_HYB_ZOOM_ONOFF` | zoom, zoom hybrydowy |
| `C_LENS_BARREL_STATUS`, `C_LM_LENS_TYPE` | stan tubusu, typ obiektywu |
| `A_TB_SET_LENS_INFO`, `A_TB_WRITE_LENS_QR_INFO`, `A_TB_LENS_POS_2E`, `A_LENS_TB`, `A_LENS_MR_RING_FC/ZM` | zapis danych serwisowych, pierścienie MR |
| `A_SET_ZPD_LENS` | kalibracja ZPD (AF) z obiektywem |
| `C_AF_ILUMI_ON/OFF`, `S_AF_ACT` | iluminator AF, aktywacja AF |

Komunikacja przez `libosal_uipc.so` + `libtestcmd.so`, więc jest używalne z root shella
(demon telnet, który potrafi uruchomić OpenMemories-Tweak).

⚠️ To narzędzie **serwisowe/fabryczne**. Komendy `A_*` zapisują dane kalibracyjne
(`WRITE_LENS_QR_INFO`, `SET_ALENS_PINT_ADJ`) i mogą rozjechać kalibrację. `S_*` i `C_*`
wyglądają operacyjnie.

`/usr/scenario/CAMERA_SCN_SET_ZOOM_DRV.so` daje drugie wejście do zoomu.

## 3. Protokół przewodowy E-mount (z dumpów analizatora logicznego)

Źródło: `github.com/Entropy512/sigrok-dumps`, `lens_mounts/sony_emount/README`.
Dumpy zrobione **na Sony ILCE-A6000** — tym samym modelu.

### Styki (widok od tyłu obiektywu, 1 → 10)

| Pin | Sygnał | Funkcja |
|---|---|---|
| 1 | `LENS_GND` | masa silnika |
| 2 | `LENS_POWER` | zasilanie silnika: **5,0 V albo nieuregulowane Vbat (7,4 V)**, negocjowane |
| 3 | `LOGIC_GND` | masa logiki |
| 4 | `BODY_VD_LENS` | nieznane; zwykle high, impulsy low ~60 Hz |
| 5 | `LOGIC_VCC` | **3,15 V** logika |
| 6 | `LENS_CS_BODY` | handshake, high podczas transmisji RXD |
| 7 | `RXD` | dane obiektyw → body |
| 8 | `TXD` | dane body → obiektyw |
| 9 | `BODY_CS_LENS` | handshake, high podczas TXD |
| 10 | `LENS_XDETECT` | obecność obiektywu; zwierany do masy. Body podaje zasilanie tylko wtedy |

### Ramki

```
0xF0 | ID komendy | payload | CRC16 (LSB first) | 0x55
```

- 8N1, LSB first, **750 kbaud, negocjowane do 1,5 Mbaud** przy inicie.
- Jedna ramka na impuls CS; długość ramki stała dla danego ID.
- `0x55` w payloadzie **nie jest escapowane**.
- W idle impuls low na `BODY_VD_LENS` wywołuje dwie ramki statusu z obiektywu, potem
  dwie z body.

### Odwzorowanie na firmware

| Protokół | Odpowiednik w firmware |
|---|---|
| negocjacja 5 V vs Vbat | `LensPowerState`, `"Wait E-MountLens ReduceVoltage"` |
| `LENS_XDETECT` | `ConnectLens`, `LENS_MOUNT` |
| ramki `0xF0…0x55` | `[LENS_PDR]` przez `BonoboDSP` |
| raportowanie zdolności | `NID_LENS_INFORMATION` (patrz §4) |
| dane optyczne | `ODL::LoadLensAberrationData` |

**ID komend nie da się odzyskać ze stringów.** Sony nie zostawił nazw, a publiczna
dokumentacja dumpów podaje tylko format ramki. Odzyskanie wymaga disassembly warstwy
`LENS_PDR` albo nowych dumpów z własnym dekoderem.

## 4. Obiektyw manualny (bez elektroniki): co jest wymagane, co możliwe

Punkt decyzyjny jest w `lib/libObj.so` (`CamUser`/`CamMgr`). Aparat dostaje strukturę
zdolności `NID_LENS_INFORMATION` i na jej polach opiera dostępność AF:

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

Diagnostyka potwierdza, że to żywa ścieżka:

```
[CAMUSER]: CamMgr) ##### NID_LENS_AF_POSSIBLE uc_AF_Impossible error[%d] #####
[CAMUSER]: CamMgr) ##### NID_LENS_INFORMATION uc_ContrastAF_Support error[%d] #####
```

Struktura ma **123 pola `uc_*`** i tylko `libObj.so` ją konsumuje. **Brak obiektywu →
brak komunikatu → `uc_AF_Impossible`.**

### Tabela warunków

| # | Warunek | Spełnialne bez elektroniki? |
|---|---|---|
| 1 | obiektyw wykryty (`LENS_XDETECT` → `ConnectLens`) | częściowo — adapter zwiera pin 10 |
| 2 | odebrany `NID_LENS_INFORMATION` | ❌ nie ma kto go wysłać |
| 3 | `uc_AF_POSSIBLE` + `uc_ContrastAF_Support` | ❌ |
| 4 | możliwość napędzania silnika ogniskowania | ❌ |
| 5 | **`Release w/o Lens` = Enable** | ✅ jedyne ustawienie po stronie użytkownika |

### Co działa

Te funkcje są w warstwie widoku (`viewUnified2.so`), nie w logice obiektywu:

- **Focus Peaking** (`ACT_Peaking`, `…CustomPeakingLevel/Color`)
- **Focus Magnifier** (`…CustomFocusMagnifier`)
- **MF Assist**
- zdjęcia — po włączeniu `Release w/o Lens`

Stringi UI mówią wprost o ograniczeniach:

```
"Release w/o Lens" → Enable / Disable
"Makes shooting unavailable when the lens is not attached."
"Check that a lens is mounted."
"For an unsupported lens, set \"Release w/o Lens\" in the menu to \"Enable\"."
"Invalid because lens not attached."
"Focus Check Live View unavailable without lens attached."
```

### Dlaczego zwarcie XDETECT nie wystarczy

Pin 10 tylko odblokowuje zasilanie. Po włączeniu zasilania body wysyła ramki
`0xF0…0x55` po `TXD` i czeka na odpowiedzi po `RXD`. Bez odpowiedzi nie ma
`NID_LENS_INFORMATION`.

Adaptery z „chipem" emulują obiektyw i raportują stały zestaw zdolności; to odblokowuje
ekspozycję, metadane, czasem stabilizację — ale AF nadal nie zadziała, bo nie ma czym
poruszyć grupą ogniskującą (chyba że sam adapter napędza silnik, jak adaptery EF→E).

**Wniosek: potwierdzenia ostrości z w pełni manualnym obiektywem nie da się włączyć
żadnym ustawieniem ani patchem firmware.** Wymaga zamkniętej pętli AF, a ta wymaga
obiektywu z silnikiem i protokołem. Praktyczny zamiennik to Focus Peaking plus lupa.
