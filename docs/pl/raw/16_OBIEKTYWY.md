# 16 — Sterowanie obiektywem: co mówi firmware

Pytanie: czy z firmware A6000 wynika sterowanie obiektywami? **Tak — i to na trzech
poziomach: logika, dane optyczne per-obiektyw, oraz narzędzie serwisowe na kamerze.**
Zestawione z protokołem E-mount z dumped sygnałów (Entropy512/sigrok-dumps).

---

## 1. Warstwa logiki — klasa `Camera::Lens`

W `av-cam.bin` (partycja `nflasha3`, `/system`) są jawne symbole:

| symbol / string | znaczenie |
|---|---|
| `void Camera::Lens::Initialize(UPM_BOOT_FACTOR*)` | inicjalizacja podsystemu obiektywu przy starcie |
| `ConnectLens` | wykrycie/połączenie obiektywu |
| `LENS_MOUNT`, `LENS_BARRIER` | stan gniazda / bariera (blokada wyzwolenia bez obiektywu?) |
| `LensPowerState` | maszyna stanów zasilania obiektywu |
| `LensTempAD` | odczyt temperatury obiektywu (przez ADC) |
| `[IMAGING_CAP]: Warning! Wait E-MountLens ReduceVoltage Wait(%d ms)` | **negocjacja napięcia** z obiektywem |
| `[LENS_PDR]: BonoboDSP_Send/Recv [ch0/ch1]` + `paritycheck_error` | transport danych do/z obiektywu |
| `this lens is not permitted` | **gating**: niektóre obiektywy są odrzucane |
| `Scanless NG because of CenterOnlyLens` | obiektyw wpływa tryb odczytu matrycy (scanless) |

**`LENS_PDR`** = warstwa „packet data request" — to odpowiednik ramek z protokołu
przewodowego. Ciekawostka: w A6000 ruch idzie przez **`BonoboDSP`** (kanały 0/1,
kontrola parzystości). Bonobo to układ stabilizacji `R2J30503LG` — ale **A6000 nie ma
`bonobo.bin`** (ma go A6300), więc ten kod może być wspólny i nieaktywny na A6000.
Do weryfikacji na sprzęcie.

## 2. Warstwa danych optycznych — `Camera::Lens::ODL`

```
Camera::Lens::ODL::Alloc / Free / Load
Camera::Lens::ODL::AllocLensAberrationData / LoadLensAberrationData / FreeLensAberrationData
Camera::Lens::ODL::ODL_ERR ...
```

**ODL** = biblioteka danych optycznych. Aparat ładuje **dane aberracji dla konkretnego
obiektywu** i przekazuje je do potoku obrazu:

```
[CAMERA_MAIN_YC]: DCV::job_YC_CalcParam: LensPos: FocusPos / IrisPos / ZoomPos (Private/Public)
[CAMERA_MAIN_YC]: SHD::CalcLensShdGain / JudgeShdOn (LensShdOn, PzShdOn)
[ADF] ZOOM[0..2] (v,p,s,f)
agb1_iris_drv_flg
```

Czyli **pozycje focus/iris/zoom realnie wchodzą do obliczeń korekcji (shading,
aberracja)** — to nie jest tylko sterowanie mechaniką, ale sprzężenie optyki z DSP.

### Pliki per-obiektyw w firmware

| gdzie | co | rozmiar |
|---|---|---|
| `0800_appli/lens/VX9101..VX9130_lensfile.bin` | **18 plików**, 2–13 KB każdy | dane konkretnych obiektywów |
| `nflasha3/lensbin_lensproperty/LensAberrationData.bin` | baza danych aberracji | **161 766 B** |
| partycja **`nflasha18` = `/lens`** | 20 MiB, vfat | miejsce na dane obiektywów w aparacie |

Numeracja `VX91xx` to identyfikatory obiektywów; mapowanie numer → model nie jest
opisane w firmware (nazw nie ma w środku plików).

## 3. Narzędzie serwisowe **na kamerze**: `/usr/bin/adjstctl.elf`

To najciekawszy praktyczny punkt. Jest to CLI do komend adjustacyjnych:

```
<options> [adjust_block] [adjust_code] [size]:[data] ...
  np. "adjust block: 0x%04x, code: 0x%04x OSAL ID: 0x%08lx cmdname: %s"
```

**~290 komend**, pogrupowanych prefiksami: `A_` (138), `C_` (55), `S_` (102).
Z obiektywem związane m.in.:

| komenda | co robi |
|---|---|
| `S_LENS_INI`, `S_LENS_END`, `S_LENS_BARRIER` | start/stop podsystemu obiektywu |
| `S_LC_GET_ALENS_INFO` | **odczyt informacji z obiektywu** |
| `S_LC_GET_ALENS_PINT_ADJ`, `S_LC_SET_ALENS_PINT_ADJ` | odczyt/zapis punktów adjustacji obiektywu |
| `S_LC_SET_MOUNT_AORI` | orientacja gniazda |
| `S_IRIS_INIT`, `S_IRIS_OPEN`, `S_IRIS_CLOSE_STDG`, `S_IRIS_CLOSE_MAXG`, `S_IRIS_MANU`, `S_IRIS_MANU_CMP` | **bezpośrednie sterowanie przysłoną** |
| `S_ZOOM_MOVIEREC`, `S_HYB_ZOOM_ONOFF` | zoom (w tym hybrydowy) |
| `C_LENS_BARREL_STATUS`, `C_LM_LENS_TYPE` | stan tubusu, typ obiektywu |
| `A_TB_SET_LENS_INFO`, `A_TB_WRITE_LENS_QR_INFO`, `A_TB_LENS_POS_2E`, `A_LENS_TB`, `A_LENS_MR_RING_FC/ZM` | zapis danych serwisowych obiektywu, pierścienie MR |
| `A_SET_ZPD_LENS` | kalibracja ZPD (AF) z obiektywem |
| `C_AF_ILUMI_ON/OFF`, `S_AF_ACT` | iluminator AF, aktywacja AF |

Komunikacja: `libosal_uipc.so` + `libtestcmd.so` (IPC do działającej usługi).
**Czyli przy root shelu (telnet z OpenMemories-Tweak) te komendy są w zasięgu ręki.**

⚠️ To narzędzie **serwisowe/fabryczne**. `A_*` potrafią zapisywać dane kalibracyjne
(`WRITE_LENS_QR_INFO`, `SET_ALENS_PINT_ADJ`) — zła komenda może rozjechać kalibrację.
`S_*` i `C_*` wyglądają na operacyjne (bezpieczniejsze).

Dodatkowo w `/usr/scenario/` jest wtyczka **`CAMERA_SCN_SET_ZOOM_DRV.so`** — czyli
zoom ma też wejście przez warstwę scenariuszy.

## 4. Protokół z dumpów (Entropy512) — jak się ma do firmware

Źródło: `github.com/Entropy512/sigrok-dumps`, `lens_mounts/sony_emount/README`.
Dumpy zrobione **na Sony ILCE-A6000** (dokładnie nasz model).

### Wyprowadzenia (widok od tyłu obiektywu, 1→10)

| pin | sygnał | funkcja |
|---|---|---|
| 1 | `LENS_GND` | masa silnika |
| 2 | `LENS_POWER` | zasilanie silnika: **5,0 V albo nieuregulowane Vbat (7,4 V)** — **negocjowane** |
| 3 | `LOGIC_GND` | masa logiki |
| 4 | `BODY_VD_LENS` | nieznane, zwykle high, impulsy low 60 Hz |
| 5 | `LOGIC_VCC` | **3,15 V** logika |
| 6 | `LENS_CS_BODY` | handshake, high podczas transmisji RXD |
| 7 | `RXD` | dane **obiektyw → body** |
| 8 | `TXD` | dane **body → obiektyw** |
| 9 | `BODY_CS_LENS` | handshake, high podczas TXD |
| 10 | `LENS_XDETECT` | wykrycie obiektywu (zwierane do masy) |

### Ramki

```
0xF0 | ID komendy | payload | CRC16 (LSB first) | 0x55
```
- 8N1, LSB first, **750 kbaud → negocjacja do 1,5 Mbaud** przy inicie.
- Jedna ramka na jeden impuls CS; długość ramki stała dla danego ID.
- `0x55` w payloadzie **nie jest escapowane**.
- W idle: impuls low na `BODY_VD_LENS` wywołuje 2 ramki statusu z obiektywu i 2 z body.

### Zestawienie z firmware

| element protokołu | odpowiednik w firmware |
|---|---|
| negocjacja 5 V vs Vbat | `LensPowerState`, `"Wait E-MountLens ReduceVoltage"` |
| `LENS_XDETECT` | `ConnectLens`, `LENS_MOUNT` |
| ramki 0xF0…0x55 po RXD/TXD | `[LENS_PDR]` (`BonoboDSP_Send/Recv`, kanały 0/1, parity) |
| ID komend | **brak nazw w firmware** — Sony nie zostawił stringów z nazwami komend |
| dane optyczne z obiektywu | `Camera::Lens::ODL::Load…` → `LensAberrationData` |

**Czego firmware NIE daje wprost:** listy ID komend protokołu. README też jej nie ma
(podaje tylko format ramki). Żeby ją odtworzyć, trzeba by albo zdisasemblować warstwę
`LENS_PDR` w `av-cam.bin` (11 MB, ARM, PIC — Ghidra potrzebuje dłuższego limitu),
albo zrobić nowe dumpy z dekoderem.

## 5. Co z tego wynika praktycznie

Da się (hipotezy do sprawdzenia na sprzęcie, wszystkie wymagają root shella):

1. **Odczytać dane obiektywu**: `adjstctl S_LC_GET_ALENS_INFO`, `C_LM_LENS_TYPE`.
2. **Sterować przysłoną** spoza UI: `S_IRIS_MANU`, `S_IRIS_OPEN` — A6000 normalnie
   nie pozwala ustawić przysłony „ręcznie" w trybie filmowym.
3. **Zoom**: `S_ZOOM_MOVIEREC`, `S_HYB_ZOOM_ONOFF`, plus wtyczka
   `CAMERA_SCN_SET_ZOOM_DRV.so` w `/usr/scenario`.
4. **Podmienić dane korekcji obiektywu**: pliki `VX9xxx_lensfile.bin` i
   `LensAberrationData.bin` leżą w obrazach, więc da się je zmienić i wgrać przez
   update `/usr` (i `/system`) — z CRC32 do przeliczenia. Efekt: inna korekcja
   aberracji/shading dla danego obiektywu.
5. **Teoretycznie**: dopuścić obiektyw odrzucany przez `"this lens is not permitted"`
   — ale to wymaga patcha logiki w `av-cam.bin`, nie ustawienia.

## 6. Ograniczenia

- Nie zidentyfikowano mapowania `VX9xxx` → model obiektywu.
- Nie odtworzono ID komend protokołu E-mount z firmware.
- Nie sprawdzono, czy `LENS_PDR`/`BonoboDSP` jest na A6000 aktywną ścieżką
  (kod może być wspólny z modelami z Bonobo).
- Wszystko z plików; **żadna komenda nie była uruchomiona na aparacie**.
