# Sony A6000 (ILCE-6000) — notatki z reverse engineeringu

**Repozytorium dwujęzyczne: [English](README.md) · [Polski](README.pl.md)**

Notatki z analizy statycznej Sony A6000 z 2014 r.: co jest w firmware, co da się
zmienić i czego nie pozwala sprzęt. Wszystko wyprowadzone z **plików** — pakietów
aktualizacji Sony, service manuali Sony oraz otwartych narzędzi projektów
*nex-hack* i *OpenMemories*.

> **Zakres i zastrzeżenie.** Wyłącznie dokumentacja. Żadnych binariów Sony, zrzutów
> firmware ani danych osobowych. Nic w tym repozytorium nie było sprawdzone na
> fizycznym aparacie przez autora; twierdzenia są albo *zweryfikowane z plików*
> (tak oznaczone), albo wprost oznaczone jako hipotezy. Postępowanie według tych
> notatek może uszkodzić aparat. **Zepsujesz — zatrzymujesz obie połówki.**

---

## Co to jest

Uporządkowana baza wiedzy o platformie ILCE-6000:

| # | Dokument | Na jakie pytanie odpowiada |
|---|---|---|
| 01 | [Sprzęt](docs/pl/01-sprzet.md) | Jakie układy są na płycie (potwierdzone service manualami Sony) |
| 02 | [Struktura firmware](docs/pl/02-struktura-firmware.md) | Prawdziwa tablica partycji, mapa NAND, co gdzie leży |
| 03 | [Integralność i flashowanie](docs/pl/03-integralnosc.md) | Manifesty CRC32, brak podpisów, co da się złożyć i wgrać |
| 04 | [Magazyn ustawień](docs/pl/04-ustawienia.md) | `Backup.bin`, znane ID, 11 plików domyślnych per region |
| 05 | [DFE](docs/pl/05-dfe.md) | Front-end: firmware, mapa rejestrów, AF fazowy, kanał logów |
| 06 | [DSP AV i scenariusze](docs/pl/06-dsp-scenariusze.md) | Programy `sabin`, warianty enkoderów, wtyczki |
| 07 | [Obiektywy](docs/pl/07-obiektywy.md) | Warstwy sterowania, protokół E-mount, czemu manualny nie ma AF |
| 08 | [Modele bliźniacze](docs/pl/08-modele-blizniacze.md) | 66 modeli CXD90014, A6000 vs A6300, czemu 4K jest niemożliwe |
| 09 | [Prior art](docs/pl/09-prior-art.md) | Kto już tą drogą szedł i gdzie się zatrzymał |
| 10 | [Pytania otwarte](docs/pl/10-pytania-otwarte.md) | Co jeszcze nie wiadomo i jak to ugryźć |
| — | [Źródła](docs/pl/99-zrodla.md) | Odnośniki z oceną wiarygodności |

Surowsze, dłuższe notatki robocze (z których powstały oba zestawy) leżą w
[`docs/pl/raw/`](docs/pl/raw/).

## Najważniejsze ustalenia na jednym ekranie

| Ustalenie | Klasa dowodu |
|---|---|
| **Brak podpisów kryptograficznych** w firmware CXD90014. Integralność to CRC32 w manifestach `*.sum`, do przeliczenia przez każdego | zweryfikowane — przeliczone wszystkie manifesty |
| **Zmodyfikowany firmware da się przepakować bit w bit.** `fwtool.py unpack` → `pack` odtwarza plik Sony z tym samym SHA-256 | zweryfikowane — `29aef21a…892f` |
| Prawdziwa tablica partycji jest **w firmware** (`0300_partconf/partinf.conf`); NAND to 463,75 MiB, 15 partycji, bez dziur | zweryfikowane |
| Update nadpisuje tylko `nflasha3/5/7/15/16`. Dane użytkownika (`nflasha17`) i ustawienia (`nflasha2`) przeżywają | zweryfikowane |
| Updater sprawdza **tylko** CRC32 + typ LSI (main/sub) + pojemność NAND. Zero weryfikacji autorstwa i wersji | zweryfikowane ze skryptów update |
| Firmware zawiera **11 gotowych `Backup.bin`, po jednym na region** → wszystkie 16 102 właściwości dostępne offline | zweryfikowane |
| **DFE (`CXD90027GF`) to prawdziwy MCU ARM** — 83 procedury: AF fazowy (ZPD), korekcja defektów (DFECAM0–5), timing matrycy (SSG) | zweryfikowane — Ghidra 12.1.4 |
| Logi DFE idą do **bufora RAM pod `0x0102D000`**, nie na UART | zweryfikowane |
| **4K na A6000 jest niemożliwe** — kodek Beaune (`CXD4236`) jest tylko na płycie A6300 | zweryfikowane — service manuale + firmware |
| A6000 i A6300 mają **ten sam DFE** (`IC6200 = CXD90027GF`); różni się tylko generacja firmware (2014 vs 2015) | zweryfikowane — service manuale |
| Potwierdzenie ostrości z manualnym obiektywem jest nieosiągalne: aparat uzależnia AF od komunikatu o zdolnościach (`NID_LENS_INFORMATION`) przysłanego przez obiektyw | zweryfikowane — stringi w `libObj.so` |

## Zawartość repozytorium

```
docs/en/            dokumenty angielskie (01–10, 99)
docs/pl/            polskie tłumaczenia tego samego zestawu
docs/pl/raw/        oryginalne polskie notatki robocze (materiał źródłowy)
tools/backup.py     CLI do Backup.bin: info / list / get / known / diff
tools/apply-dfe-names.py   skrypt Ghidry odtwarzający nazwy symboli DFE
data/dfe-names.txt  83 nazwane procedury dfe.bin
references/         lista źródeł w formie maszynowej
```

## Czego tu **celowo** nie ma

- obrazów firmware Sony, także odszyfrowanych
- zrzutów NAND (zawierają dane konkretnego egzemplarza i dane osobowe)
- PDF-ów service manuali (dystrybucja — podane są odnośniki)
- wyciągniętych `dfe.bin`, `av-cam.bin`, programów `sabin`

Wszystko to odtwarza się z publicznych plików aktualizacji Sony narzędziami
wymienionymi w [`99-zrodla.md`](docs/pl/99-zrodla.md).

## Odtworzenie od zera

```bash
# 1. Oficjalny updater (link w 99-zrodla.md), potem:
pip install pycryptodomex pyyaml
git clone https://github.com/ma1co/fwtool.py
python fwtool.py/fwtool.py unpack -f FirmwareData_ILCE6000V321.dat -o fw

# 2. Magazyn ustawień
python tools/backup.py info fw/firmware.tar_unpacked/0110_backup/SYSMUSASHI-DSLR/DM_UUD3/CX77500_ALLLANG.bin
python tools/backup.py known fw/firmware.tar_unpacked/0110_backup/SYSMUSASHI-DSLR/DM_UUD3/CX77500_ALLLANG.bin

# 3. Firmware DFE (Ghidra): raw binary, ARM LE v7, baza 0x01000000
#    następnie uruchom tools/apply-dfe-names.py
```

## Licencja

Dokumentacja i skrypty: MIT (patrz [LICENSE](LICENSE)).
Firmware, service manuale i narzędzia firm trzecich pozostają własnością ich
właścicieli i nie są tu redystrybuowane.
