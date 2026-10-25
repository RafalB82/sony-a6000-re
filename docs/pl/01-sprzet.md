# 01 — Sprzęt

Wszystko poniżej pochodzi z *SERVICE MANUAL LEVEL 3* Sony dla obu aparatów
(`ILCE-6000` i `ILCE-6300`) oraz ze stringów w firmware. Zdjęcia z rozbiórki nie były
potrzebne.

## Wykaz układów (A6000)

| Rola | Oznaczenie | Układ | Uwagi |
|---|---|---|---|
| SoC („BIONZ X") | `IC6000` | pkg `MHZ4G8G01A` = **CXD90014** | 4× ARM Cortex-A5, Linux + µITRON |
| **DFE (front-end)** | **`IC6200`** | **`CXD90027GF`** — „CAMERA SIGNAL PROCESS" | 4 arkusze schematu; „not supplied" jako część zamienna |
| Power IC | `IC5700` | `MB9AF004BGL` („Darwin", Cortex-M3) | start SoC + RTC |
| Inne | — | `CXD9950AK` ×2 | rola nieustalona |

Matryca: **IMX210** — w `av-cam.bin` są klasy sterownika `C_ImagerCtrl_IMX210E`
i `ImagerDrvParam_IMX210E`.

> Powtarzane twierdzenie, że CXD90014 to układ *Qualcomma*, jest błędne. `CXD` to
> prefiks Sony; notatki OpenMemories opisują CXD90014 jako własny „BIONZ X",
> 4× Cortex-A5, kryptonim *Musashi / Kojiro?*.

## A6300 obok

| Rola | Oznaczenie | A6000 | A6300 |
|---|---|---|---|
| SoC | `IC6000` | `MHZ4G8G01A` | `MCZ4G8G21A` (nowszy pakiet) |
| **DFE** | `IC6200` | **`CXD90027GF`** | **`CXD90027GF`** — *ten sam układ* |
| Kodek („Beaune") | `IC9012` | **brak** | **`CXD4236-1GG`** (13 arkuszy) |
| Power IC | `IC5700` | `MB9AF004BGL` | `MB9AF004BGL` |

Ta jedna tabela wyjaśnia całą sprawę 4K — patrz
[08-modele-blizniacze.md](08-modele-blizniacze.md).

## Co gdzie działa

```
matryca ──► DFE CXD90027GF ──► SoC CXD90014 ──► (tylko A6300: kodek CXD4236 „Beaune")
             MCU ARM              4× Cortex-A5        MIPS, eSOL eBinder
             dfe.bin              Linux + µITRON      beaune/ipl.bin + firmware.bin
                                  + userland Androida
```

- **DFE** obsługuje odczyt matrycy: dane AF fazowego (ZPD), korekcję defektów
  (DFECAM0–5), generowanie timingów (SSG) i łącze do SoC (DFELINK).
  Szczegóły: [05-dfe.md](05-dfe.md).
- **SoC** prowadzi dwa światy naraz: userland Linuksa (z Androidem 2.3.7 dla appek
  PlayMemories) oraz system czasu rzeczywistego dla potoku AV.
- **Kodek** (Beaune) jest opcjonalny; tylko modele z nim potrafią kodować 4K.

## Pamięć

NAND to jedno urządzenie **463,75 MiB** (`0x00000000`–`0x1BAC0000`), podzielone na
15 partycji bez dziur. Tabela i szczegóły: [02-struktura-firmware.md](02-struktura-firmware.md).

## Źródła tego dokumentu

- Sony `ILCE-6000/6000L/6000Y` SERVICE MANUAL LEVEL 3 (5 arkuszy).
- Sony `ILCE-6300/6300L/6300M` SERVICE MANUAL LEVEL 3 (65 stron) — porównanie.
- `ma1co/OpenMemories-Docs` → `hardware.rst` — rodziny SoC/DFE/kodek, uwaga o µITRON.
- Stringi z firmware: `C_ImagerCtrl_IMX210E`, `SHD::Regulus`, `Hello Regulus`.
