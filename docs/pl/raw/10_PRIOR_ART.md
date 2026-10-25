# 10 — Prior art: kto już szedł tą drogą

Rekonesans internetu (2026-10-25). Pytanie: czy ktoś już (a) repakował firmware Sony,
(b) modyfikował obrazy partycji i wgrywał je, (c) reverse-engineeringował `av-cam.bin`,
sabin/SA-DSP i wtyczki scenariuszy, (d) rozpracował nazwy BKID.

---

## 1. Wnioski w pięciu zdaniach

1. **Ścieżka „unpack → modyfikacja → repack → re-encrypt → wgrywalny plik" została
   przejść do końca już w 2013–2014** przez projekt nex-hack, a dla CXD90014 (czyli
   A6000) jest dziś zaimplementowana w `fwtool.py` ma1co.
2. **Sam to potwierdziłem**: przepakowanie niezmodyfikowanego firmware 3.21 daje plik
   **bit w bit identyczny** z oryginałem Sony (ten sam SHA256) — czyli kryptografia jest
   w pełni odwracalna i nie ma podpisu.
3. **Tryb „modify" nigdy nie powstał** — nex-hack zaplanował `fwtool -m`, ale zostało
   „not implemented yet". Nikt publicznie nie opisał wgrania zmodyfikowanego obrazu
   partycji do aparatu Sony.
4. **Warstwa AV (`av-cam.bin`, sabin/SA-DSP) jest częściowo ruszona**: jest
   dekompilator do SA-DSP (ma1co, Ghidra), jest niedokończony disassembly `av-cam.bin`
   dla NEX-6 (steelcnn), jest QEMU do emulacji firmware — ale **nie dla A6000**.
5. **Wtyczki scenariuszy (`/usr/scenario`, 35 plików) i mapowanie nazw BKID → ID —
   brak jakichkolwiek publicznych prac.** To jest niezaprzeczalnie nowy teren.

---

## 2. Kto co zrobił — mapa

### 2.1. nex-hack (oz_paulb, kenan, vitaliy_kiselev) — 2012–2014

Strona: `personal-view.com/faqs/sony-hack/*` (DokuWiki, żyje w Wayback).

| osiągnięcie | szczegóły |
|---|---|
| **Odszyfrowanie firmware** | gen. 1 = SHA1, gen. 2 = AES |
| **Repack + re-encrypt** | `fwtool -c` re-szyfruje `FDAT.dec` → `FDAT.reenc` i **przebudowuje `FirmwareData_NexHack.dat`**: „*This is a valid firmware update file and running FirmwareUpdater.exe will update the device*" |
| **v06final** | „Complete Repack from level3 to loadable firmware update file" |
| **Czego nie zrobili** | `-m Modify firmware (not implemented yet)`; v0.8 (cramfs/fatfs) nigdy nie wyszło |
| **`av-cam.bin`** | NEX-6: zidentyfikowany jako **kod ARM na T-Kernel RTOS**, głównie JPEG/wideo; skrypt IDA + uwaga o przełączaniu ARM32/Thumb16; rebase pod `0xC3421000` dla NEX-5N |
| **Kod** | `erik-smit/nex-hack` (C, `fwt_util.c`, `fdat_cipher_aes.c`, `fdat_cipher_sha1.c`), `steelcnn/nex-hack` (IDC do IDA) |

**To najważniejszy punkt całego rekonesansu:** koncepcja „zmodyfikowany firmware Sony
wgrany oficjalnym updaterem" została **wykazana jako wykonalna** ponad dekadę temu.
Nie ma natomiast śladu, żeby ktoś to *faktycznie* zrobił na aparacie.

### 2.2. ma1co — 2015–2024 (główny żywy projekt)

| repo | co daje | znaczenie dla nas |
|---|---|---|
| **fwtool.py** | unpack **i pack** firmware, CXD90014 obsłużony | **klucz** — repack działa (patrz §3) |
| **Sony-PMCA-RE** | USB: app install, updatershell, serviceshell | dostęp do kamery |
| **OpenMemories-Tweak** | zmiana ustawień w `Backup.bin` | warstwa 0 |
| **OpenMemories-Platform** | natywny kod C/C++ na kamerze (backup, tweaks, usbcmd) | baza do własnych payloadów |
| **OpenMemories-Framework** | SDK do appek PMCA (322 klasy `com.sony.*`) | warstwa 1 |
| **SA-DSP** | **wtyczka do Ghidry: dekompiluje „sabin"** (2021) | **klucz do enkoderów** |
| **qemu** | fork QEMU dla BIONZ | emulacja |
| **OpenMemories-CI** | emuluje kamery w QEMU na GitHub Actions | testy bez sprzętu |
| **OpenMemories-Symbols** | `bin2elf.py` + baza symboli dla **11 modeli** | metoda, ale **nie A6000** |

### 2.3. Społeczność (ustawienia)

- **A5000 clean HDMI**: `bk.elf w 0x01070a47 00` — wyłącza overlay HDMI (LinuxGameCast
  / Hackaday 2022-11). **Sprawdziłem lokalnie: ten BKID istnieje w Backup.bin A6000,
  attr `0x40`, domyślnie `01`** → ta sztuczka powinna działać też na A6000.
- OpenMemories-Tweak: limit 30 min, języki, NTSC.
- **PlayMemories Camera Apps** — martwe od 2025-08-31, APKi w Internet Archive.

### 2.4. Analogie z innych marek (dowód, że koncepcja jest realna)

- **Canon — Magic Lantern**: podmiana/rozszerzenie firmware na dużą skalę, sukces.
- **Panasonic — PTool (Vitaliy Kiselev, ten sam człowiek co nex-hack)**: patchowanie
  **bitrate'u i parametrów kodowania** w firmware kompaktów — dokładnie ten pomysł,
  który tu rozważamy dla ZIMA/sa_avce.

Czyli „zmiana parametrów enkodera w firmware aparatu" **została zrobiona gdzie indziej**.
Dla Sony — nie.

---

## 3. Co potwierdziłem sam (najmocniejszy wynik)

Round-trip bez kamery:

```bash
fwtool.py unpack -f FirmwareData_ILCE6000V321.dat -o fw
fwtool.py pack -c fw/config.yaml -f fw/firmware.tar -u fw/updater.img -o repack
```

| plik | rozmiar | SHA256 |
|---|---|---|
| oryginał Sony | 212 988 056 | `29aef21ab9b5c2e98388974ac9749c2cbfb1815273b444e62f2e41398aa8892f` |
| **repack fwtool.py** | 212 988 056 | **`29aef21a…892f` — identyczny** |

**Znaczenie:** nie tylko „da się rozpakować", ale **„da się złożyć z powrotem i wynik
jest bit w bit poprawny"**. Skoro tak, to każda modyfikacja zawartości `firmware.tar`
przechodzi tę samą drogę i daje plik, który przechodzi CRC32 i kontrolę modelu.
Brakuje tylko (a) przeliczenia `*.sum`, (b) odwagi, żeby to wgrać.

Przy okazji: `fw/config.yaml` z rozpakowania potwierdza **USB PID-y z Sony**:
normalne `054c:07c4` (wśród innych modeli CXD90014), updater `054c:03e2`,
model `0x41030035`, wersja `3.21`.

---

## 4. Czego NIKT nie zrobił (nasz teren)

| temat | stan | dlaczego to okazja |
|---|---|---|
| **Wgranie zmodyfikowanego obrazu partycji** | brak relacji | ostatni krok nigdy publicznie wykonany |
| **Wybór wariantu enkodera** (`avce_performance` / `quality` / `performance_plus`) | nieznany | 3 warianty leżą w `/usr/sabin`, nikt nie sprawdził który działa lepiej |
| **Programy SA DSP** (`sa_avce_*`, `sa_spica`, `sa_frc2`) | jest tylko dekompilator (SA-DSP), **zero publikowanej analizy** | „sabin" nikt nie rozłożył publicznie |
| **Wtyczki `/usr/scenario`** (35 .so, `scenario.elf`) | **zero prac** | gotowy ABI + runner w shellu |
| **Mapowanie BKID → ID** | w firmware 1058 nazw, ale nikt nie opublikował tabeli | odblokowałoby nazwy tysięcy ustawień |
| **`av-cam.bin` dla A6000** | tylko NEX-6 (steelcnn, niedokończone) i tylko 11 starych modeli w Symbols | A6000 to 11.4 MB kodu C++ AV z symbolami |
| **Emulacja A6000** | QEMU/CI obsługuje NEX-3, RX100M5, HX99, QX10, W90 | dodanie A6000 = testy bez bricksa |

---

## 5. Co z tego wynika dla planu

**Zmiana priorytetów względem `08_ZMIANY_W_KODZIE.md`:**

1. **Zanim cokolwiek wgramy — warto sprawdzić emulację.** ma1co ma QEMU dla BIONZ
   i runner (`OpenMemories-CI/runner/`: `nand.py`, `onenand.py`, `qemu.py`, `kernel_patch.py`).
   Jeśli da się dodać A6000, testujemy obrazy bez ryzyka. To najtańsza droga do
   „sprawdź, czy kamera wstanie".
2. **`SA-DSP` (Ghidra) jest gotowe** — nie trzeba pisać własnego disassemblera.
   Wystarczy wgrać wtyczkę i zdekompilować `sa_avce_performance_zma.bin`, żeby
   porównać warianty enkoderów.
3. **`OpenMemories-Symbols` daje metodę** (`bin2elf.py` + mapa segmentów) — dla A6000
   trzeba dorobić wpis w `known_files.yaml` (segmenty `av-cam.bin` da się wyznaczyć
   rebasingiem, jak opisał nex-hack).
4. **Clean HDMI na A6000 prawdopodobnie da się zrobić jednym BKID** (`0x01070a47 = 00`),
   bez PMCA-HDMICam i bez reflashu — do potwierdzenia na sprzęcie.

---

## 6. Źródła

| źródło | typ | ocena |
|---|---|---|
| `personal-view.com/faqs/sony-hack/fwtool` (Wayback 2026-05) | dokumentacja nex-hack | **A** — autorzy narzędzia |
| `personal-view.com/faqs/sony-hack/nex6-av-cam.bin-reversing` (Wayback) | notatki z RE | **A/B** — niepełne, ale pierwotne |
| `erik-smit/nex-hack` | kod C fwtool | **A** |
| `steelcnn/nex-hack` | IDC do IDA dla av-cam.bin | **B** — niekompletny |
| `ma1co/fwtool.py`, `SA-DSP`, `qemu`, `OpenMemories-*` | kod | **A** |
| LinuxGameCast / Hackaday 2022-11-25 | A5000 clean HDMI, `0x01070a47` | **B** — potwierdzone lokalnie w Backup.bin |
| `personal-view.com/faqs/ptool/*` | PTool (Panasonic) — analogia | **B** — dowód koncepcji |
| Sony Alpha Forum „a6000 flashed with a6300 bios" | spekulacja, **bez potwierdzenia** | **D** — nikt tego nie zrobił |
