# 12 — Obrazy partycji: TPZL i reguły zmieniania obrazu

[03](03-integralnosc.md) pokazuje, że **niezmieniony** pakiet Sony da się przepakować
bit w bit. Ta strona jest o następnym kroku: zmianie **treści** obrazu partycji. Format
jest nieudokumentowany, dekompresor jest sprzętowy, a pomyłka ucegla aparat w sposób,
którego nie wykryje żaden test programowy.

> **Źródło i status.** Zrekonstruowane przez
> [`nicolvus/a6000-fw-decomp`](https://github.com/nicolvus/a6000-fw-decomp) z
> `bootloader.bin` (Loader3 + ARM7 „BossFirm"), z GPL-owego `cmpr.c` Sony oraz z korpusu
> 16 obrazów Sony (raporty E26-R15, R16, R17, R30, R36, R39, R45; X–XI 2026).
> Etykiety ich autorstwa zachowane. **Nic nie zostało przez nas sprawdzone na sprzęcie.**
> Jedyne istniejące potwierdzenie sprzętowe jest pośrednie: aparat wystartował z obrazu
> zbudowanego według tych reguł.

## 1. Czym jest TPZL

Sony'owski kontener kompresji obrazów partycji (`nflasha3`, `nflasha15`, …). Nie ma
publicznej specyfikacji ani próbki spoza aktualizacji Sony.

```
TOC (np. 369 bloków)  →  blok  →  16 rekordów × 4096 B
                                 ├─ stored:  0F 00 <u16 4096> + 4096 B
                                 └─ LZ77:    F0 …
```

## 2. Reguły

| Reguła | Wartość | Dowód |
|---|---|---|
| Wyrównanie offsetu bloku | **512 B** (reszta 0) | `cmpr_demand_wlen`, cały korpus Sony |
| Rekordy na blok | **zawsze 16 × 4096 B** | ARM7 przekazuje `blok >> 12` do LDEC |
| Maks. rozmiar skompresowanego bloku | `(blok/4096) × 4112 + 8` → **65 800 B** dla 64 KiB | `cmpr.c` |
| Wypełnienie między blokami | `0x00`, nie `0xFF` | korpus Sony |
| Sektory na odczyt | **≤ 126** w `nflasha3`; > 128 powoduje podział odczytu przez ARM7 na dwie tury | Sony; Linux ćwiczy podział w `nflasha15/16`, Loader3 — nigdy |
| Rozmiary w TOC | wielokrotności 512 | korpus Sony |

## 3. Droga sprzętowa, której nikt nie modeluje

```
Loader3 (BIONZ)  →  struktura żądania  →  ARM7 (op 0)  →  LDEC (sprzętowy dekompresor)
```

- `c01fdd8e`: `residuo = offset & 0x1ff`. Przy wartości ≠ 0 Loader3 **tylko wypisuje
  ostrzeżenie** i czyta całe sektory od `offset >> 9`, w liczbie
  `(residuo + size + 0x1ff) >> 9`.
- Struktura robocza niesie `{n, lista sektorów, residuo (+8), registros = blok>>12 = 16
  (+0xc), destino (+0x10), rozmiar}`.
- Handler ARM7 (`0x1338`, `0x3f4`) kopiuje **`+0xc` (liczba rekordów) i `+0x10` (cel)**.
  Pola `+8` (reszta) **nie czyta żadna instrukcja**.

Czyli przy reszcie 256 B strumień podany do LDEC zaczyna się 256 B *przed* blokiem,
a nic nie mówi sprzętowi, żeby te bajty pominął. Wcześniejsze raporty uznawały „co
silikon robi z resztą" za nierozstrzygalne; decydujące jest to, że **reszta nigdy do
silikonu nie dociera**.

## 4. Jak to ucegliło aparat

Pakiet 3.25 różnił się od działającego 3.23 w dokładnie jednej rzeczy, którą Loader3
czyta: `nflasha3`, przebudowanym ich własnym enkoderem.

| Defekt | Skala | Skutek |
|---|---|---|
| Builder wyrównywał do **256 B** | **359 z 369 bloków** z resztą 256 | 256 B poprzedniego bloku wchodzi do strumienia LDEC |
| Bloki 0, 48, 57 jako **jeden rekord 64 KiB** (73 732 B) | 3 bloki | LDEC programowany na 16 × 4096; przekroczona cota 65 800 B |
| Wypełnienie `0xFF` | 4 bloki | nie tak, jak robi Sony |
| Bloki po **129 sektorów** (> 128) w pierwszej wersji 3.25c | 3 bloki | ARM7 dzieli odczyt na dwie tury — ścieżka, którą Linux używa w `nflasha15/16`, a Loader3 nigdy |

Do tego każda normalna ścieżka bootu trafia na wadliwy blok: blok 0 to sektor startowy
FAT, blok 240 to pierwszy wpis RAMCFG (`\sabin`), `idt_cam.bin` 4/4 bloki, `sa_dfdet.bin`
4/4, `av-cam.bin` 166/176, `initrd.img` 63/63, `vmlinux.bin` 55/55.

## 5. Dlaczego testy offline to przepuściły

- Dekodery programowe (`fwtool`, ich własny `tpzl.py`) **sklejają rekordy** i ignorują
  wyrównanie oraz geometrię rekordów — obraz „dekompresował się poprawnie".
- Builder weryfikował wynik **własnym dekoderem** (sprawdzenie cykliczne).
- Żaden weryfikator nie modelował `Loader3 → ARM7 → LDEC`. Dopiero emulacja z prawdziwym
  kodem Loader3 i ARM7 oraz zamodelowanym LDEC odtworzyła awarię: **361/369 bloków**
  (Sony i obraz poprawiony: 0).

## 6. Jak wygląda poprawny obraz

Korpus: **16 obrazów TPZL Sony** (A6000 3.21, α7S 3.20, α6300 2.01, zrzuty z samego
aparatu) = **19 489 bloków, 311 824 rekordów**: każdy blok to 16 × 4096 B, każdy offset
ma resztę 0 — sprawdzone dwoma niezależnymi parserami. Rekordów „stored" Sony używa
4 556 razy w `nflasha15`, gdzie 162 bloki składają się wyłącznie z nich (129 sektorów)
i Linux czyta je przy każdym boocie.

## 7. Bezpieczny sposób zmiany partycji

Z ich `scripts/e25_27/tpzl.py` (wersja poprawiona):

1. Wyrównanie do 512.
2. Zmieniać jak najmniej stron 4096 B; w każdym zmienionym bloku zachować **oryginalne
   skompresowane rekordy Sony** dla stron nietkniętych, a zmienioną stronę wydać jako
   jeden rekord „stored" (`_splice`).
3. Wypełnienie `0x00`; każdy blok ≤ 126 sektorów.
4. Przeliczyć CRC32 i rozmiar w `part_image.sum`.
5. Zablokować build na kontroli `hardware_violations()` (reszta ≠ 0, rekordy ≠ 16 × 4096,
   cota rozmiaru, cota sektorów) i odmówić wydania obrazu, który jej nie przechodzi.

Wynik w ich przypadku: 369/369 bloków czystych, 30/30 kontroli, emulacja 0/369 błędów,
obraz 11 493 888 B wobec 11 489 040 B Sony (partycja 30 MiB). Potem potwierdził to
sprzęt: firmware 3.27 (ta sama treść, inny numer) wystartował, a Loader3 załadował
`\sabin\idt_cam.bin` tam, gdzie 3.25 zwracał −302.

## 8. Ograniczenia

- **Potwierdzenie UART-em jest niemożliwe**: konsola Loader3 jest wyciszona przez
  `Backup[0x510015]=0`, więc `LD3_E`/`FAT_E`/`CFG_E` nie wychodzą z układu.
- Zachowanie LDEC przy reszcie uznano za nierozstrzygalne (R16/R17), a potem nieistotne
  (R36) — ale nikt nie zmierzył, co robi z **ostatnim** blokiem, gdy plik nie kończy się
  na granicy sektora.
- Poza aktualizacjami Sony nie istnieje żadna próbka TPZL, więc cała wiedza o formacie
  jest indukcyjna.
- Poprawny format nie sprawia, że payload działa: 3.25c/3.27 startują, ale ich patch
  migawki nadal nie ma efektu.

## 9. Co to znaczy dla tego repozytorium

[03](03-integralnosc.md) odpowiada „czy pakiet da się złożyć" — tak, bit w bit, dopóki nie
zmieniasz treści. Ta strona odpowiada „czy treść da się zmienić" — tak, w granicach z §2,
a kosztem złamania jednej z nich jest dokładnie ta cegła, którą opisuje
[11](11-odzysk-swd.md), gdzie jedyną drogą powrotu było lutowanie do SoC.

Raporty po kolei: [R15](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r15-tpzl-custom-fw325.md) (Loader3 przyjmuje resztę, tylko ostrzega),
[R16](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r16-ldec-hardware-audit.md) / [R17](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r17-arm7-ldec-segment-analysis.md) (LDEC i ARM7),
[R36](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r36-causa-fallo-325.md) (przyczyna, korpus),
[R39](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r39-estatico-profundo.md) (emulacja),
[R45](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r45-firmware-325c-experimental.md) (poprawiony builder, limit sektorów).
