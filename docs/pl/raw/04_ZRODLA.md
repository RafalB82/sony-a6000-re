# 04 — Źródła i ocena wiarygodności

Skala: **A** = kod źródłowy / dokumentacja projektu (sprawdzone lokalnie),
**B** = dokumentacja projektu przeczytana online, **C** = źródło wtórne (blog/forum),
**D** = pojedyncze źródło, niezweryfikowane, traktować jako hipotezę.

## A — kod na dysku (najwyższa wartość)

| Co | Gdzie | Do czego |
|---|---|---|
| `fwtool.py/devices.yml` | `sony/fwtool.py/` | baza modeli: arch, model code, wsparcie appek |
| `pmca/backup/__init__.py` | `sony/Sony-PMCA-RE/` | **struktura Backup.bin** (pola, offsety) |
| `pmca/commands/`, `pmca-console.py` | tamże | lista komend (install, updatershell, serviceshell, print_backup, backup…) |
| `OpenMemories-Platform/api/backup.cpp` | `sony/OpenMemories-Platform/` | **ID ustawień, tablice języków, protection** |
| `OpenMemories-Platform/api/tweaks.cpp` | tamże | wartości on/off, logika tweaków |
| `OpenMemories-Platform/drivers/backup.h` | tamże | offsety w preset data (`version` 0x0c, `id1` 0x28, `region` 0xc0) |
| `OpenMemories-Tweak/app/.../jni.cpp` | `sony/OpenMemories-Tweak/` | mapowanie kluczy JNI → tweaki |
| `OpenMemories-Tweak/app/src/main/jni/Android.mk` | tamże | jak budowany jest `adbd` i stuby libs |
| `OpenMemories-AppList/apps.yaml` | `sony/OpenMemories-AppList/` | lista appek instalowalnych |

## B — dokumentacja projektów

- **Sony-PMCA-RE README** — https://github.com/ma1co/Sony-PMCA-RE
  Trzy tryby, driver requirements (Zadig per tryb), CXD90045/90057 niepodpisane → nie.
- **OpenMemories-Tweak README** — https://github.com/ma1co/OpenMemories-Tweak
  Zakres tweaków, komendy do dumpu, FAQ (co przetrwa factory reset / update firmware).
- **Supported devices** — https://openmemories.readthedocs.io/devices.html
  Tabela generowana z `fwtool.py/devices.yml` (JS). Lokalne `devices.yml` jest wygodniejsze.
- **fwtool.py README** — https://github.com/ma1co/fwtool.py
- **OpenMemories (strona projektu)** — https://openmemories.github.io/

## C — źródła wtórne (blogi, użyteczne praktycznie)

- **docodethatmatters.com Part 1** — https://docodethatmatters.com/hacking-sony-a6000-for-modernization/
  Najbardziej znany wpis. Wartość: odkrycie, że `setPostviewImageSize("Original")` w Sony
  Camera API zwraca **pełną ścieżkę do pliku na dysku kamery**, a potem URL-iteracją
  da się ściągać dowolne pliki (`http://<ip>:8080/postview/memory/1000/DCIM/...`).
  Do tego: PC Remote + gphoto2, super-rozdzielczość z burstu, GPS przez RPi.
  ⚠️ Autor nie robi RE firmware — to "użytkowe" hacki.
- **Part 2** — https://docodethatmatters.com/hacking-sony-a6000-more/
  USB-C dummy battery, FTP uploader z appki PMCA, realna przepustowość (~70 plików / 13 min).
- **Part 3** — https://docodethatmatters.com/sony-camera-part3/ (RPi tethering)
- **"Research" (2026-08)** — https://docodethatmatters.com/sony-a6000-a6400-research/
  Duży zbiór linków + FAQ. **Samo deklaruje**, że jest "mostly automated researched
  reviewed" → miejscami myli A6000 z A6400, więc nie traktować jako źródła faktów.
- **niemczuk.tech** — https://niemczuk.tech/2022/10/09/installing-openmemories-on-sony-a6000
  Instalacja OpenMemories na A6000 **z Linuksa** — przydatne, bo reszta tutoriali to Windows.

## D — pojedyncze, niezweryfikowane

- **CliffVale/sony-a6000-firmware-research** — https://github.com/CliffVale/sony-a6000-firmware-research
  **Sprawdzone 2026-10-25 na materiale** (`06_CLIFFVALE_OCENA.md`). Werdykt: offsety
  partycji prawdziwe (zgodne z `partinf.conf`), metoda dumpu sensowna, ale tabela
  „byte-identical verification" wyliczona z zaokrągleń, mapa myli rozmiary obrazów
  z rozmiarami partycji, „trailing 187.47 MB" błędne, „Qualcomm CXD90014" błędne.
  Wartościowe: URL-e CDN + hashe (potwierdzone), trop FAT16 @ `0x14200000` (potwierdzony),
  gotcha z OK. **Nie używać jako źródła faktów o układzie NAND.**

## A — dodatkowo, sprawdzone 2026-10-25

- **`ma1co/OpenMemories-Docs` → `hardware.rst`** — https://github.com/ma1co/OpenMemories-Docs
  Tabela SoC-ów: **CXD90014 = Sony BIONZ X, 4× ARM Cortex-A5, „Musashi/Kojiro?", X-2013**;
  power IC MB9AF004BGL „Darwin" (Cortex-M3); DFE CXD90027 „Regulus". To obala
  „Qualcomm CXD90014" z repo CliffVale.
- **Własne rozpakowanie firmware 3.21** — patrz `07_FIRMWARE_3.21.md`. Najmocniejsze
  źródło: `0300_partconf/partinf.conf`, `0100_config/mount.conf`, 11× `Backup.bin` per region.

## Archiwa / społeczność

- **Internet Archive: PMCA** — https://archive.org/download/sony-playmemories-camera-apps
  (folder `Sony A6000/`) — jedyne źródło oryginalnych appek po zamknięciu sklepu.
- Oficjalne zakończenie usługi PMCA: Sony art. **00289030**
- r/a6000 — wątki: "load discontinued apps onto your A6000", "USB power supply"
- Sony Alpha Forum, DPReview — dyskusje o modach (głównie plotki/doświadczenia)
- Firmware 3.21 download: Sony `00015954` (Windows)

## Repozytoria pomocnicze (nie sklonowane, warte uwagi)

| Repo | Co |
|---|---|
| `ma1co/OpenMemories-Platform` | warstwa C/C++ (backup, tweaks, usbcmd) — **sklonowane lokalnie** |
| `dired/PMCA-HDMICam` | clean HDMI dla A6000 |
| `jonasjuffinger/TimeLapse` | intervalometer jako appka PMCA |
| `obsidium` FocusBracket / BetterManual | appki PMCA (były na kamerze) |
| `ThibaudM/timelapse-sony` | intervalometer po Wi-Fi (F-Droid) |
| `petabite/libsonyapi` | Python binding do Sony Camera API (HTTP/JSON, nie USB) |
