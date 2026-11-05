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
| **Wgranie zmodyfikowanego obrazu partycji do aparatu** | **zrobione raz, IX–XI 2026, nie przez nas** — patrz §6 |
| Którego wariantu enkodera AVC używa A6000 | nieznane |
| Jakakolwiek analiza programów `sabin` poza specyfikacją Ghidry | brak |
| Wtyczki `/usr/scenario` (35 `.so` + `scenario.elf`) | zero publikacji |
| Tabela nazwa `BKID_*` → numeryczne ID (1058 nazw w binariach) | brak mapowania |
| Analiza `dfe.bin` | brak przed tą pracą |
| Emulacja A6000 w QEMU | nie zrobiona (inne modele tak) |

## 6. nicolvus/a6000-fw-decomp (2026) — ostatni krok, przejechany raz

[`nicolvus/a6000-fw-decomp`](https://github.com/nicolvus/a6000-fw-decomp) to jedyny
znany publiczny projekt, który wgrał zmodyfikowany obraz do A6000 i opisał wynik.
Raporty po hiszpańsku (542, z etykietami `MEDIDO`/`INFERENCIA`/`NO VERIFICADO`),
dwujęzyczna wiki i pakiety `.dat` w release'ach GitHuba.

| Osiągnięcie | Szczegóły | Nasza ocena |
|---|---|---|
| **Zmodyfikowany `darwin_core.bin` działa** | 2 bajty pod `0x1fe6a` (`28 46` → `0a e0`) — bramka mechanizmu zawsze zwraca 0, migawka mechaniczna nie jest napędzana. Potwierdzone na prawdziwym aparacie: cichy strzał bez błędu | spójne z naszym [03](03-integralnosc.md) — brak podpisów, tylko CRC32 |
| **Rekompresja `nflasha3`** | Ich 3.25 uceglił aparat; przyczyna znaleziona offline (reszta sektora TPZL + zła geometria rekordów) i naprawiona w 3.25c | najcenniejsza rzecz w repo: ograniczenia formatu dekompresora |
| **Odzysk po SWD** | Uceglony aparat odzyskany przez wymuszenie jednego rejestru CPU podczas bootu; fabryczny updater wgrał oficjalne 3.26 | patrz [11-odzysk-swd.md](11-odzysk-swd.md) |
| **Migawka elektroniczna** | Dodany selektor w menu BIONZ; na 04-11-2026 przełącza się wewnątrz BIONZ, ale wartość nie dochodzi do Darwina | **nie działa** — nie traktować jako zrobione |
| **Prawo** | Publikują `.dat` Sony (po 213 MB) z jawną notą, że nie mają licencji | ryzyko redystrybucji jest ich, nie nasze |

Warto też wiedzieć: ich E25-10 zmierzył ekspozycję wiersz po wierszu bez tylnej
kurtyny (`T + ~7 ms + 15,2 µs × wiersz`, odczyt ≈ 61 ms) — to ogranicza, co „cicha
migawka" realnie daje na tej matrycy.

## 7. Twierdzenia, które okazały się błędne

- `CliffVale/sony-a6000-firmware-research` — prawdziwa metodologia zrzutu i poprawne
  offsety *startów* partycji, ale tabela „byte-identical" jest policzona z zaokrąglonych
  megabajtów, mapa regionów myli rozmiar obrazu z rozmiarem partycji, „trailing
  187,47 MB" jest błędne, a CXD90014 nazwany jest Qualcommem. Przydatne jako lista
  kontrolna, nie jako źródło faktów.
- „A6300 nie ma firmware DFE" — niepełne: ma, wbudowany w `av-cam.bin`.
