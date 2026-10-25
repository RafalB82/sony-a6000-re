# 10 — Pytania otwarte i metodyka

## 1. Pytania otwarte, uszeregowane po wartości

1. **Nazwa `BKID_*` → numeryczne ID.** Firmware zawiera 1058 różnych nazw `BKID_*`
   (786 w `libmprctrl.so`), ale nikt nie opublikował mapowania. Rozszyfrowanie dałoby
   nazwy tysiącom z 16 102 właściwości `Backup.bin`. Metoda: disassembly `libmprctrl.so`
   wokół `Backup_read` i tabel deskryptorów. Pierwsza próba (skan wskaźników) dała
   1430 kandydatów, ale **żadnego ze znanych ID** — czyli szum; layout tabeli jest inny.
2. **Który obraz DFE SoC wgrywa** — `/usr/dfe/dfe.bin` czy kopię w `av-cam.bin` pod
   `0xA67F00`. Rozstrzygalne testem A/B; warunkuje cały eksperyment „nowszy DFE z A6300".
3. **Którego wariantu enkodera AVC używa A6000** (`performance` / `quality` /
   `performance_plus`) i czy pozostałe poprawiają jakość obrazu.
4. **Jak odczytać bufor logów DFE** (`0x0102D000`) od strony SoC — dałoby wgląd w
   inicjalizację matrycy na żywo.
5. **Co robi pozostałe ~16 000 właściwości.**
6. **Czy bloki `SSG`/`DFECAM` DFE nie odsłaniają nieużywanych trybów odczytu matrycy**
   (binning, line-skipping, inne okna). To jedyne miejsce, gdzie takie tryby mogłyby być.
7. **ID komend protokołu E-mount** — potrzebne do zbudowania emulatora obiektywu.
8. **Emulacja A6000 w QEMU**, żeby eksperymenty z firmware nie wymagały sprzętu
   (fork ma1co emuluje już pięć innych modeli).

## 2. Zastosowana metodyka

Wszystko pochodzi z analizy statycznej plików:

| Źródło | Co z nim zrobiono |
|---|---|
| Oficjalny updater Sony (`Update_ILCE6000V321.dmg`) | rozpakowany `fwtool.py` (crypter CXD90014) |
| Updater A6300 (`Update_ILCE6300V201.exe`) | rozpakowany do porównania |
| Service manuale Sony (LEVEL 3, oba modele) | identyfikacja układów ze schematów |
| Domyślne `Backup.bin` (11 plików) | sparsowane parserem Sony-PMCA-RE |
| `dfe.bin` | Ghidra 12.1.4 przez REA, ARM LE v7 @ `0x01000000` |
| `av-cam.bin`, biblioteki, `.so` | analiza stringów, RTTI, skan literal pools, `capstone` |
| Publiczne repozytoria | czytane, nie kopiowane (licencje uszanowane) |

Styl weryfikacji: przeliczać sumę kontrolną zamiast ufać liczbie; porównywać dwa modele
zamiast ufać tabeli; każdą tezę oznaczać jako zweryfikowaną, wywnioskowaną lub hipotezę.

## 3. Czego **nie** zrobiono

- Żadnego eksperymentu na fizycznym sprzęcie. Każde „działa" w tych dokumentach znaczy
  „zaimplementowane i publicznie opisane", a nie „sprawdzone przez autora".
- Nie wgrano zmodyfikowanego firmware.
- Nie przechwycono ani nie odtworzono protokołu obiektywu.
- Nie próbowano emulacji.

## 4. Twierdzenia korygowane w trakcie pracy

Zapisane, żeby czytelnik mógł skalibrować zaufanie:

1. „Qualcomm CXD90014" — błędne; to własny BIONZ X Sony, 4× Cortex-A5.
2. „A6300 nie ma firmware DFE" — niepełne; jest wbudowany w `av-cam.bin`.
3. „A6000 i A6300 mają tę samą matrycę" — przesadzone; tabele PSF są identyczne, ale
   matryce to różne układy, więc tabele są tabelami przetwarzania.
4. „A6000 używa tylko wariantu `performance`, pozostałe są martwe" — oparte na wzorcu
   bajtów, który przecinał dwa sąsiednie wpisy tablicy 32-bitowej. W ogóle nieustalone.

## 5. Jeśli chcesz kontynuować

Sugerowana kolejność, od najtańszego, wszystko wymaga aparatu i naładowanego akumulatora:

1. Zainstalować OpenMemories-Tweak, włączyć Wi-Fi + telnet, potwierdzić root shell.
2. `bk.elf w 0x01070a47 00` (lub odpowiednik w Tweak) dla clean HDMI — odwracalne.
3. Uruchomić `scenario.elf` z `MPR_SCN_GET_TOTAL_LOG.so` — read-only, dowodzi działania
   harnessu.
4. Test A/B na `/usr/dfe/dfe.bin`, żeby poznać, czy plik jest w ogóle używany.
5. Dopiero potem rozważać podmianę DFE z A6300 — i tylko z planem odzyskania aparatu.
