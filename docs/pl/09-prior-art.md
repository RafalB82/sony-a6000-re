# 09 — Prior art

Kto już tą drogą szedł, jak daleko doszedł i gdzie nigdy nie zrobiono ostatniego kroku.

## 1. nex-hack (2012–2014) — praca, która to umożliwiła

Dokumentacja: `personal-view.com/faqs/sony-hack/*` (DokuWiki, czytelna przez Wayback
Machine). Autorzy: oz_paulb, kenan, Vitaliy Kiselev.

| Osiągnięcie | Szczegóły |
|---|---|
| Odszyfrowanie firmware | generacja 1 = SHA1, generacja 2 = AES |
| **Repack + re-encrypt** | `fwtool -c` re-szyfruje `FDAT.dec` → `FDAT.reenc` i przebudowuje `FirmwareData_NexHack.dat`: „*This is a valid firmware update file and running FirmwareUpdater.exe will update the device*" |
| v06final | „Complete Repack from level3 to loadable firmware update file" |
| **Nigdy nie dokończone** | `-m Modify firmware (not implemented yet)`; v0.8 (cramfs/fatfs) nie wyszło |
| `av-cam.bin` | NEX-6: zidentyfikowany jako **kod ARM na T-Kernel RTOS**, głównie JPEG/wideo; skrypt IDA + uwaga o przełączaniu ARM32/Thumb16; rebase do `0xC3421000` dla NEX-5N |
| Kod | `erik-smit/nex-hack` (C: `fwt_util.c`, `fdat_cipher_aes.c`, `fdat_cipher_sha1.c`), `steelcnn/nex-hack` (IDA `.idc`) |

**To jest sedno:** koncepcja „zmodyfikowany firmware Sony wgrany oficjalnym updaterem"
została wykazana jako wykonalna dekadę temu. Nie ma śladu, żeby ktokolwiek faktycznie
wgrał zmodyfikowany obraz do aparatu.

## 2. ma1co (2015–2024) — projekt żywy

| Repozytorium | Co daje | Znaczenie |
|---|---|---|
| **fwtool.py** | unpack **i pack**, obsługa CXD90014 | narzędzie, które umożliwia repack |
| **Sony-PMCA-RE** | USB: instalacja appek, `updatershell`, `serviceshell` | dostęp do aparatu |
| **OpenMemories-Tweak** | edycja `Backup.bin` | warstwa ustawień |
| **OpenMemories-Platform** | natywny kod C/C++ na aparacie | baza dla własnych payloadów |
| **OpenMemories-Framework** | SDK do appek PMCA (322 klasy `com.sony.*`) | warstwa aplikacji |
| **SA-DSP** | **specyfikacja procesora do Ghidry dla `sabin`** (2021) | klucz do programów DSP |
| **qemu** | fork QEMU dla BIONZ | emulacja |
| **OpenMemories-CI** | emuluje kamery w QEMU na GitHub Actions (NEX-3, RX100M5, HX99, QX10, W90) | testy bez sprzętu |
| **OpenMemories-Symbols** | `bin2elf.py` + baza symboli dla 11 **starych** modeli | metoda, ale bez A6000 |

## 3. Społeczność — ustawienia i pojedyncze hacki

- **Clean HDMI na A5000**: `bk.elf w 0x01070a47 00` (LinuxGameCast / Hackaday, 2022-11).
  Zweryfikowane tutaj na domyślnych A6000: właściwość istnieje, `attr=0x40`, domyślnie
  `01` — więc sztuczka powinna działać też na A6000.
- **OpenMemories-Tweak**: limit nagrania, języki, ekran NTSC.
- **`voxivoid/recipe-lab-sony-pmca`** — aktywnie utrzymywana appka dla A6000/A6300/
  A6500/A5100/A7 II/A7S II. Jej `docs/DEVELOPMENT.md` publikuje **pierwszą zweryfikowaną
  mapę ID ustawień A6000**, uzyskaną przez „disassembling the camera app's parameter
  registration in `libObj.so`" — tym samym pliku, w którym jest 786 nazw `BKID_*`.
- **PlayMemories Camera Apps** wyłączone 2025-08-31; APKi są w Internet Archive i nadal
  instalowalne przez `pmca-console install`.

## 4. Analogie z innych marek

- **Canon — Magic Lantern**: rozbudowa firmware na dużą skalę; sprawdzony model.
- **Panasonic — PTool** (ten sam Vitaliy Kiselev): patchuje **bitrate i parametry
  kodowania** w firmware kompaktów — dokładnie ta klasa zmiany, którą tu rozważamy dla
  enkoderów ZIMA.

Czyli „zmiana parametrów enkodera w firmware aparatu" została zrobiona gdzie indziej.
Dla Sony — nie.

## 5. Czego nikt nie zrobił publicznie

| Temat | Stan |
|---|---|
| **Wgranie zmodyfikowanego obrazu partycji do aparatu** | **brak relacji** — ostatni krok |
| Którego wariantu enkodera AVC używa A6000 | nieznane |
| Jakakolwiek analiza programów `sabin` poza specyfikacją Ghidry | brak |
| Wtyczki `/usr/scenario` (35 `.so` + `scenario.elf`) | zero publikacji |
| Tabela nazwa `BKID_*` → numeryczne ID (1058 nazw w binariach) | brak mapowania |
| Analiza `dfe.bin` | brak przed tą pracą |
| Emulacja A6000 w QEMU | nie zrobiona (inne modele tak) |

## 6. Twierdzenia, które okazały się błędne

- `CliffVale/sony-a6000-firmware-research` — prawdziwa metodologia zrzutu i poprawne
  offsety *startów* partycji, ale tabela „byte-identical" jest policzona z zaokrąglonych
  megabajtów, mapa regionów myli rozmiar obrazu z rozmiarem partycji, „trailing
  187,47 MB" jest błędne, a CXD90014 nazwany jest Qualcommem. Przydatne jako lista
  kontrolna, nie jako źródło faktów.
- „A6300 nie ma firmware DFE" — niepełne: ma, wbudowany w `av-cam.bin`.
