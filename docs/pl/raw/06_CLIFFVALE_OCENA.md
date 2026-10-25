# 06 — Ocena: CliffVale/sony-a6000-firmware-research

Sprawdzone 2026-10-25 **na materiale**, nie na wrażeniu: pobrałem oficjalny firmware 3.21,
rozpakowałem `fwtool.py`, porównałem z twierdzeniami repo i z oryginalną tablicą partycji Sony
(`0300_partconf/partinf.conf`, która jest w firmware).

## Werdykt w jednym zdaniu

**Metoda i offsety są prawdziwe, ale opis jest miejscami zmyślony/niezrozumiały —
a i tak jest już przestarzały, bo `partinf.conf` z firmware odpowiada na to samo
pytanie dokładniej i bez kamery.**

## Co się potwierdziło (twardo)

| Twierdzenie | Weryfikacja | Wynik |
|---|---|---|
| Oficjalny firmware da się pobrać z podanych URL-i CDN | `curl -I` → 302 → `di.update.sony.net` | ✅ |
| DMG ≈ 205 MB, EXE ≈ 207 MB | 214 920 547 B / 216 393 792 B | ✅ |
| `sha256` DMG `844349ff…a3e` | mój: `844349ff…ba3e` — prefix i sufiks zgodne | ✅ |
| `sha256` .dat `29aef21a…892f` | **identyczny co do znaku** | ✅ |
| 7z rozpakowuje DMG do `FirmwareData_ILCE6000V321.dat` | tak, 205 MB | ✅ |
| Starty partycji w mapie regionów | zgodne z `partinf.conf` Sony co do bajtu | ✅ |
| Android userdata @ `0x14200000`, ~100 MB | to **nflasha17** = `/android/data`, 99.75 MiB | ✅ |
| Wejście w updater mode wymaga OK na ekranie | potwierdzone niezależnie (fora, issues) | ✅ |
| `fwtool.py` rozpakowuje CXD90014 | zadziałało lokalnie | ✅ |
| W Backup.bin jest ~15 000 wpisów | 17 167 zadeklarowanych / 16 102 istniejących | ✅ |

## Co jest nieprawdą

### 1. „Qualcomm CXD90014" — błąd
CXD90014 to **własny SoC Sony, BIONZ X**, 4× ARM Cortex-A5, kryptonim „Musashi / Kojiro?",
premiera 2013-10. Źródło klasy A: `ma1co/OpenMemories-Docs/hardware.rst`.
Prefiks `CXD` jest Sony, nie Qualcomma — zdanie jest wewnętrznie sprzeczne.

### 2. Tabela „weryfikacji" jest wyliczona z zaokrągleń, nie zmierzona
Kolumna *Bytes compared* w `docs/04-verification.md` vs **realne rozmiary** plików
z rozpakowanego firmware:

| partycja | realne bajty | realne MiB | „bytes compared" | różnica |
|---|---|---|---|---|
| nflasha3 | 11 489 040 | 10.9568 | 11 493 888 | −4 848 |
| nflasha5 | 42 293 120 | 40.3339 | 42 254 336 | +38 784 |
| nflasha7 | 3 324 495 | 3.1705 | 3 326 976 | −2 481 |
| nflasha15 | 84 042 977 | 80.1496 | 84 044 288 | −1 311 |
| nflasha16 | 59 013 103 | 56.2793 | 59 018 240 | −5 137 |

Każda liczba „bytes compared" = **podane MB × 1048576** (sprawdzone: 4/5 zgadza się
z zaokrągleniem do <4 KB). Czyli ktoś policzył bajty z zaokrąglonej kolumny MiB.
To zgadza się z `KNOWN_ISSUES.md`, które przyznaje, że `verify_partitions.py`
**nigdy nie został uruchomiony**. Twierdzenie „wszystkie 5 partycji byte-identical"
nie ma więc żadnego pokrycia w ich własnym materiale.

### 3. Mapa regionów myli **rozmiar obrazu z firmware** z **rozmiarem partycji**
To jest źródło wszystkich błędów arytmetycznych w `05-region-map.md`.
Sony wysyła w aktualizacji obrazy **mniejsze** niż partycje (reszta to 0xFF).
CliffVale wziął rozmiar pliku z `0700_part_image/dev/` i podpisał go jako „partycja":

| partycja | wg `partinf.conf` | obraz w firmware | co pisze CliffVale |
|---|---|---|---|
| nflasha3 | **30 MiB** | 10.96 MiB | „10.96 MB" |
| nflasha5 | **60 MiB** | 40.33 MiB | „40.30 MB" |
| nflasha7 | **4 MiB** | 3.17 MiB | „3.17 MB" |
| nflasha15 | **100 MiB** | 80.15 MiB | „80.15 MB" |
| nflasha16 | **82.75 MiB** | 56.28 MiB | „56.28 MB" |

Konsekwencje:
- „gap" między nflasha16 a userdata **nie istnieje** — partycja nflasha16 ma dokładnie
  82.75 MiB i kończy się na `0x14200000`.
- „gapy" między partycjami to w rzeczywistości **prawdziwe partycje**, których firmware
  nie wysyła (nflasha4 = MPR backup, nflasha6 = Jiritsu, nflasha10 = /tmp, nflasha11 = /log).
  Efekt (0xFF w dumpie) jest prawdziwy, interpretacja („nieużywane") — nie.
- Wiersz **„trailing 0x1a5c0000+ 187.47 MB" jest błędny w trzech rzeczach**:
  `0x1A5C0000` to start **nflasha18 (LensData, 20 MiB)**, po nim jest nflasha23 (PMBP, 1 MiB),
  a NAND kończy się na `0x1BAC0000` — czyli „trailing" ma **21 MiB, nie 187.47**.

### 4. „fwtool.py nie obsługuje EXE, bo to archiwum LZH" — błędne rozumowanie
`fwtool.py` **ma** parser LZH (`fwtool/lzh/`). Błąd `Unknown exe file` oznacza
„nie rozpoznałem tego jako LZH", a nie „LZH nieobsługiwane". Realne ograniczenie
jest inne: obsługiwany jest tylko LZH **niekompresowany** (`-lh0-`).

### 5. Jakość kodu
- `scripts/map_regions.py` zawiera martwą linię z komentarzem `# placeholder`.
- `verify_partitions.py` szuka 16-bajtowego nagłówka i bierze **pierwsze** trafienie,
  bez sprawdzenia jednoznaczności — przy dwóch partycjach o wspólnym prefiksie
  porówna zły region (i albo da fałszywe OK, albo fałszywy MISMATCH).
- `carve_fat16.py` — sami przyznają, że psuje nazwy w `/local/*`.

### 6. Historia repo
Cała treść (docs + skrypty) w **jednym commicie** 2026-08-02 17:01. Trzy minuty później
commit „chore: touch commit to refresh GitHub contributor aggregation". Miesiąc później
8 commitów boilerplate w 3 minuty (CODEOWNERS, dependabot, SECURITY.md, szablony issue).
Zero commitów naprawiających zgłoszone błędy. To nie dziennik badań, to publikacja.

## Co mimo wszystko jest wartościowe

1. **Metoda**: porównanie dumpu z `0700_part_image/dev/*` jako sposób zakotwiczenia
   offsetów — dobra technika, warto użyć (tylko liczyć `len(file)`).
2. **Trop FAT16 userdata @ `0x14200000`** — trafny. Parametry BPB, które podają
   (200 sektorów FAT, klaster 2048 B), dają dokładnie 51 200 klastrów × 2048 = **100.0 MiB**,
   czyli są ze sobą spójne do bajtu. Ktoś to naprawdę sparsował.
3. **Konkretne URL-e CDN + hashe** — sprawdziłem, działają i zgadzają się.
4. **PID-y USB** (`054c:07c4` normalnie, `054c:03e2` w updaterze) — użyteczne przy udev.
5. **Gotcha z OK** — realna, oszczędza 5 minut na próbę.

## Jak używać tego repo

- **NIE** jako źródła faktów o układzie NAND (→ użyj `partinf.conf`, patrz `07_FIRMWARE_3.21.md`).
- **TAK** jako checklisty procedury i źródła linków.
- Wszystkie liczby z tabel regionów i weryfikacji traktować jako nieistniejące.
