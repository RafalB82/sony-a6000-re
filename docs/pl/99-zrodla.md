# 99 — Źródła i wiarygodność

Skala: **A** = źródło pierwotne (kod, oficjalna dokumentacja, plik przez nas
zweryfikowany), **B** = wtórne, ale staranne, **C** = opis społeczności,
**D** = pojedyncze niezweryfikowane źródło — traktować jako hipotezę.

## A — pierwotne

| Źródło | Do czego użyte |
|---|---|
| Firmware Sony `Update_ILCE6000V321` / `ILCE6300V201` | wszystko o partycjach, ustawieniach, DFE, DSP |
| Sony **SERVICE MANUAL LEVEL 3** — `ILCE-6000/6000L/6000Y`, `ILCE-6300/6300L/6300M` | identyfikacja układów (`IC6200 = CXD90027GF`, `IC9012 = CXD4236-1GG`, `IC5700 = MB9AF004BGL`) |
| `ma1co/fwtool.py` | unpack/pack, definicje crypterów, baza modeli `devices.yml` |
| `ma1co/Sony-PMCA-RE` | parser `Backup.bin`, updatershell, `usbshell.cpp`, `updaterbody.cpp` |
| `ma1co/OpenMemories-Platform` | `api/backup.cpp` (ID właściwości), `api/tweaks.cpp` (wartości) |
| `ma1co/OpenMemories-Docs/hardware.rst` | rodziny SoC/DFE/kodek/power IC, uwaga o µITRON |
| `ma1co/SA-DSP` | specyfikacja procesora do Ghidry dla `sabin` |
| `ma1co/qemu`, `ma1co/OpenMemories-CI` | infrastruktura emulacji firmware |
| `erik-smit/nex-hack` | implementacja C repack/encrypt firmware |

## B — wtórne, staranne

- **wiki nex-hack** (`personal-view.com/faqs/sony-hack/*`, przez Wayback):
  `fwtool`, `fwencryption`, `nex6-av-cam.bin-reversing`.
  Pierwszorzędne od autorów narzędzi, ale niekompletne.
- **Wikipedia „Bionz"** — parowanie układów per model; artykuł ma zastrzeżenia o braku
  źródeł i miesza konwencje nazewnicze („CXD90027GF SoC" vs CXD90014 u OpenMemories).
- **iFixit, teardown a7R II** — identyfikacja `CXD4236-1GG`.
- **`voxivoid/recipe-lab-sony-pmca`** — zweryfikowana mapa ID ustawień A6000, z opisaną
  metodą; jeden autor, ale metodyka przejrzysta.

## C — społeczność

- LinuxGameCast / Hackaday (2022-11-25) — clean HDMI na A5000 przez
  `bk.elf w 0x01070a47 00`. Zweryfikowane lokalnie na domyślnych A6000.
- Wątki dpreview / EOSHD / DVXuser — kontekst XAVC S, przegrzewanie przy 4K, historia firmware.

## D — pojedyncze źródło, niezweryfikowane

- `CliffVale/sony-a6000-firmware-research` — metodologia zrzutu poprawna i poprawne
  offsety *startów* partycji, ale: tabela „byte-identical" policzona z zaokrąglonych
  megabajtów, mapa regionów myli rozmiar obrazu z rozmiarem partycji, „trailing
  187,47 MB" błędne, CXD90014 nazwany Qualcommem. Używać wyłącznie jako listy kontrolnej.
- `docodethatmatters.com` „research" (2026-08) — sam opisuje się jako „mostly automated
  researched reviewed"; miesza A6000 z A6400.

## Artefakty przywoływane, ale nie redystrybuowane tutaj

| Artefakt | Skąd |
|---|---|
| `Update_ILCE6000V321.dmg` | wsparcie Sony (ILCE-6000, v3.21) |
| `Update_ILCE6300V201.exe` | wsparcie Sony (ILCE-6300, v2.01) |
| Service manuale (LEVEL 2 / LEVEL 3) | archiwum iFixit, photo-parts.com.ua |
| APKi PlayMemories | `archive.org/download/sony-playmemories-camera-apps` |
| Dumpy E-mount z analizatora | `github.com/Entropy512/sigrok-dumps`, `lens_mounts/sony_emount/` |
| Strona projektu OpenMemories | `openmemories.github.io`, `openmemories.readthedocs.io` |

## Skróty plików, na których pracowaliśmy

```
Update_ILCE6000V321.dmg
  844349ff7edddc294c0fddd90a454848eeda8987b6bf043c9757982b3a42ba3e

FirmwareData_ILCE6000V321.dat
  29aef21ab9b5c2e98388974ac9749c2cbfb1815273b444e62f2e41398aa8892f

dfe/dfe.bin (z rozpakowanego drzewa)
  fc4e314db24a72d584bd8795bd8f1144b003c97c390cb143d09b840b38bf9fcd

Update_ILCE6300V201.exe
  8c850f7d5cf6b6717f2e99ca6c7ff38ecbc59745ec0ebdea1833b63f9b76d1d1
```

Te skróty pozwalają potwierdzić, że patrzy się na te same dane wejściowe.
