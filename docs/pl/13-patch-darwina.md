# 13 — Darwin: dwa bajty, które zatrzymują migawkę mechaniczną

„Cicha migawka", która działa na prawdziwym A6000, to nie patch BIONZ. To dwa bajty
w firmware **Darwina** — MCU zasilania/migawki (`IC5700`, `MB9AF004BGL`, Fujitsu FM3
Cortex-M3). Ta strona odtwarza, co te dwa bajty robią i co zostaje nietknięte.

> **Źródło i status.** Z [`nicolvus/a6000-fw-decomp`](https://github.com/nicolvus/a6000-fw-decomp),
> raporty E25 (dezaktywacja mechaniczna), E24-05a/d, E25-02, E25-05 (pakowanie) oraz testy
> na aparacie T024/T040. Etykiety ich autorstwa zachowane. Zachowanie potwierdzone na
> sprzęcie (cichy strzał bez błędu); *skutki uboczne* — nie. **Nie sprawdzone przez nas.**

## 1. Cel

| Element | Wartość |
|---|---|
| Plik | `0640_darwin/darwin_core.bin`, 157 276 B |
| Baza ROM | `0x4200` — adres ROM = offset pliku + `0x4200` |
| Własny bootloader | `0x0–0x41ff` (osobny od aplikacji) |
| String wersji | `VER0.78` pod `0x25b3c` |

Darwin podejmuje dwie niezależne decyzje i obie czytają **tę samą komórkę**
`[0x20000050 + kanał]` przez `0x1b080`:

```
0x1b080   presence = [0x200002c0 + ch]; jeśli 0 -> zwróć 0
          byte = [0x20000050 + ch]
          górny nibble (0..5, >=6 -> 0) = bramka : silnik / naciąg dozwolony?
          dolny nibble (bity 0..2)      = typ    : napęd cewek P4D/P4E?
```

| Funkcja | Czyta | Steruje |
|---|---|---|
| `0x20c74` | dolny nibble | typ cewki; czterej pisarze (`0x20c90/0x20cb2/0x20cd4/0x20d00`) pytają ją przed dotknięciem P4D/P4E (`0x234`/`0x238`) |
| `0x1fe66` | górny nibble | bramka silnika i naciągu; **12 konsumentów** |

## 2. Dlaczego nie ma skrótu „zmiennej ulotnej"

Oczywisty pomysł — ustawić ten bajt konfiguracji w czasie działania zamiast patchować kod —
nie działa:

- **W `darwin_core` nie ma statycznego pisarza `0x20000050`**: brak literału adresu, brak
  aliasu bitowego `0x22000a00`, a skan pod `str [rX,#0x50]` nie znajduje realnej instrukcji.
- `InitCom 0x12` zapisuje cały blok `0x78` B od podstawy wyrównanej do `0x78`; żeby dojść do
  `+0x50`, trzeba wysłać co najmniej `0x51` B, w tym pola watchdoga `+0x40..+0x43`.
- `InitCom 0x16` *zrobiłby* zapis absolutny 1 bajtu (`0x20000050`, długość 1) — to jedyna
  selektywna ścieżka w kodzie — ale **nie znamy nadawcy tej ramki po stronie BIONZ**,
  a zadanie COM istnieje tylko podczas `Seton`, nie podczas zdjęć.
- SRAM Darwina jest stale zasilana: normalne wyłączenie tego nie cofa.

## 3. Patch „typ 0" — cewki

```text
0x20c74: ...            ; typ mechanizmu/cewki z dolnego nibble
0x20c78: 09 e0          b 0x20c8e
0x20c7a: 00 bf          nop
0x20c7c: 00 bf          nop
0x20c7e: 00 bf          nop
```

`0x20c74` zwraca teraz zawsze 0 — czyli istniejącą gałąź oryginalnego kodu („brak cewek").
P4D/P4E nigdy nie są napędzane. Wgrane jako **3.22** (T024); aparat wystartował.

## 4. Patch „B1a" — silnik

```text
przed:   0x1fe66: 70 b5        push {r4,r5,r6,lr}
         0x1fe68: 00 25        movs r5,#0
         0x1fe6a: 28 46        mov r0,r5        <- patchowany
         0x1fe6c: fb f7 08 f9  bl 0x1b080
         0x1fe70: 04 09        lsrs r4,r0,#4
         0x1fe72: 06 2c        cmp r4,#6
         0x1fe74: 05 d2        bhs 0x1fe82
         0x1fe76: df e8 04 f0  tbb [pc,r4]
         0x1fe82: 28 46        mov r0,r5
         0x1fe84: 70 bd        pop {r4,r5,r6,pc}

po:      0x1fe6a: 0a e0        b 0x1fe82        (zmienione 2 bajty)
```

Skok leci prosto do epilogu: nibble nie jest czytany, `r5` zostaje 0, ramka stosu nietknięta.
Offset pliku `0x1bc6a` = 113770. Wgrane jako **3.23** (T040): aparat strzelał cicho, bez
błędu, 36/36 klatek.

## 5. Co to zmienia dalej

Bramka ma 12 konsumentów; przy zwracanym 0:

| Miejsce | Funkcja | Skutek |
|---|---|---|
| `0x1f5a2` | thunk trzech starterów + 3 impulsy serwisowe | wszystkie trzy wybierają listę **L0** |
| `0x1f5a6` | bezpośredni naciąg | wraca pod `0x1f5ae`, silnik nigdy nie włączony |
| `0x1f4b6`, `0x1f4ce`, `0x1f572` | impuls serwisowy, sprawdzenie i odczyt krzywki | pominięte / zwracają 0 |
| `0x1f88a`, `0x1f8fc`, `0x1fa3a`, `0x1fe86`, `0x201b0` | maszyna wewnętrzna, timeout, motor=2 | nieosiągalne z L0 albo bez efektu |

Trzy startery wybierają listę stanów z tabeli:

| Starter | Bramka = 4 (normalnie) | Bramka = 0 |
|---|---|---|
| `0x1fee2` (load) | `0x29cdd` = `[0,2,3,6,9,10]` (L1) | `0x29cd8` = `[0,7,8,9,10]` (**L0**) |
| `0x1ff72` (capture, stan 4) | `0x29ce3` = `[0,4,5,6,9,10]` (L2) | L0 |
| `0x1ffce` (capture, stan 5/0x1f) | `0x29ce9` = `[0,1,4,5,6,9,10]` (L3) | L0 |

L0 wykonuje `0x20100` (zaznacza zajętość, czeka `0x8ca0`), `0x2014c` (woła `0x20c90`, czeka
`0x5dc0`), `0x200e2` (czeka/kończy), `0x200e6` (`0xd18e(0x1000000)`, zwalnia zajętość)
i `0x200fc` (koniec). Wewnętrzna maszyna 27 stanów startuje tylko ze stanów zewnętrznych
2 i 4 (`0x20126`/`0x2013a`), których L0 nie zawiera.

**Typ 0 jest obowiązkowy, nie opcjonalny:** stan 7 z L0 nadal woła `0x20c90`, czyli nadal
próbuje pisać P4D — bramka nie filtruje cewek, tylko silnik. Bez patcha typu 0 ten zapis
by doszedł.

## 6. Co zostaje żywe

| Element | Stan | Komentarz |
|---|---|---|
| **Operacja 5 (hamulec)** | aktywna | `0x1f600 → 0x1fcb8 → 0x1feb6` pisze P40=P41=1 (`PDOR4 0x51cc`, `r1=3`, `r2=0xfffc`), bez bramki. Przy bramce XOR, która faktycznie jest w schemacie ([16](16-serwisowka.md) §5.3), `1⊕1 = 0`, czyli brak napędu — słowo „hamulec" to interpretacja, nie odczyt schematu. Efekt fizyczny niezmierzony |
| `P4B` (`0x22c`, bit 11) | aktywny | sygnalizacja zajętości, maska `0x800` |
| `P4C` (`0x230`) | aktywny | ustawiany/czyszczony na każde zdjęcie przez `0x1ecec`; koryguje wcześniejsze twierdzenie, że pisane jest tylko 0 |
| Błąd 6 pod `0x1989c` | aktywny | kontrola pozycji z ADC; może zakolejkować operację 5, sam silnika nie ruszy |

Poprawne twierdzenie jest więc węższe niż „migawka nie żyje": **żadnego napędu silnika
i żadnego impulsu cewek przy zdjęciu i naciągu**, z hamulcem awaryjnym nadal podłączonym.

## 7. Ograniczenia

- **Brak niezależnego odzysku**, jeśli spatchowany Darwin nie wystartuje: ten sam MCU
  steruje zasilaniem. Dlatego patch ma 2 bajty i dlatego nic więcej w Darwinie nie jest
  ruszane.
- Nie wykazano, że watchdog toleruje długość L0 (`0x8ca0 + 0x5dc0` ticków, jednostka
  niemierzona).
- Nietestowane na sprzęcie: lampa błyskowa, wideo, Live View pod patchem; operacja 5;
  konsumenci P4B/P4C (w SoC nie zlokalizowano odbiorcy).
- Wszystko powyżej to analiza osiągalności plus model obwodu z service manuala; fizyczny
  bezruch wnioskujemy z 36 cichych zdjęć i jednej analizy RAW, nie z sondowania P40/P41.

## 8. Dlaczego to ważne dla nas

Nasz [01-sprzet.md](01-sprzet.md) wymienia `IC5700 = MB9AF004BGL` „Darwin" jako układ
zasilania, który startuje SoC. To ten sam element, a patch wyjaśnia migawkę: MCU jest
prawdziwym kontrolerem z własną maszyną stanów, nie tylko sekwencerem zasilania. Daje też
konkretne nazwy GPIO (P40/P41 silnik, P4D/P4E cewki, P4B/P4C zajętość), których nasze
[01](01-sprzet.md) i [02](02-struktura-firmware.md) nie zawierają.

Raporty: [E25](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-desactivacion-mecanica.md) (mechanizm, 12 konsumentów, macierze),
[E25-05](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-05-preparacion-paquetes-323-324.md) (pakowanie 3.23/3.24),
[E24-05a](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e24-05a-captura-fin-bionz-darwin.md) (protokół BIONZ↔Darwin),
[darwin-shutter-entrypoints](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/darwin-shutter-entrypoints.md) (baza Ghidry `0x4200`, mapowanie ADC).
