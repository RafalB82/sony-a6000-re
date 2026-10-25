# 13 — `dfe.bin` w Ghidrze: pierwsza analiza firmware DFE

Cel: wrzucić firmware układu DFE (CXD90027 „Regulus") z A6000 do Ghidry i zobaczyć,
co ten procesor w ogóle robi.

**Wynik: `dfe.bin` to firmware rdzenia ARM sterującego odczytem matrycy — w tym
**detekcją fazową AF (ZPD)**, korekcją defektów (DFECAM) i generatorem timingów (SSG).

---

## 1. Jak załadować

Plik: `fw-3.21/fw/firmware.tar_unpacked/0700_part_image/dev/nflasha15_unpacked_unpacked/dfe/dfe.bin`
Rozmiar: **65 536 B**, SHA256 `fc4e314db24a72d584bd8795bd8f1144b003c97c390cb143d09b840b38bf9fcd`.

To surowy blob bez nagłówka — trzeba podać architekturę i adres bazowy.
**Adres bazowy da się wyprowadzić z kodu** (nie trzeba zgadywać):

```
00000000: 18 f0 9f e5   ← wektor 0: LDR PC,[PC,#0x18]  → czyta spod (A+8)+0x18 = A+0x20
...
00000020: 70 58 00 01   ← wartość 0x01005870 = adres reset handlera
```

Skoro literał wskazuje `0x01005870`, a leży pod offsetem 0x20, to **offset 0 = 0x01000000**.
Dalsze literały (`0x01005834`, `0x01005838`, `0x0100584C`, `0x01005850`) potwierdzają.

```bash
# REA (Ghidra 12.1.4, ARM:LE:32:v7)
open_binary(path=".../dfe/dfe.bin", format="raw-binary",
            architecture="arm", entry_point="0x01000000")
```

Snapshot analizy: `analysis/dfe-a6000.rea.json` (16 rekordów Evidence).

---

## 2. Co analiza znalazła

| metryka | wartość |
|---|---|
| segment | 1 (`ram`), `0x01000000`–`0x01010000` (64 KiB) |
| procedury | **83** |
| stringi | **94** |
| architektura | ARM little-endian v7 (Ghidra default) |

Entry `0x01000000` → thunk → **`0x01005870`** (reset handler) → skacze przez wskaźnik
z `0x01005a3c`.

---

## 3. Mapa rejestrów (MMIO) — wyprowadzona z literałów

Skan pliku pod kątem słów w zakresie `0x01010000`–`0x02000000` dał spójny zestaw
wskaźników na bloki peryferyjne. Powiązane z nazwami bloków z testów APB:

| blok (z nazw stringów) | adres bazowy | skąd wiemy |
|---|---|---|
| **ZPD** (AF fazowy) — główny blok | `0x01010000` | `DAT_01001fc0`, 6 referencji |
| ZPD_APB0 | `0x0109828C` … `0x01099F54` | test APB „Min/Max addr" |
| ZPD_APB1 | `0x0102B808` … `0x0102B9B0` | j.w. |
| SSG (timing generator) | `0x01080020` … `0x010800FC` — **IRQ: `0x01080100`, `0x0108010C`** | j.w. |
| SiMISC | `0x01088200` … `0x0108853C` — **IRQ: `0x01088900`, `0x01089900`** | j.w. |
| DFECAM0 | `0x010A0108` … `0x010A781C` — **IRQ: `0x010A0010`** | j.w. |
| DFECAM1 | `0x010A800C` … `0x010A8B38` — **IRQ: `0x010A001C`** | j.w. |
| DFECAM2 | `0x010B0000` … `0x010B5000` | j.w. |
| DFECAM3 | `0x010B8000` … `0x010BA000` | j.w. |
| DFECAM4 | `0x010C7000` … `0x010C8000` | j.w. |
| DFECAM5 | `0x010CF000` … `0x010F0050` | j.w. |
| **DFELINK** (łącze do BIONZ) | `0x010F11C4`, status `0x010F0000` | j.w. |
| dodatkowe bloki | `0x01011000`, `0x01012000`, `0x01013000`, `0x0101D000`, `0x0101E000`, `0x01020000`, `0x01022000`, `0x01026000`, `0x01029000`, `0x0102D000` | nieprzypisane |

To pierwsza publiczna mapa tego układu. Uwaga: zakresy „Min/Max addr" to *testy*
dostępu do APB (zapis/odczyt skrajnych adresów), więc granice bloków są przybliżone.

---

## 4. Co ten procesor robi — z dekompilacji

### 4.1. `FUN_01000c8c` — Power-On Self Test magistrali APB

```
FUN_01006070("CPU APB ACCESS Sequence Start");
... dla każdego bloku: zapisz 0xFF / 0x00 pod Min addr i Max addr, odczytaj, porównaj
    → "CPU APB ACCESS OK"  albo  "\nCPU APB ACCESS NG!!!!!"
```

Czyli firmware **weryfikuje po kolei wszystkie bloki peryferyjne**. To wyjaśnia,
skąd tyle stringów `CPU APB : <BLOK> Value write (Min/Max addr)`.

### 4.2. `FUN_01000a94` — test linii przerwań

```
FUN_01006070("CPU IRQ Sequence Start");
  "CPU IRQ : ZPD0"     → FUN_01000a28(0x01098900)
  "CPU IRQ : ZPD1"     → FUN_01000a28(0x0102BC00)
  "CPU IRQ : DFECAM0"  → FUN_01000a28(0x010A0010)
  "CPU IRQ : DFECAM1"  → FUN_01000a28(0x010A001C)
  "CPU IRQ : SiMISC0/1"→ FUN_01000a28(0x01088900 / 0x01089900)
  "CPU IRQ : SSG0/1"   → FUN_01000a28(0x01080100 / 0x0108010C)
  "CPU IRQ : DFELINK"  → ...
  "Before IRQ Enable 0/not 0", „After IRQ Enable 0/not 0"
```

### 4.3. `FUN_01001da4` — **ZPD = detekcja fazowa AF**

```
FUN_01006070("Hello Regulus: apl_zpd_af_det");
status = *(u32*)(ZPD_BASE + 0xfc);
if (status & 0x100000) { ... }            // ścieżka „AF detect"
else { FUN_01006070("zpd_init"); ... }
...
"ZPD_START:ON" / "ZPD_START:OFF"
programuje: +0xf8, +0xe010, +0xe014, +0x88908, +0x88008, +0x100
```

Nazwa `apl_zpd_af_det` nie pozostawia wątpliwości: **ZPD to blok detekcji fazowej
autofokusu** (A6000 ma 179 punktów PDAF). „Hello Regulus" potwierdza układ.

### 4.4. `FUN_0100294c` — sekwencja „SCC"

```
"zpd_scc_end1." → czekaj aż (reg+0xc00 & 0x20) != 0
"zpd_scc_end.2" → FUN_0100288c(0x20)
"zpd_scc_end.3" → FUN_01002898(0,1)
"zpd_scc_end.4"
```

### 4.5. Reszta stringów

- `CPU AIF : ZPD W-ch0 Start/Done`, `R-ch1`, `W-ch2`, `R-ch2` — kanały DMA/pamięci AF.
- `>>> ICache: Enable`, `>>> DCache: Enable`, `>>> Main...`, **`>>> Simulation Finished...`**
  — to ślady **harnessu testowego/symulacyjnego**. Ciekawe: build zawiera kod
  diagnostyczny, który w produkcji może być nieaktywny (do sprawdzenia xrefami).

---

## 5. Wnioski

1. **DFE to nie jest „głupi front-end".** Ma własny rdzeń ARM, własny firmware i realną
   logikę: detekcja fazowa AF, korekcja defektów na 6 kanałach, generator timingów,
   łącze DFELINK do BIONZ.
2. **`dfe.bin` jest tu, gdzie trzeba, jeśli szukać trybów odczytu matrycy.** Blok
   **SSG** (timing generator) i **DFECAM0..5** sterują fizycznym odczytem — to tam
   warto szukać nieużywanych rozdzielczości/binningu.
3. **Duża część pliku to self-test**, nie praca. Przy dalszej analizie trzeba najpierw
   oddzielić kod testowy (APB/IRQ sekwencje) od runtime'u (ZPD init/start, SCC).
4. **Nikt tego wcześniej nie opisał** — brak jakichkolwiek publicznych wzmianek
   o `dfe.bin` poza `hardware.rst`.

---

## 6. Co dalej (konkretne kroki w Ghidrze)

1. **Nazwać procedury** na podstawie stringów (łatwe, bo każda funkcja testowa
   zaczyna się od `FUN_01006070("...")`) — skryptem po xrefach.
2. **Rozłożyć `FUN_01006070`** (0x01006070) — to funkcja wypisująca; ustalić, gdzie
   pisze (UART? bufor w RAM sprawdzany przez DFELINK?) — to wskaże kanał logów.
3. **Znaleźć tabelę trybów SSG** — szukać tablic `u32` w okolicy `FUN_010031a4`,
   `FUN_01003218`, `FUN_010032c8`.
4. **Porównać z DFE z RX10M2** (ten sam CXD90027) — różnice powinny wskazać,
   co jest per-matryca, a co wspólne.
5. **Sprawdzić, czy `>>> Simulation Finished` jest osiągalne** (xref) — jeśli tak,
   jest w firmware furtka testowa.

---

## 7. Ograniczenia tej analizy

- Ghidra załadowała plik jako `ARM:LE:32:v7` z auto-analizą domyślną — część funkcji
  może być nieodkryta (83 procedury na 64 KiB to sensowna, ale nie pełna liczba).
- Dekompilator zgłasza `bad instruction data` w kilku miejscach — typowe dla surowego
  ARM-a z przeplotem danych; nie wpływa na wnioski z §4.
- Adresy MMIO pochodzą z literałów; **nie były weryfikowane na sprzęcie**.
- Nazwy bloków (ZPD/SSG/DFECAM/SiMISC) pochodzą z tekstów diagnostycznych Sony,
  nie z dokumentacji.

---

## 8. Kanał logów: bufor w RAM, nie UART

Rozłożone po kolei:

```
dfe_print(0x01006070)          → wrapper
  ├─ dfe_lock (0x01005a6c)
  ├─ dfe_critical_enter (0x0100581c)     ← zapisuje stan, wyłącza przerwania
  ├─ dfe_puts_emit (0x01005a94, arg)     ← wypisuje string ZNAK PO ZNAKU
  ├─ dfe_puts_emit (0x01005a94, &LAB_010060d8)   ← dopisuje stały terminator
  ├─ dfe_flush (0x01005ae8)              ← zeruje licznik
  └─ dfe_critical_exit (0x0100582c)
```

`dfe_puts_emit` robi w pętli `*puVar1 = bajt;` gdzie `puVar1 = DAT_01005ce4`.
Wartości literalne:

| adres literału | wartość | znaczenie |
|---|---|---|
| `0x01005ce4` | **`0x0102D000`** | **wskaźnik bufora wyjściowego** |
| `0x01005ce0` | `0x0100639C` | licznik/flag (zerowany przez `dfe_flush`) |

**Wniosek: logi nie idą na żaden UART — firmware pisze tekst do bufora w RAM
pod `0x0102D000`, czyli poza obrazem 64 KiB.** To wewnętrzna pamięć DFE.
Nie ma w obrazie żadnego adresu przypominającego rejestr UART.

**Dlaczego to ważne:** ten bufor musi być czytelny z zewnątrz — najprawdopodobniej
przez **DFELINK** (`0x010F0000`) albo jako okno pamięci widziane przez BIONZ.
To pierwszy trop do „jak wyciągnąć diagnostykę z DFE bez rozbierania aparatu".

## 9. Nazwy procedur — 83/83

Nazwy nadane w Ghidrze: `analysis/dfe-names.txt` + skrypt `analysis/apply-dfe-names.py`
(Ghidra/Jython; skrypt odtwarza nazwy po ponownym imporcie, bo snapshotu nie da się
zapisać po edycji metadanych).

Metoda:
1. **Ręcznie** — 15 funkcji kluczowych, na podstawie dekompilacji
   (`dfe_entry`, `dfe_reset_handler`, `dfe_print`, `dfe_puts_emit`, `dfe_flush`,
   `dfe_lock`, `dfe_critical_enter/exit`, `dfe_irq_selftest`, `dfe_irq_probe`,
   `dfe_apb_selftest`, `dfe_zpd_af_detect`, `dfe_zpd_init`, `dfe_zpd_scc_end`,
   `dfe_scc_mode_start`).
2. **Automatycznie** — dla pozostałych: z pseudokodu wyciągane są odwołania
   `DAT_xxxxxxxx` (literały), a wartość każdego literału jest porównywana ze znanymi
   bazami peryferyjnych bloków (61 wpisów mapy z §3). Funkcja dziedziczy nazwę
   bloku, którego dotyka: `dfe_zpd_apb0_NN`, `dfe_zpd_apb1_NN`, `dfe_ssg_NN`,
   `dfe_defcamN_NN`, `dfe_dflink_NN`, `dfe_logbuf_NN`. Bez trafienia → `dfe_util_NN`.

Rozkład: **~43 funkcje** przypisane do peryferiów, **33** bez wyraźnego bloku
(helpery, obsługa stosu, inicjalizacja cache).
Dominują `zpd_apb0` (14) i `zpd_apb1` (10) — czyli **większość kodu obsługuje
blok AF**, co pasuje do profilu DFE.

## 10. Korekta: A6300 **ma** firmware front-endu — tylko schowany

Wcześniejszy wniosek z `12_DFE.md` („A6300 nie ma `dfe.bin`") był niepełny.
Sprawdzenie bajtowe:

| co | A6000 | A6300 |
|---|---|---|
| `dfe.bin` jako osobny plik `/usr/dfe/dfe.bin` | ✅ 65 536 B | ❌ |
| **kopia `dfe.bin` wewnątrz `av-cam.bin`** | ✅ **@ `0xA67F00`**, **bit w bit** | ❌ (inny blob) |
| własny blob front-endu w `av-cam.bin` | — | ✅ **@ `0xC1EB00`** |

Blob A6300 to **inna, nowsza wersja**: wektory wskazują na `0x0100C000`,
w stringach jest `"ICACHE,DCACHE and MMU Enable"` (u A6000: `">>> ICache: Enable"`),
ale zestaw diagnostyki ten sam (`SiMISC`, `ZPD`, `DEFCAM`, `DFELINK`).

**Poprawiony wniosek:** A6300 ma front-end i jego firmware, tylko (a) nie jako
osobny plik, (b) w nowszej wersji z MMU, (c) ładowany innym interfejsem
(`DfeCamAif`, `DFE Acquire`). Czyli różnica A6000↔A6300 to **generacja front-endu**,
a nie „jest / nie ma".

**Konsekwencja dla tezy o 4K:** nadal stoi — A6300 ma dodatkowo `/usr/beaune/`
(kodek CXD4236) i `beaune_drv.ko`, czego A6000 nie ma. Ale „brak DFE" nie jest
żadnym z elementów tej różnicy.
