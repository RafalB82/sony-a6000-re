# 14 — Czy nowszy DFE z A6300 da się uruchomić w A6000?

Porównanie bajtowe i strukturalne obu obrazów front-endu (CXD90027 „Regulus").
Materiał: `analysis/dfe-a6300.bin` (wycięty z `av-cam.bin` A6300 @ `0xC1EB00`)
i `dfe/dfe.bin` z A6000.

---

## 1. Co jest identyczne

| cecha | A6000 | A6300 |
|---|---|---|
| rozmiar | **65 536 B** | **65 536 B** |
| architektura | ARM LE 32 | ARM LE 32 |
| adres bazowy (z literałów wektorów) | `0x01000000` | `0x01000000` |
| układ wektorów | 8× `LDR PC,[PC,#0x18]`, NOP, `LDR PC,[PC,#-0x120]`, `SUBS PC,LR,#4` | **identyczny** |
| **tag celu w binarce** | **`20140123_0000_REGULUS`** | **`20151222_00_1971_REGULUS`** |
| stringi | 97 | 96 |

**Najważniejsze: oba obrazy są zbudowane dla tego samego układu — `REGULUS`.**
A6300 to build z **2015-12-22**, A6000 z **2014-01-23**. Ta sama nazwa celu,
dwa lata różnicy.

Podobieństwo kodu: **94 z 97 stringów wspólnych** (m.in. cała diagnostyka
`CPU APB …`, `Detected IRQ …`, `DFECAM0..5`, `SiMISC`, `ZPD`). To ta sama baza kodu,
tylko rozwinięta.

Bloki 16-bajtrowe (krok 4 B): A6000 5 840, A6300 10 826, wspólne 2 520 →
**Jaccard 0,178**. Czyli ~18% wspólnego materiału bajtowego: sporo się zmieniło.

## 2. Co jest różne

| cecha | A6000 (2014) | A6300 (2015) |
|---|---|---|
| adres resetu | `0x01005870` | **`0x0100C000`** |
| MMU | brak śladów | **`ICACHE,DCACHE and MMU Enable`** |
| instrukcje CP15 (p15) | 2 | **7** |
| bloki MMIO (wyrownane, < `0x01030000`) | 18 | 22 |
| dodatkowe bloki MMIO | — | `0x01013100`, `0x01014000`, `0x01014B00`, `0x01016000`, `0x01016D00` |
| stringi tylko tam | `ZPD_SCC`, `zpd_init` | `ICACHE,DCACHE and MMU Enable` |

Wspólne bloki: **17 z 18** baz A6000 występuje też w A6300 → ten sam układ
peryferyjny, rozszerzony o 5 bloków.

## 3. Odpowiedź — po sprawdzeniu service manuali: **wykonalne, ryzykowne, sensowne jako eksperyment**

### 3.0. Service manuale rozstrzygają sprawę sprzętu

Pobrałem schematy poziomu 3 (Sony) dla obu modeli i sprawdziłem oznaczenia:

| element | A6000 (ILCE-6000 L3) | A6300 (ILCE-6300 L3) |
|---|---|---|
| **DFE** — `IC6200` | **`CXD90027GF`** „CAMERA SIGNAL PROCESS" | **`CXD90027GF`** „CAMERA SIGNAL PROCESS" |
| SoC — `IC6000` | `MHZ4G8G01A` (pkg) | `MCZ4G8G21A` (pkg) |
| power IC — `IC5700` | `MB9AF004BGL` (Darwin) | `MB9AF004BGL` (Darwin) |
| kodek — `IC9012` | **brak w wykazie** | **`CXD4236-1GG`** (13 arkuszy!) |

**Czyli front-end jest fizycznie ten sam układ o tym samym numerze części.**
To nie jest „inny DFE" — to **ten sam CXD90027GF**, tylko z firmwarem o dwa lata
nowszym. (Uwaga: schemat A6000, który mam, to 5-stronicowy wyciąg; brak `CXD4236`
w nim to słaby dowód, ale brak katalogu `/usr/beaune/` w firmware A6000 jest mocny.)

**Konsekwencja:** argument „inny chip → nie zadziała" **upada**. Zostają tylko
różnice rewizji krzemu i sprzężenia z kodem SoC.

### 3.1. Co przemawia za tym, że się *da* wgrać

- **Ten sam układ (CXD90027GF, IC6200)** — potwierdzone schematem Sony.
- Ten sam rozmiar (64 KiB) → podmiana pliku bez zmiany struktury partycji.
- Ten sam adres bazowy i układ wektorów → loader nie musi nic wiedzieć.
- Ten sam tag układu (`REGULUS`) → nie jest to firmware innego chipu.
- Leży w `/usr/dfe/dfe.bin`, czyli w partycji `nflasha15` — **odwracalne reflashem**,
  bez dotykania bootloadera. To najniższe ryzyko z wszystkich znanych modyfikacji.

### Co przemawia przeciw

1. **MMU.** Build A6300 jawnie konfiguruje MMU (7 instrukcji CP15 vs 2). Jeśli
   Regulus w A6000 to starsza rewizja bez sprawnego MMU (albo z innym układem tablic),
   firmware padnie na starcie — zanim cokolwiek zainicjuje.
2. **Pięć dodatkowych bloków rejestrów.** A6300 dotyka `0x01013xxx`, `0x01014xxx`,
   `0x01016xxx`. Na starszej rewizji te adresy mogą nie istnieć → zapis na nie
   może być ignorowany (łagodnie) albo powodować błąd szyny (ostro).
3. **Sprzężenie z kodem SoC.** W A6000 `av-cam.bin` jest klasa **`SHD::Regulus`**
   z metodami typu `ThinoutAdjustQsrfShd` (thinout = decymacja przy odczycie matrycy)
   oraz `Camera::ZPD::Control`. To **SoC** pisze rejestry Regulusa, zakładając mapę
   z 2014 r. Nowy firmware DFE + stary kod SoC = możliwy rozjazd przy inicie
   sensora i AF.
4. **Inny sposób ładowania.** A6300 używa interfejsu `DfeCamAif` / `DFE Acquire`
   i nie ma ścieżki `/usr/dfe/dfe.bin`. A6000 ładuje po ścieżce pliku. Sekwencja
   uploadu (w tym ewentualna tablica MMU) może się różnić — A6000 może nie wysłać
   tego, czego nowy firmware oczekuje.

### Werdykt

**Da się podmienić i — po dowodzie ze schematów — jest to realny eksperyment,
a nie fantazja.** Ten sam układ, ten sam rozmiar, ten sam adres bazowy.
Nadal jednak **nie ma podstaw sądzić, że zadziała w pełni**: blokują rzeczy
z listy powyżej (MMU, 5 dodatkowych bloków rejestrów, sprzężenie z kodem SoC
z 2014 r.). Realistyczny scenariusz: kamera wstaje, ale nie inicjuje matrycy
(czarny ekran) albo nie ma AF. Scenariusz katastrofalny (brick) jest mało
prawdopodobny, bo plik leży w `/usr`.

**Oczekiwanie:** ~30–40% szans, że zadziała w całości; wyżej, że częściowo
(np. matryca wstanie, AF nie); bardzo nisko, że uszkodzi kamerę nieodwracalnie.

## 4. Otwarta kwestia, którą trzeba rozstrzygnąć **przed** próbą

**Czy A6000 uruchamia DFE z pliku `/usr/dfe/dfe.bin`, czy z kopii wbudowanej
w `av-cam.bin` pod `0xA67F00`?**

Fakt: `dfe.bin` leży w `av-cam.bin` **bit w bit** (offset `0xA67F00`), a jednocześnie
istnieje jako osobny plik i `av-cam.bin` zawiera string `/usr/dfe/dfe.bin`
(w towarzystwie nazw klas `Camera::ZPD::Control`, `…::AsyncSequencer`, `…::Detect`).

Jeśli ładowana jest kopia wbudowana, **podmiana pliku nic nie zmieni** — trzeba by
patchować `av-cam.bin` (partycja `nflasha3`, też reflashowalna, ale większe ryzyko).

Czego nie udało się ustalić: kod jest **PIC** (position-independent) — nie ma
literałów ze ścieżką, a skan `ADR`/`LDR` literałowych nie znalazł odniesień.
Ghidra na `av-cam.bin` (11 MB) przekroczyła limit startowy 330 s.
**Potrzebne:** dłuższy limit (`REA_GHIDRA_STARTUP_TIMEOUT_MS`) albo analiza
offline w Ghidrze z GUI.

## 5. Proponowana kolejność eksperymentów (od najtańszego)

| # | eksperyment | ryzyko | co rozstrzyga |
|---|---|---|---|
| 1 | **A/B: podmienić `/usr/dfe/dfe.bin` na kopię z wyzerowanym fragmentem** (np. uszkodzić wektor resetu), z przeliczeniem CRC32 | niskie | **czy plik jest w ogóle używany** — jeśli kamera działa identycznie, liczy się kopia w `av-cam.bin` |
| 2 | podmienić plik na blob A6300 (`analysis/dfe-a6300.bin`) | niskie/średnie | czy nowsza generacja wstaje na starszej rewizji |
| 3 | jeśli 2 zawiedzie — patch kopii w `av-cam.bin` (`nflasha3`) | średnie | czy ładowana jest kopia wbudowana |

Eksperyment 1 jest kluczowy i **nie wymaga blobu A6300** — to najczystszy test
„który obraz jest źródłem prawdy".

## 6. Ograniczenia analizy

- Wnioski o MMU opierają się na obecności instrukcji CP15 i stringu, nie na
  znajomości konkretnej rewizji krzemu.
- Nie wiadomo, czy `0x01013xxx`–`0x01016xxx` istnieją w A6000 (brak dokumentacji
  i brak zrzutu rejestrów z żywego układu).
- Nie ustalono, który obraz (plik vs kopia w `av-cam.bin`) jest ładowany.
- Porównanie robione na obrazach z firmware; **żaden test nie był wykonany na sprzęcie**.
