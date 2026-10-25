# 17 — Obiektyw manualny (bez elektroniki): co firmware wymaga

Pytanie: czy w firmware są warunki, które muszą być spełnione, żeby działało
**potwierdzenie ostrości** — w sytuacji obiektywu manualnego bez styków.

**Odpowiedź krótka: potwierdzenie ostrości (AF) jest zablokowane sprzętowo-logicznie,
bo aparat czerpie zdolności AF z komunikatu `NID_LENS_INFORMATION` przysłanego
przez obiektyw. Brak elektroniki = brak komunikatu = `uc_AF_Impossible`.
Tego nie da się obejść ustawieniem.**

---

## 1. Gdzie w firmware siedzi decyzja

W `lib/libObj.so` (warstwa `CamUser` / `CamMgr`) są jawne komunikaty o **flagach
możliwości obiektywu**, przychodzących w `NID_LENS_INFORMATION`:

| flaga | znaczenie |
|---|---|
| **`uc_AF_POSSIBLE` / `uc_AF_Impossible`** | czy AF jest w ogóle możliwy |
| `uc_AF_A_Support`, `uc_AF_C_Support` | czy obiektyw obsługuje AF-A / AF-C |
| **`uc_ContrastAF_Support`** | czy obsługuje AF kontrastowy |
| `uc_DMF_Support`, `uc_Lens_DMF_sw_Support` | DMF (AF + ręczna korekta) |
| `uc_AFMF_sw_Support`, `uc_AFMF_sw_State` | przełącznik AF/MF na obiektywie |
| `uc_PreAF_Support` | pre-AF |
| `uc_AF_AreaCenterOnly` | obiektyw ogranicza obszar AF do centrum |
| `uc_Lens_AFMFDMF_sw_Priority` | priorytet przełącznika na obiektywie |

W `libObj.so` jest **123 różnych pól `uc_*`** — to duża struktura opisująca obiektyw.
W całym firmware tylko ta biblioteka konsumuje `NID_LENS_INFORMATION`.

Przykładowe stringi diagnostyczne (dowód, że to realna ścieżka, nie domysł):

```
[CAMUSER]: CamMgr) ##### NID_LENS_AF_POSSIBLE uc_AF_Impossible error[%d] #####
[CAMUSER]: CamMgr) ##### NID_LENS_INFORMATION uc_ContrastAF_Support error[%d] #####
[CAMUSER]: CamMgr) ##### NID_LENS_INFORMATION uc_AF_AreaCenterOnly error[%d] #####
```

Czyli: **obiektyw melduje, co potrafi; aparat na tej podstawie odblokowuje tryby AF.**
Bez obiektywu nie ma czego zapytać.

## 2. Warstwa obrazu też reaguje na zdolności obiektywu

W `av-cam.bin` (moduł `CAMERA_MAIN_LC` — *Lens Control*) widać, że AF korzysta
z odczytu matrycy i jest zależny od trybu:

- `Camera::Imager::C_Imager::SetExposure_ZAF` / `SetRead_ZAF` — specjalny odczyt
  **ZAF** (ZPD-AF) do danych detekcji fazowej,
- `lc_AF_Scan.cpp`, `lc_HybridAF.cpp`, `lc_DM_AF_*` — skan AF i AF hybrydowy,
- `Scanless NG because of CenterOnlyLens`, `Select AF Area is out of SCANLESS-RANGE` —
  ograniczenia wynikające z obiektywu,
- `"FOCUS MODE is not AF-A"` — kontrola spójności trybu.

To wszystko to **pętla AF**: aparat musi móc *poruszyć* ogniskiem, żeby potwierdzić
ostrość. Przy obiektywie bez silnika i bez komunikacji nie ma czym.

## 3. Co dokładnie jest wymagane (zestaw warunków)

| # | warunek | gdzie | spełnialne bez elektroniki? |
|---|---|---|---|
| 1 | obiektyw wykryty (`LENS_XDETECT` → `ConnectLens`) | `av-cam.bin` | ❌ (dumb adapter zwiera XDETECT do masy, więc *częściowo* tak — patrz §5) |
| 2 | komunikat `NID_LENS_INFORMATION` z flagami AF | `libObj.so` | ❌ **brak źródła** |
| 3 | `uc_AF_POSSIBLE` = tak (+ `uc_ContrastAF_Support` lub AF-A/C) | `libObj.so` | ❌ |
| 4 | możliwość sterowania silnikiem ogniskowania | `CAMERA_MAIN_LC` | ❌ |
| 5 | `Release w/o Lens` = **Enable** (żeby w ogóle zwolnić migawkę) | menu / `SetNoLensRelease` | ✅ ustawienie |

Punkt 5 to jedyna rzecz, którą użytkownik może ustawić. Reszta jest własnością obiektywu.

## 4. Co DZIAŁA bez elektroniki (potwierdzone stringami w UI)

Te funkcje są w warstwie widoku (`viewUnified2.so`), **nie** w logice obiektywu:

- **Focus Peaking** — `ACT_Peaking`, `CmnViewProcessDataElementCustomPeakingLevel/Color`
- **Focus Magnifier** (lupa) — `CmnViewProcessDataElementCustomFocusMagnifier`
- **MF Assist** — `MF Assist` w `string_english.uxc`
- zdjęcia — po włączeniu **`Release w/o Lens`**

Komunikaty UI potwierdzają ograniczenia:

```
"Release w/o Lens"  →  Enable / Disable
"Makes shooting unavailable when the lens is not attached."
"Check that a lens is mounted."
"For an unsupported lens, set \"Release w/o Lens\" in the menu to \"Enable\"."
"Invalid because lens not attached."
"Focus Check Live View unavailable without lens attached."   ← jawne odcięcie funkcji
```

## 5. Dlaczego „zwarcie XDETECT" nie wystarczy

Z dumpów E-mount (Entropy512, zrobione **na A6000**) pin 10 `LENS_XDETECT` służy
tylko do **wykrycia obecności** — body podaje zasilanie dopiero, gdy jest zwarty.
To warunek konieczny, ale **nie wystarczający**: po zasilaniu body wysyła ramki
`0xF0…0x55` po `TXD` i czeka na odpowiedź po `RXD`. Bez odpowiedzi nie ma
`NID_LENS_INFORMATION`, więc AF pozostaje niemożliwy.

Istnieją adaptery z „chipem", które **emulują obiektyw** (raportują stałą ogniskową
i podstawowe zdolności). Efekt w firmware: aparat dostaje `NID_LENS_INFORMATION`
i odblokowuje część funkcji (np. stabilizację, ekspozycję, metadane), ale
**AF i tak nie zadziała**, bo nie ma czym poruszyć ogniskiem — chyba że chip
dodatkowo steruje silnikiem (tak robią adaptery EF→E).

## 6. Wniosek praktyczny

**Potwierdzenie ostrości przy czysto manualnym obiektywie jest nieosiągalne przez
żadne ustawienie ani przez patch firmware** — bo wymaga zamkniętej pętli AF,
a ta wymaga obiektywu z silnikiem i komunikacją.

Co ma sens zamiast tego:
1. `Release w/o Lens` = Enable (inaczej brak spustu),
2. **Focus Peaking** (Level + Color) — jedyne „potwierdzenie ostrości" dostępne bez AF,
3. **Focus Magnifier** / MF Assist do precyzji,
4. jeśli zależy na potwierdzeniu: obiektyw z chipem (raportuje się jako wspierany)
   albo adapter z elektroniką i silnikiem.

## 7. Gdzie ewentualnie szukać głębiej

- `NID_LENS_INFORMATION` ma 123 pola `uc_*` — pełna lista pokazałaby, co jeszcze
  obiektyw „włącza" (np. korekcje, stabilizację, ograniczenia obszaru AF).
  Wypisanie wszystkich nazw: `strings -a lib/libObj.so | grep -oE "uc_[A-Za-z_]+" | sort -u`.
- `Camera::Lens::ODL` — korekcje optyczne zależą od danych obiektywu, więc przy
  dumb adapterze nie są aplikowane (można to obejść plikami `VX9xxx_lensfile.bin`,
  patrz `16_OBIEKTYWY.md`).
- Ścieżka `LENS_PDR` w `av-cam.bin` — odtworzenie ID komend protokołu pozwoliłoby
  zbudować własny emulator obiektywu (teoretycznie).

## 8. Zastrzeżenie

Wszystko z analizy plików i publicznych dumpów. **Nie testowane na aparacie.**
Wnioski o „AF niemożliwy" opierają się na architekturze pętli AF (obiektyw musi
raportować zdolności i mieć silnik), nie na próbie obejścia.
