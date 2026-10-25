# 05 — DFE: front-endowy MCU

`/usr/dfe/dfe.bin` to firmware układu **CXD90027GF** — tego, który czyta matrycę.
Jest mały, nieobfuskowany i — o ile ta praca ustaliła — nigdy wcześniej publicznie
nie analizowany.

## 1. Załadowanie do disassemblera

```
plik:   dfe/dfe.bin
rozmiar: 65 536 bajtów
sha256: fc4e314db24a72d584bd8795bd8f1144b003c97c390cb143d09b840b38bf9fcd
```

Surowy blob, bez nagłówka. Adres bazowy da się wyprowadzić z kodu:

```
00000000: 18 f0 9f e5    ← wektor 0: LDR PC,[PC,#0x18] → czyta (A+8)+0x18 = A+0x20
00000020: 70 58 00 01    ← wartość 0x01005870 = reset handler
```

Skoro literał leży pod offsetem 0x20 i wskazuje `0x01005870`, **offset 0 = `0x01000000`**.
Kolejne literały (`0x01005834`, `0x01005838`, `0x0100584C`) to potwierdzają.

Ładować jako **ARM little-endian v7** pod `0x01000000`. Analiza znajduje
**83 procedury** i **94 stringi**.

## 2. Co robi

| Funkcja | Rola |
|---|---|
| `dfe_entry` / `dfe_reset_handler` (`0x1005870`) | łańcuch wektora resetu |
| `dfe_apb_selftest` (`0x1000c8c`) | zapis/odczyt min i max adresu każdego bloku po APB, druk OK/NG |
| `dfe_irq_selftest` (`0x1000a94`) | przechodzi wszystkie linie przerwań (ZPD0/1, DFECAM0/1, SiMISC0/1, SSG0/1, DFELINK) |
| **`dfe_zpd_af_detect`** (`0x1001da4`) | **autofokus fazowy** |
| `dfe_zpd_init`, `dfe_zpd_scc_end`, `dfe_scc_mode_start` | sekwencje inicjalizacji ZPD |
| `dfe_print`, `dfe_puts_emit`, `dfe_flush` | wypis logów (patrz §4) |

Najmocniejsza identyfikacja to jeden string w handlerze ZPD:

```
"Hello Regulus: apl_zpd_af_det"
```

*Regulus* to kryptonim CXD90027; `zpd` to blok detekcji fazowej. A6000 ma 179 punktów
PDAF — to firmware, który je produkuje.

Duża część binarki to self-test, nie runtime: testy dostępu APB per blok, testy linii
przerwań i stringi `>>> ICache: Enable`, `>>> DCache: Enable`, `>>> Main...`,
`>>> Simulation Finished...`. Każda głębsza analiza musi najpierw oddzielić bring-up
od kodu roboczego.

## 3. Mapa rejestrów (odzyskana z literałów)

Sony zostawił nazwy bloków w stringach diagnostycznych; adresy bazowe pochodzą
z literal pools.

| Blok | Baza | Uwagi |
|---|---|---|
| **ZPD** (AF) | `0x01010000` | blok główny; status `+0xfc`, sterowanie `+0xf8`, `+0xe010`, `+0xe014`, `+0x88908` |
| ZPD_APB0 | `0x0109828C` … `0x01099F54` | granice testów APB |
| ZPD_APB1 | `0x0102B808` … `0x0102B9B0` | |
| **SSG** (timing) | `0x01080020` … `0x010800FC`, IRQ `0x01080100`/`0x0108010C` | timing matrycy |
| SiMISC | `0x01088200` … `0x0108853C`, IRQ `0x01088900`/`0x01089900` | |
| **DFECAM0** | `0x010A0108` … `0x010A781C`, IRQ `0x010A0010` | korekcja defektów |
| DFECAM1 | `0x010A800C` … `0x010A8B38`, IRQ `0x010A001C` | |
| DFECAM2 | `0x010B0000` … `0x010B5000` | |
| DFECAM3 | `0x010B8000` … `0x010BA000` | |
| DFECAM4 | `0x010C7000` … `0x010C8000` | |
| DFECAM5 | `0x010CF000` … `0x010F0050` | |
| **DFELINK** (do SoC) | `0x010F0000`, `0x010F11C4` | łącze z hostem |
| nieprzypisane | `0x01011000`, `0x01012000`, `0x01013000`, `0x0101D000`, `0x0101E000`, `0x01020000`, `0x01022000`, `0x01026000`, `0x01029000`, `0x0102D000` | `0x0102D000` to bufor logów, patrz §4 |

Adresy pochodzą z literal pools; **nie były weryfikowane na żywym układzie**.
Nazwy bloków pochodzą z tekstów diagnostycznych Sony.

## 4. Kanał logów to RAM, nie UART

Łańcuch wywołań:

```
dfe_print (0x1006070)
  ├─ dfe_lock
  ├─ dfe_critical_enter
  ├─ dfe_puts_emit(arg)        ← wypisuje string bajt po bajcie
  ├─ dfe_puts_emit(terminator)
  ├─ dfe_flush                 ← zeruje licznik
  └─ dfe_critical_exit
```

`dfe_puts_emit` pisze każdy znak przez wskaźnik z literału:

| Literał | Wartość | Znaczenie |
|---|---|---|
| `0x01005ce4` | **`0x0102D000`** | **wskaźnik bufora wyjściowego** |
| `0x01005ce0` | `0x0100639C` | licznik/flag zerowany przez `dfe_flush` |

W obrazie nie ma żadnego adresu przypominającego rejestr UART. **Diagnostyka DFE jest
zapisywana do bufora RAM pod `0x0102D000`**, który musi być czytelny z zewnątrz —
najprawdopodobniej przez DFELINK albo jako okno w pamięć DFE. Domknięcie tego obiegu
to otwarta pozycja.

## 5. Firmware jest dostarczany dwa razy

`dfe.bin` istnieje jako osobny plik **oraz** bit w bit wewnątrz `av-cam.bin` pod
offsetem **`0xA67F00`** (poprzedzony zerowym wypełnieniem, wyrównanie do 0x100).

Którą kopię SoC faktycznie wgrywa — **nie ustalono**. `av-cam.bin` to kod PIC bez
literału wskazującego ścieżkę, a limit startowy Ghidry (330 s) nie wystarczył na moduł
11 MB. To ma znaczenie: jeśli liczy się kopia wbudowana, podmiana
`/usr/dfe/dfe.bin` nic nie zmieni.

## 6. Nazwy symboli

Wszystkie 83 procedury są nazwane w `data/dfe-names.txt`; `tools/apply-dfe-names.py`
odtwarza nazwy w świeżym projekcie Ghidry. Dwa przebiegi:

1. **Ręcznie (15)** — z dekompilacji: `dfe_print`, `dfe_puts_emit`, `dfe_flush`,
   `dfe_lock`, `dfe_critical_enter/exit`, `dfe_irq_selftest`, `dfe_irq_probe`,
   `dfe_apb_selftest`, `dfe_zpd_af_detect`, `dfe_zpd_init`, `dfe_zpd_scc_end`,
   `dfe_scc_mode_start`, `dfe_entry`, `dfe_reset_handler`.
2. **Heurystycznie (68)** — każde odwołanie `DAT_xxxxxxxx` w dekompilowanym ciele jest
   rozwiązywane względem mapy rejestrów; funkcja dziedziczy nazwę bloku, którego dotyka
   (`dfe_zpd_apb0_NN`, `dfe_ssg_NN`, `dfe_defcamN_NN`, `dfe_dflink_NN`,
   `dfe_logbuf_NN`), w przeciwnym razie `dfe_util_NN`.

Wynik: ~43 funkcje przypisane do peryferiów, 33 generyczne helpery. Największe grupy to
`zpd_apb0` (14) i `zpd_apb1` (10) — większość kodu obsługuje blok AF, co pasuje do
profilu DFE.

## 7. Dlaczego to ważne

DFE odpowiada za **odczyt matrycy**: `SSG` (timing) i `DFECAM0–5` (korekcja defektów).
Jeśli ten aparat ma gdzieś nieużywane tryby sensora — binning, line-skipping, inne okna
odczytu — to właśnie tutaj, a nie w `av-cam.bin` ani w `sabin/`.

Plik jest też wyjątkowo przystępny: 64 KiB, czysty ARM, bez kompresji, prosty model
przerwań.
