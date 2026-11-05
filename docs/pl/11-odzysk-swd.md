# 11 — SWD: port debugowania i odzysk uceglonego A6000

A6000 ma żywy port debugowania ARM CoreSight, którego nic w łańcuchu startowym Sony
nie blokuje. W listopadzie 2026 użyto go do odzyskania aparatu uceglonego
zmodyfikowanym firmware: wymuszono `r0` na jednej instrukcji podczas bootu,
wystartował fabryczny updater, a firmware Sony zainstalował się przez USB.
**Do NAND nie zapisano nic.**

> **Źródło i status.** Wszystko poniżej jest z drugiej ręki — z raportów
> [`nicolvus/a6000-fw-decomp`](https://github.com/nicolvus/a6000-fw-decomp)
> (E26-R40, R46, R47, R48, R49, R51; 31-10 … 03-11-2026). Ich etykiety dowodu
> (`MEDIDO` = zmierzone, `LEÍDO` = odczytane z binarki, `INFERENCIA` = wywnioskowane,
> `NO VERIFICADO` = niezweryfikowane) są zachowane. **Nic z tego nie zostało przez nas
> sprawdzone na sprzęcie.** Adresy dotyczą Loader3 z 3.21/3.26 i przesuwają się razem
> z bootloaderem.

## 1. Port istnieje, na dwóch padach 0402

| Element | Wartość | Pochodzenie |
|---|---|---|
| Cel | SoC `IC6000` = CXD90014 (BIONZ X), kulki **W25 = SWCLK**, **W26 = SWDIO** | schemat z service manuala |
| Droga do złącza serwisowego | `R4911` / `R4912` → `CN4906` piny 11/12 | schemat |
| Montaż | `R4911`, `R4912`, `R4915`, `R4916` i `CN4906` **nie są zamontowane** (same pady) | schemat oznacza `XX`, potwierdzone wzrokowo |
| Klasyczny JTAG | TDI/TCK/TMS podciągnięte do `D_3.15V_MSS` → bezużyteczny | schemat |
| `FUSE_EN` (T12) | też podciągnięty do 3,15 V; eFuse blokującego debug nigdy nie zaobserwowano | schemat |
| Alternatywny reset | `NTRST` = `XRESET_CR` (kulka H26) | schemat |
| Napięcie linii, aparat włączony | 3,09 V na obu padach (logika 3,15 V) | zmierzone |

Użyta droga: drut 0,1–0,2 mm przylutowany **bezpośrednio do padu `R4911`/`R4912` od
strony BIONZ**, plus masa. Bez rezystorów 0 Ω i bez `CN4906`. To nieodwracalna praca
na płycie; alternatywa (wlutować 0 Ω i użyć `CN4906`) wymaga więcej lutowania na
drobniejszych padach.

## 2. Co odpowiada na magistrali

```
DPIDR   0x3ba02477
AP0     IDR 0x44770001  AHB-AP   CSW=0x02800062   pamięć fizyczna
AP1     IDR 0x24770002  APB-AP   CSW=0x80000042   CoreSight, BASE=0x80000000
AP2     IDR 0x14760010  JTAG-AP
AP3–AP5 puste
```

- Tablica ROM `0x80000000` → zagnieżdżona `0x80100000` → **cztery Cortex-A5**
  (`part 0xc05`), bazy debugowania `0x80110000/12000/14000/16000`, każdy z PMU/CTI/ETM.
  Cała praca odbyła się na rdzeniu 0.
- **Brak blokady odczytu.** AP0 i AP1 odpowiadają; eFuse blokujące odczyt debugowania
  odpada. Zapis przez DAP nie był testowany poza `halt` i `set_reg` rejestrów CPU.
- Dwa sposoby czytania pamięci: przez AP0 (`TAR` = `0x04`, `DRW` = `0x0c`, słowa
  32-bit) albo przez rdzeń (`target create … cortex_a -ap-num 1 -dbgbase 0x80110000`,
  `read_memory` — respektuje MMU i cache).

To niezależnie potwierdza to, co mówi nasz [01-sprzet.md](01-sprzet.md) na podstawie
service manuala: CXD90014 to 4× Cortex-A5.

## 3. Halt bez obiektu target

Używane, żeby zatrzymać CPU zanim łańcuch startowy dobiegnie końca:

```tcl
apreg 1 0x04 0x80110fb0 ; apreg 1 0x0c 0xc5acce55   ; DBGLAR   = unlock
apreg 1 0x04 0x80110300 ; apreg 1 0x0c 0            ; DBGOSLAR = 0
apreg 1 0x04 0x80110090 ; apreg 1 0x0c 1            ; DBGDRCR  = halt request
```

To standardowa sekwencja zewnętrznego debugowania Cortex-A. Zapisuje wyłącznie
rejestry debugowania CPU — nie pamięć aplikacji ani NAND.

## 4. Przejęcie kontroli nad bootem

Cały łańcuch (BootROM → Loader2 → Loader3) trwa poniżej sekundy, więc technika jest
taka: halt jak najwcześniej, potem łańcuch breakpointów — jeden na wejściu Loader3
(`0xc01f0000`), a przy każdym trafieniu usuń wszystkie, zrób `step`, uzbrój następne,
wznów.

Cztery pułapki, z których każda kosztowała sesję:

1. **Breakpointy założone w Loader2 nie przeżywają do Loader3.** Opublikowano raport
   oparty na takim breakpoincie („nie odpalił"), który trzeba było wycofać.
2. **Bez `step` breakpoint odpala na sobie dziesiątki razy.** Jeden przebieg
   zanotował „39 trafień", które nie były 39 wywołaniami.
3. **Generyczne aliasy `sp`/`lr` czytają 0 dla rejestrów bankowanych.** Trzeba
   jawnie `sp_svc`/`lr_svc`; raz generyczne aliasy pokazały zdrowy stos jako
   `mov pc,lr` do NULL.
4. **„Startuje dwa razy" było nieprawdą.** Po włożeniu baterii przy wyłączonym
   switchu aparat wykonuje Loader2/Loader3 przez ~0,87 s i sam się wyłącza
   (`XPWR_OFF`, `b .` pod `c01f5e50`, gałąź BootMode 7/8/9/13/14). Przekręcenie
   switcha to **jeden** ciągły boot (~2,7 s) kończący się w pętli LED (BootMode 11).
   Skrypt czekający na „drugi boot" po prostu się przedawnił i nic nie zmienił.

## 5. Skąd bierze się −302, zmierzone

Kod błędu LED liczy się w `c01f3b74` jako `r4 = -kod`, `LDR2 = r4/1000`,
`LNG = (r4%1000)/100`, `SHT = r4%100`. Rejestry dały `0/3/2` → **−302**, zgodnie
z miganiem 3 długie + 2 krótkie.

Przy breakpointach na właściwym (switchowym) boocie:

| Punkt | Wartość |
|---|---|
| Wejście P2, `0xc01f2f24` (`CFG_E:Load file`) | `r0 = 0xc005c000` — wpis 0 tabeli CFG |
| Powrót z P2 | **`r0 = 0xfffffed2` (−302)** |
| Rutyna LED `c01f3b74` | ten sam −302, `lr = 0xc01f1269` |

Tabela CFG leży pod `0xc005c000`, krok `0x90`, maska trybu na `+0xc`:

| Plik | Cel | Partycja |
|---|---|---|
| `\sabin\idt_cam.bin` | `0x83501000–0x83540fff` | 3 |
| `\sabin\sa_dfdet.bin` | `0x96800000–0x9682ffff` | 3 |
| `\av-cam.bin` | `0x83541000–0x84140fff` | 3 |
| `\kemco.txt` | `0x80033000–0x80033fff` | 2 |
| `\initrd.img` | `0x80628000–0x80e27fff` | 3 |

Pierwszy plik z partycji 3 nie daje się odczytać i loader zatrzymuje się tam — czyli
`nflasha3` naprawdę jest nieczytelna, a hipoteza o formacie z ich R36 potwierdza się
pomiarem.

## 6. Iniekcja: sprawić, żeby `\updater\mode` „istniał", nic nie zapisując

`chk updater` pod `0xc01f15c0` woła `c01f44c6("\updater\mode")`, a potem robi
`cmp r0,#0` / `bge`. Jeśli `r0 >= 0` (plik istnieje), Loader3 wybiera **BootMode 3**
i ładuje fabryczny updater z `nflasha1`, którego żaden update nie nadpisuje.

Wymuszenie `r0 = 0` na tej jednej instrukcji jest więc równoważne istnieniu pliku:

```
BP_HIT k=0 pc=0xc01f0000                    wejście Loader3
BP_HIT k=1 pc=0xc01f15c0 -> r0 wymuszone 0   chk updater
BP_HIT k=2 pc=0xc01f1e16                    wybrany BootMode 3
BP_HIT k=3 pc=0xc01f15c0 -> r0 wymuszone 0   drugie wywołanie
BP_HIT k=4 pc=0xc01f1378                    wejście do updatera
```

Od wejścia Loader3 do wejścia updatera: **696 ms**. `chk updater` ma 8 miejsc
wywołania; skrypt wymusza we wszystkich i po każdym zapisie odczytuje `r0` z powrotem,
żeby udowodnić, że `set_reg` zadziałał. Skrypt Tcl:
[`analysis/e26-recovery/r48_updater_swd.cfg`](https://github.com/nicolvus/a6000-fw-decomp/blob/main/analysis/e26-recovery/r48_updater_swd.cfg).

Dlaczego nie zapisali po prostu NAND: **Loader3 nie umie pisać bloków.** W
`muminblk_request` (`c01fd5a4`) odczyt woła `muminblk_transfer`, a zapis skacze na
`c01fd66a` i zwraca sukces **nic nie przenosząc** (literał w trace to `"write"`
zamiast `"read"`). Funkcje zapisu MuMin są w RAM, ale warstwa blokowa ich nie używa.
Dlatego odpadły obie opcje — „utwórz plik ręcznie" i „przegraj `nflasha3` po SWD":
brak mechanizmu, nie tylko ryzyko.

## 7. Przebieg odzysku

- Aparat w trybie updatera: `054c:03e2`; `pmca-console firmware -f` z pakietem 3.26
  (oficjalna treść 3.24 z podniesionym numerem — legalnie, bo guard sprawdza tylko
  CRC32, typ LSI i wersję; patrz [03-integralnosc.md](03-integralnosc.md)).
- **Pierwsza próba zatrzymała się na 45 % z `Response error: 0x1063`.** Rozszyfrowane
  ich metodą: `ErrorConverter::Convert` w `sauu` (`0xe9b0`) zwraca kod LED z
  `| 0x1000`, więc `0x1063` = LED **`0x63`** = „Darwin nie odpowiedział po SIO /
  nie osiągnął stanu 5". Potem kanał protokołu odpowiadał `0x1063` na wszystko, ale
  kernel Linux updatera nie wisiał (bankowane `sp_svc`/`lr_svc` zdrowe), a wersja
  nadal była 3.25 (`CompleteUpdate` nie doszedł do skutku).
- Po power cycle aparat **sam** wrócił do trybu updatera, bo `StartUpdate` zdążył
  utworzyć `\updater\mode`.
- **Druga próba: 100 %, `Done`.** `pmca info` → firmware 3.26, normalny Mass Storage.
  Przyczyna `0x63` nigdy nie wyjaśniona; jedyna hipoteza to zakłócenie od sondy na
  liniach Darwina.

## 8. Co jeszcze dał port

- **Klucz BootROM z `nflasha0`**: BootROM kopiuje blok 0 do SRAM przy każdym starcie;
  pod `0xc0000600` jest `EXBL` plus wskaźniki do `Loader2.bin` (`0xc01f0000`)
  i `DiagUni.bin` (`0xc0038000`), a pod `0xc0001200` klucz **`0x5bc022a5`**, po nim
  `0xa8840468` = `~crc32(klucz)` — CRC-32 pierwszych 8 B to `0xffffffff`, czyli
  format poprawny. Odczyt przez `mem_ap` **z włączonym aparatem, bez halt**.
- Pełny backup NVRAM na 3.26 (852 647 B, BK4) i pakiet rollback 3.28.
- Znalezisko poboczne: włączenie adb na 3.27 trafia na `LDEC ERR -10003` na stronie
  `0x02c3` z `nflasha0p17` (`/android/data`) → `NULL pointer dereference at 0x6`
  → `WARMBOOT`. Uszkodzona strona w partycji danych, nie wina patcha.

## 9. Ograniczenia i to, co się nie zgadza

- **Zapis przez DAP nietestowany.** Zatrzymywali CPU i zmieniali rejestry; nigdy nie
  załadowali kodu do RAM. Defconfigi Sony `cxd90014_ice_*` istnieją właśnie po to,
  żeby załadować kernel z debuggera — to ominęłoby cały łańcuch Loader3. Nikt nie
  próbował.
- **`0x1063` (NG Darwina) niewyjaśnione.** Nie badali, bo ponowna próba się udała.
- **Sonda wciąż wlutowana** (stan na ich ostatni raport).
- **Sprzeczność w ich własnej dokumentacji:** R48 §8 twierdzi, że aparat wszedł do
  updatera „inną drogą" i że P1 nigdy nie wykonano, a R49 §7.2 pokazuje udaną
  iniekcję i nazywa ją „drogą, która zadziałała"; `PENDIENTES.md` cytuje obie wersje.
  *Mechanizm* jest udowodniony logiem rejestrów (wybrany BootMode 3, wejście
  `c01f1378`), ale z raportów nie da się odtworzyć, która próba faktycznie go użyła.
- **Nie zweryfikowane przez nich:** `CTRL/STAT` portu debugowania, dostępność padów
  `CN4906`, czy eFuse blokuje *zapis* przez port, oraz jakikolwiek zewnętrzny zrzut
  NAND.

## 10. Dlaczego to ważne dla tego repozytorium

- To jedyna udokumentowana droga powrotu z uszkodzonego `nflasha3`, a opiera się
  dokładnie na tym, co ustaliliśmy w [03-integralnosc.md](03-integralnosc.md):
  brak podpisów, tylko CRC32 i guard wersji.
- Potwierdza z krzemu to, co mieliśmy z service manuala (4× Cortex-A5).
- Dodaje adresy, których nie mieliśmy: baza Loader3 `0xc01f0000` (88 064 B,
  identyczny w `bootloader.bin` pod `0x22800`), `chk updater`, tabela CFG, rutyna
  kodu LED.
- Ustala też realny koszt eksperymentów: droga powrotu to **lutowanie do SoC**, nie
  sztuczka przez USB. Każdy plan modyfikujący `nflasha3` powinien to zakładać.

Ich raporty po kolei: [R40](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r40-jtag-swd-bionz.md) (statyczny wywód za SWD),
[R46](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r46-procedimiento-fisico-swd.md) (procedura),
[R47](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r47-primer-contacto-swd-lectura-ram.md) (pierwszy kontakt, zrzut RAM, −302 zmierzone),
[R48](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r48-plan-recuperacion-actualizador-swd.md) (plan iniekcji),
[R49](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r49-cierre-recuperacion-326.md) (zamknięcie),
[R51](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e26-r51-respaldo-clave-nflasha0-nvram-326.md) (klucz, NVRAM).
Czytelna wersja narracyjna: ich [wiki, strona 15](https://github.com/nicolvus/a6000-fw-decomp/wiki/15-Recuperacion-SWD-experimental).
