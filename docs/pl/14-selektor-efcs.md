# 14 — Selektor EFCS/Electronic: czemu menu działa, a migawka nie

To jedyna znana próba *dodania funkcji* — selektora trybu migawki — i zarazem ta, która
ucegliła aparat. Kod jest na miejscu i robi to, co miał robić, wewnątrz BIONZ; sygnał,
który produkuje, nie dochodzi do Darwina w sposób wiarygodny. Na 04-11-2026 migawka
elektroniczna nie działa.

> **Źródło i status.** Z [`nicolvus/a6000-fw-decomp`](https://github.com/nicolvus/a6000-fw-decomp),
> raporty E25-24, E25-24b, E25-25, E25-26, E25-27, E26-R52, E26-R53, z pomiarami na
> prawdziwym aparacie (sonda SWD). Etykiety ich autorstwa zachowane. **Nie sprawdzone przez nas.**

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

Ich najnowsze pomiary (R53 §7) lokują prawdziwego emitenta zdarzenia 1 pod `0x436b8a50`
(kopiuje `payload+0x40` → `0x43f91e32`); na breakpoincie tam widok CPU bufora pokazuje
`pkt[0x0e]=0`, a widok AHB tego samego adresu 1 — artefakt spójności cache, który czyni
część wcześniejszego próbkowania niewiarygodną.

## 6. Dlaczego nie zrobili bramki w Darwinie „lepkiej"

Oczywisty następny krok — zatrzasnąć 1 w Darwinie, żeby przetrwało pakiety spoczynkowe —
nie mieści się: w tablicy wektorów obok istniejącej cave są **2 wolne bajty**, „strefa NOP"
pod `0xdf06` (80 B) jest w rzeczywistości funkcją wołaną z `0xdfbe`/`0xdfcc`, a w kodzie nie
ma dziur z zerami. Dlatego zmiana przeniosła się do źródła danych w BIONZ.

## 7. Ograniczenia

- **Migawka elektroniczna nie działa.** Działającym wynikiem na sprzęcie pozostaje 3.23
  (patch 2-bajtowy Darwina, [13](13-patch-darwina.md)).
- Nie wiadomo, co Darwin dostaje w momencie zdjęcia ani co widzi bramka `0x4318`; odczyt
  RAM Darwina (`0x20003716`) wymaga sondy na `CN4906` piny 11/12 (to linie SWD BIONZ, nie
  Darwina).
- W BIONZ opóźnienie w łańcuchu wywołań powoduje, że `S+0x30..0x47` jest czyszczone tylko
  na starcie zadania (`0x196fa`, wołane raz z `0x1815c`); `0x1b080` czyta 24 miejsca,
  a tylko `0x20c78`/`0x1fe6c` przechodzą przez cave.
- Trójstan (MECHANICAL/EFCS/ELECTRONIC) zaprojektowano, ale nie zaimplementowano: wymagałby
  trzeciej trwałej wartości, a A6000 nie wystawia ustawienia Silent w menu.
- Powtórzenie ich przebiegu oznacza wgranie zmodyfikowanego `nflasha3` — patrz
  [12](12-format-partycji.md), ile to kosztuje, i [11](11-odzysk-swd.md), jak wrócić.

## 8. Dlaczego to ważne dla nas

To odpowiada — kodem i pomiarami — na pytanie, które nasze
[10-pytania-otwarte.md](10-pytania-otwarte.md) zostawia otwarte: tryb migawki A6000 nie jest
ukrytym enumem czekającym na przełączenie. Aparat ma w tej ścieżce dokładnie dwa stany
(EFCS on/off), matryca dostaje instrukcje z pola `ShutMode` per zdjęcie, a tłumienie
mechaniki jest właściwością komórki konfiguracyjnej Darwina — dlatego działa patch
2-bajtowy, a funkcja za 100 bajtów w BIONZ jeszcze nie.

Raporty: [E25-24](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-24-selector-efcs-electronico.md) (audyt i blokady),
[E25-24b](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-24b-implementacion-selector.md) (implementacja, cave'y, emulacja),
[E25-26](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-26-c3b-exposicion-electronica.md) (C3-B),
[E25-27](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-27-construccion-firmware-integrado.md) (build zintegrowany),
[R52](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r52-prueba-fisica-selector-327.md) / [R53](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r53-paquete-329-ajuste-efcs-en-vivo.md) (co zmierzył aparat).
