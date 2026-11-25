# 14 — Selektor EFCS/Electronic: od uceglenia do działającej migawki elektronicznej

To jedyna znana próba *dodania funkcji* — selektora trybu migawki — i zarazem ta, która
najpierw ucegliła aparat, a potem okazała się działającą drogą do cichej migawki. Kod
selektora w BIONZ robił swoje, ale sygnał ginął: prawdziwym produktem bajtu `pkt[0x0e]`
okazał się konstruktor **wysyłki** `0x438d0064`, nie konstruktor capture (R54). Po
przekierowaniu wysyłki **migawka elektroniczna działa od 3.30** (04-11-2026). Ten sam
cykl ujawnił drugą rzecz: **EFCS włączony wychodzi czarny od 1/1000 także na czystym
firmware Sony** (R57 §5) — to wada samej ścieżki aparatu, naprawiana później tablicą
kalibracyjną w NVRAM (R84–R86).

> **Źródło i status.** Z [`nicolvus/a6000-fw-decomp`](https://github.com/nicolvus/a6000-fw-decomp),
> raporty E25-24, E25-24b, E25-25, E25-26, E25-27, E26-R52, R53 (selektor), R54–R57
> (elektroniczna), R66–R68 (czarne EFCS), R84–R87 (Darwin v3, tablice EFCS), z pomiarami na
> prawdziwym aparacie (sonda SWD). Etykiety ich autorstwa zachowane. **Nie sprawdzone przez
> nas.** Zaktualizowano 25-11-2026.

## 1. Pomysł

A6000 nie ma pozycji „Silent" w menu. Ma natomiast ustawienie **EFCS on/off**, którego
wartość ląduje w jednym polu: `+0x210` bloku `0x43edf684` (`0` = EFCS włączony,
`1` = wyłączony — zmierzone w T012, odwrotnie niż zakładał wcześniejszy test). Patch
wykorzystuje to ustawienie jako dwustanowy selektor trybu:

| Menu | Model | `+0x210` | Tryb | Tylna kurtyna |
|---|---|---|---|---|
| EFCS włączony | `0x2b4` | 0 | EFCS | mechaniczna (ścieżka Sony) |
| EFCS wyłączony | `0x2b5` | 1 | ELECTRONIC | brak (Darwin tłumi cewki i silnik) |

Bez nowej pozycji menu i bez reinterpretacji zapisanego bajtu: nowe znaczenie jest
przenoszone per zdjęcie, w bajcie pakietu capture.

## 2. Łańcuch, od końca do końca

```
libObj (userland)  akcja 0x6896ac -> komunikat 0x75fa -> parametr 0x9776
                   konwerter 0x68c24a: 1 -> 0x2b4, 2 -> 0x2b5
                   sekwencja 0x95a308 -> selektor LIRO 0x4099 -> konwerter 0x99e968
                   bufor 9 B: [+0]=05, [+2..3]=99 40, [+8]=0/1
        | LIRO
        v
wpis tablicy LIRO 0x4099 (offset 0xabe954) -> handler 0x43802e4c
        ldrb r2,[r0,#8] ; str.w r2,[0x43edf684 + 0x210]
        v
0x43844e80   czyta (*ctx)+0x210, zapisuje słowo do param6+0x41c
        v
0x43841070   konstruktor capture
   |- 0x43842158  czyta [sb+0x41c], liczy klasę ekspozycji 0..7
   |- PATCH: pkt[0x0e] = [sb+0x41c]   (obie gałęzie)
   v  pakiet 0x0c, 22 B, przez CAIF
Darwin 0x17f8c: kopiuje pakiet do S+0x30 (S = 0x200036d8)
       0x17ff8/0x17ffc: pkt[0x0e] -> S+0x3e (0x20003716)
        v
Darwin 0x20c74 / 0x1fe66 -> cave 0x4318 -> 0x1b080 (EFCS) albo 0 (Electronic)
        v
P4D/P4E i silnik: normalnie przy EFCS, stłumione przy Electronic
```

Reszta ścieżki capture jest nietknięta: `0x437f8a50` buduje `cap+0x64c/0x6bc`,
`0x438c830c` woła `SetExposure`, `0x438c831e` `SetRead`, `0x438c8330` `Execute(1)`,
a `0x43901a8c` wysyła pakiet `0x107`. Selektor decyduje wyłącznie o tym, czy Darwin może
cokolwiek ruszyć.

## 3. Dwie cave'y

**BIONZ, `av-cam.bin`** — 20 bajtów pod `0x43541800`, w zarezerwowanym obszarze nagłówka
LIRO (zera w A6000 i A7S, brak literałów i celów skoków):

```
00 23          movs r3,#0            ; zostawia r3=0, żeby pkt[1] zostało 0x40
23 70          strb r3,[r4]          ; pkt[0] = 0
d9 f8 1c 24    ldr.w r2,[sb,#0x41c]  ; pole EFCS
a2 73          strb r2,[r4,#0xe]     ; pkt[0x0e] = tryb
01 29          cmp r1,#1
01 d0          beq +2
ff f2 70 bd    b.w 0x43841576        ; druga (oryginalna) gałąź
70 47          bx lr
```

Zmieniane są trzy miejsca wokół: `0x4384133e` (skok warunkowy → 2 × `nop`), `0x43841342`
(`→ bl 0x43541800`) i `0x43841476` (późniejszy bezwarunkowy zapis → `nop`, żeby nie
nadpisał bajtu). Wcześniejsze umieszczenie pod `0x43541a80` odrzucono — okazało się, że to
wnętrze 512-bajtowego obiektu z wpisem w GOT.

**Darwin, `darwin_core.bin`** — 14 bajtów pod `0x4318` plus literał pod `0x4330`:

```
ldr r2,[pc,#0x14]   ; -> 0x4330 = 0x20003716 (S+0x3e)
ldrb r2,[r2]
cbz r2, +2          ; 0 -> ścieżka oryginalna
movs r0,#0
bx lr               ; != 0 -> zwróć 0 (bez cewek, bez silnika)
b.w 0x1b080
```

Przekierowane są dwa miejsca wywołań: `0x20c78` (typ cewki, `0x20c74`) i `0x1fe6c` (bramka
silnika, `0x1fe66`). `0x4318..0x4327` i `0x4330..0x4333` to zerowe wpisy tablicy wektorów
(70 i 76). To **zastępuje** patche typ 0/B1a: wychodzi z oryginalnego Darwina, więc EFCS
dostaje prawdziwą ścieżkę mechaniczną, a Electronic tłumienie per zdjęcie.

## 4. C3-B: strona ekspozycji

Stłumienie mechanizmu to za mało — matryca musi zintegrować i zostać odczytana bez tylnej
kurtyny; to osobny patch (E25-26), wpięty pod `0x438c82fe`, warunkowany tym samym
`pkt[0x0e] == 1`, ustawiający `ShutMode 0` i linię startu `r5` zamiast natywnego producenta
`0x4383fa40`. Ich zmierzony model ekspozycji to `T + ~7 ms + 15,2 µs × wiersz`
(odczyt ≈ 61 ms), czyli bez tego czasu migawki od 1/4000 do 1/500 prawie się nie skalują.

Natywna instalacja `ShutMode`, dla porządku: klasa z `0x43842158` → `record+0x6d` →
`0x4383fd6c` kopiuje 16 bajtów (`record+0x64..0x73`) do celu → klasa ląduje w `cap+0x655`
→ `0x438c828c` woła `SetExposure` z `cap+0x64c` (pomijane, gdy `cap+0x4b9c≠0`; klasy
urządzeń 2/3 nadpisują selektor zerem) → slot `+0x28` → IMX210 `0x436d6f6c` → rejestr
`0x4401ca2c` → lista P2S `0x43fe995c`, indeks 1.

## 5. Co aparat faktycznie zrobił

| Wersja | Wynik |
|---|---|
| 3.25 | **cegła.** Ten sam payload zawierał też zrekompresowany `nflasha3`; patrz [12](12-format-partycji.md). Przyczyną był format partycji, nie selektor |
| 3.25c / 3.27 | startuje; pierwszy dowód, że poprawnie zbudowany `nflasha3` się ładuje (`idt_cam.bin` tam, gdzie 3.25 dawał −302) |
| 3.27, EFCS off | selektor działa *wewnątrz* BIONZ: `+0x210 = 1` → `cap+0x41c = 1` → cave pisze `pkt[0x0e] = 1` → zaobserwowane breakpointem (`r1=1`, `pc=0x43541800`); watchpoint zapisu potwierdził, że cave zapisuje 1. Wartość żyje **< 1 ms** w buforze konstruktora, a bufor *wysłany* czyta 0 |
| 3.27, próbkowanie | 1 widziane raz przez AHB w momencie zdjęcia, nigdy w buforze wychodzącym; późniejszy raport wycofał jeden „rutynę wysyłki" (`0x4382fac8` to konwersja na µs, nie nadawca) |
| 3.29 | cave przepisana tak, żeby czytać pole EFCS na żywo zamiast `[sb+0x41c]`; **wgrana i zmierzona**: pakiet capture niesie 1, ale 2 ms później bufor wraca do pakietu spoczynkowego (`pkt[0x0e]=0`), czyli coś go przywraca. Dźwięk bez zmian („el fix no funciona") |
| 3.30 | **elektroniczna działa.** Prawdziwy producent `pkt[0x0e]` to konstruktor wysyłki `0x438d0064` (`strb.w r3,[r2,#0x4e]` pod `0x438d01fa`), który nadpisywał 1 selektora przy każdym wysłaniu (R54 §1). Nowa 16-bajtowa cave pod `0x43541820` wpina się w `0x438d01fa` i pisze `pkt[0x0e]` = ustawienie EFCS przy *każdym* wysłaniu. Zdjęcie bez kurtyny potwierdzone przez użytkownika (EFCS off, MEDIDO). Ekspozycja: dopiero z patchem RAM aplikacji (ShutMode 0 + `r5`, kalibracja 1/250), patrz [13](13-patch-darwina.md) |
| 3.33–3.35 | **bez cave'ów, blok TPZL 0 nienaruszony** (zmieniają się tylko bloki 48 i 57): patch inline w samym `0x438d0064` (3.33), a od 3.34/3.35 także w konstruktorze zdjęcia `0x43841070`, obejmujący obie gałęzie (R56). Wiszący adb z [11](11-odzysk-swd.md) okazał się skutkiem zmodyfikowanego bloku 0 — po jego odtworzeniu adb działa (R56 §4) |
| 3.36 / 3.37 | komora Darwina `== 1` nie była przyczyną czarnych klatek: na **oficjalnej treści Sony 3.37** EFCS włączony wychodzi czarny od 1/1000, także na mechanicznej migawce — to wada samej ścieżki EFCS w tym aparacie, nie patcha (R57 §5). Referencją ekspozycji jest EFCS off na 3.37 (pełny mechaniczny) |
| 3.43 + tablica w NVRAM | Darwin v3 (R82–R84): ta sama komora plus tabela kompensacji czytana z **NVRAM** `0x1850000+0x48`. Z tablicą testową (`c` = 2000 µs na wszystko) EFCS włączony **przestaje wychodzić czarny, włącznie z 1/4000** (MEDIDO) — zapis NVRAM rzeczywiście dochodzi do Darwina |
| 3.76 / 3.77 | trzy tryby wypoziomowane (R85–R87): mechaniczny = referencja; EFCS wyrównany skalibrowaną tablicą w NVRAM (strata ≈ 1,0–1,25 ms); Silent w obrazie (hook `0x438c82fe`, ten sam co C3-B: ShutMode 0 + `r5` z Tv, cap 4218 ≈ 1 linia opóźnienia). CFW 3.76 zainstalowany 11-11, tablica EFCS zapisana skryptem service-mode |

Ich najnowsze pomiary (R53 §7) lokują prawdziwego emitenta zdarzenia 1 pod `0x436b8a50`
(kopiuje `payload+0x40` → `0x43f91e32`); na breakpoincie tam widok CPU bufora pokazuje
`pkt[0x0e]=0`, a widok AHB tego samego adresu 1 — artefakt spójności cache, który czyni
część wcześniejszego próbkowania niewiarygodną. (To akapit historyczny: R54 rozwiązał
zagadkę prościej — nadpisującym wysłaniem.)

### 5a. Po 04-11: czarne EFCS i naprawa tablicą

Czarne klatki przy EFCS włączonym (na 3.35/3.36 i na czystym Sony) mają zmierzoną
przyczynę czasową: strata ≈ **1,0–1,25 ms** w pętli EFCS (R85), do tego pionowy gradient —
różnica między górą a dołem klatki rośnie od ≈0,9 ms (1/350) do ≈1,8 ms (1/3000) (R83 §5).
Naprawa nie była w BIONZ: Darwin czyta tablicę kompensacji z **NVRAM** (`0x1850000+0x48`,
56 B, checksum, synchronizacja do flasha), a Darwin v3 (R82–R84, in-situ
`0x18d6e..0x18e0f`) stosuje `c` per czas. Zdjęcia DSC03749–03806 dały skalibrowane
tablice (R85, R86); przewidywana ekspozycja 0,985–1,015·T od 1/4000 do 1/30.

Limity (MEDIDO): gradientu pionowego tablica nie wyrównuje — EFCS jest równy tylko
uśredniony, od ~1/1000 w górę używać mechanicznego albo elektronicznego (R85 §3.1).
Silent szybko: powyżej ~1/600 model daje ≤ 0 linii, czyli podłoga ekspozycji ≈ 1,7 ms
ekwiwalentu (`r5` cap 4218); patch subliniowy pod ten limit istnieje tylko w emulacji,
bez CFW (G38).

## 6. Dlaczego nie zrobili bramki w Darwinie „lepkiej"

Oczywisty następny krok — zatrzasnąć 1 w Darwinie, żeby przetrwało pakiety spoczynkowe —
nie mieści się: w tablicy wektorów obok istniejącej cave są **2 wolne bajty**, „strefa NOP"
pod `0xdf06` (80 B) jest w rzeczywistości funkcją wołaną z `0xdfbe`/`0xdfcc`, a w kodzie nie
ma dziur z zerami. Dlatego zmiana przeniosła się do źródła danych w BIONZ.

## 7. Ograniczenia

- **Migawka elektroniczna działa** — od 3.30 (R54), z kalibrowaną ekspozycją od 3.35
  (R56 §7) i w obrazie od 3.76 (R86). Pierwszy działający krok na sprzęcie pozostaje 3.23
  ([13](13-patch-darwina.md)).
- **EFCS włączony ma wadę sprzed patcha:** czarny od 1/1000 na oficjalnym Sony 3.37
  (R57 §5). Przyczyna fizyczna nieznana (kandydaci: kalibracja utracona przy odzysku,
  hardware sensora/kurtyny — NO VERIFICADO); kompensowana tablicą NVRAM z limitami z §5a.
- Nie wiadomo, co Darwin dostaje w momencie zdjęcia ani co widzi bramka `0x4318`; odczyt
  RAM Darwina (`0x20003716`) wymaga sondy na `CN4906` piny 11/12 (to linie SWD BIONZ, nie
  Darwina).
- W BIONZ opóźnienie w łańcuchu wywołań powoduje, że `S+0x30..0x47` jest czyszczone tylko
  na starcie zadania (`0x196fa`, wołane raz z `0x1815c`); `0x1b080` czyta 24 miejsca,
  a tylko `0x20c78`/`0x1fe6c` przechodzą przez cave.
- **Podejście cave'owe zostało wycofane:** od 3.33 patche BIONZ są inline, bez cave'ów,
  z blokiem TPZL 0 nienaruszonym (zmieniają się bloki 48/57); to też rozwiązało wiszący
  adb (R56 §4). Pozostałe cave'y BIONZ (`0x43541800/1820/1840`) i komora Darwina `0x4318`
  zostają w buildach CFW.
- Trójstan (MECHANICAL/EFCS/ELECTRONIC) zrealizowano inaczej niż zaprojektowano: nie przez
  trzecią trwałą wartość w menu, tylko przez kompozycję — Silent w obrazie warunkowany
  swoim bajtem (`cap+0x41d`), EFCS wyrównany tablicą NVRAM, mechaniczny bez zmian (R86 §1).
- Powtórzenie ich przebiegu oznacza wgranie zmodyfikowanego firmware (instalacja
  `pmca-console firmware`, często pierwszy `0x1063` do powtórzenia) — ryzyko bez zmian:
  **brak niezależnego odzysku** (E24-04/E25-04), droga powrotem to [11](11-odzysk-swd.md).

## 8. Dlaczego to ważne dla nas

To odpowiada — kodem i pomiarami — na pytanie, które nasze
[10-pytania-otwarte.md](10-pytania-otwarte.md) zostawia otwarte: tryb migawki A6000 nie jest
ukrytym enumem czekającym na przełączenie. Aparat ma w tej ścieżce dokładnie dwa stany
(EFCS on/off), matryca dostaje instrukcje z pola `ShutMode` per zdjęcie, a tłumienie
mechaniki jest właściwością komórki konfiguracyjnej Darwina — dlatego działa patch
2-bajtowy. Funkcja w BIONZ zaczęła działać dopiero, gdy patch objął prawdziwego
producenta bajtu (konstruktor wysyłki, R54), a ekspozycję skalibrowano osobno — najpierw
patchem RAM, potem hookiem w obrazie (R86).

Raporty: [E25-24](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-24-selector-efcs-electronico.md) (audyt i blokady),
[E25-24b](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-24b-implementacion-selector.md) (implementacja, cave'y, emulacja),
[E25-26](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-26-c3b-exposicion-electronica.md) (C3-B),
[E25-27](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-27-construccion-firmware-integrado.md) (build zintegrowany),
[R52](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r52-prueba-fisica-selector-327.md) / [R53](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r53-paquete-329-ajuste-efcs-en-vivo.md) (co zmierzył aparat),
[R54](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r54-paquete-330-envio-pkt0e.md) (wysyłka, pierwsza elektroniczna),
[R56](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r56-paquete-333-envio-inline.md) (inline, 3.33–3.35, kalibracja),
[R57](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r57-paquete-336-darwin-eq1.md) (komora ==1, czyste EFCS na Sony),
[R66](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r66-bloques-darwin-en-nvram-1850000.md) (bloki Darwina w NVRAM),
[R84](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r84-darwin-v3-en-camara.md) (Darwin v3 na aparacie),
[R85](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r85-calibracion-fotos-3749-3779.md) / [R86](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r86-cfw-376-tres-modos-nivelados.md) (tablice EFCS, trzy tryby).
