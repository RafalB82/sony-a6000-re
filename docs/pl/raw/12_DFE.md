# 12 — DFE (Digital Front End): co mówi internet i co mówi firmware

Pytanie: co to jest DFE w aparatach Sony, jaki układ, i dlaczego A6000 ma `dfe/dfe.bin`,
a A6300 nie. Poniżej: wiedza z sieci + to, co wyciągnąłem z plików (to drugie jest nowe).

---

## 1. Co mówi internet

### 1.1. OpenMemories-Docs / `hardware.rst` — źródło klasy A **[S]**

> **Front-End (DFE)** — The DFE is *optional* and is placed **between the image sensor
> and the SoC**.

| układ | nazwa | aparaty |
|---|---|---|
| CXD9974 | Pegasus | NEX-3, SLT-A33, … |
| CXD90009 | Sirius | NEX-FS700, PXW-FS5, … |
| CXD90016 | Mobius | DSC-RX1, NEX-6, … |
| **CXD90027** | **Regulus** | **ILCE-7, ILCE-6000**, … |
| CXD900?? | Leo | ILCE-7M3, … |

Kluczowe zdania z tego dokumentu:

- *„Starting with **CXD90016**, the DFE has an **integrated ARM core** (firmware in **`dfe.bin`**)."*
- *„In some cases, the DFE has a **private DRAM**. With **Leo**, the DRAM is even stacked on top (PoP)."*
- *„Note: the **RX10M2 includes a DFE** (CXD90027), while the **RX100M4 does not**."*

Czyli DFE nie jest uniwersalny — to opcjonalny układ, a A6000 go **ma** (Regulus CXD90027).

### 1.2. Wikipedia „Bionz" — parowanie układów **[B]**

Sekcja „BIONZ X – Sony CXD4236 ISP + CXD90027GF SoC" podaje przypisania modeli:

| konfiguracja | aparaty |
|---|---|
| SoC + **niezidentyfikowany ISP (stacked DRAM)** | α7, α7R, α7 II, **α6000**, **α6500**, α99, α7 III |
| SoC + **CXD4236-1GG** | α7S, α7S II, **RX100 IV**, FDR-AX33 |
| SoC + **dwa CXD4236-1GG** | α7R II, α7R III |
| niezidentyfikowane | ILCE-5000, DSC-RX10, ILCA-77M2, RX100 III, RX0, α7R IV |

⚠️ **Uwaga na nazewnictwo:** Wikipedia nazywa SoC „CXD90027GF", a OpenMemories —
`CXD90014`. To dwóch różnych autorów opisujących ten sam stos; artykuł ma zresztą
zgłoszone braki źródeł. **Więcej wiary w `hardware.rst`** (autorzy rozbierali firmware
i service manuale), ale mapowanie modeli z Wikipedii jest użyteczne jako trop.

### 1.3. Teardowny i identyfikacja układów **[B]**

- **iFixit, Sony a7R II Teardown (2015)**: na płycie zidentyfikowano
  **„Sony CXD4236-1GG, likely a newer version of the CXD4236GG"** jako image processor.
- **Chipworks** ma dokument *„Sony CXD4236GG Device Overview"* (CWR-1403-802) — płatny.
- **CXD4236-1GG / -2GG** są w obrocie jako części BGA (Censtry, YIC) — czyli układ
  jest dostępny handlowo.

### 1.4. Service manuale A6000 — są publicznie **[B]**

- *ILCE-6000/6000L/6000Y SERVICE MANUAL* Ver 1.2 (2014-09), 21 stron — iFixit.
- *SERVICE MANUAL **LEVEL 3*** Ver 1.1 (2014-11), **54 strony** — iFixit / photo-parts.com.ua.
- Nazwy płyt z manuala: **SY-1028** (płyta główna), **IS-095** (CMOS imager),
  IS-075/IS-076 (flexy), ST-1018.
- W manualu są schematy i listy części — to jedyne publiczne źródło, które może
  **fizycznie potwierdzić obecność CXD90027** na płycie (o ile Sony podaje tam numery CXD).

### 1.5. Czego w sieci **nie ma**

- **Zero** wzmianek o `dfe.bin` poza `hardware.rst`. Nikt tego pliku nie analizował.
- Zero analizy firmware DFE, jego ISA, protokołu, tabel trybów sensora.
- Zero informacji, czy DFE da się „przeprogramować" z SoC.

---

## 2. Co mówi firmware (ustalenia własne) **[S]**

### 2.1. `dfe.bin` to firmware procesora w układzie DFE

A6000, `/usr/dfe/dfe.bin`, **65 536 B**:

```
00000000: 18 f0 9f e5 18 f0 9f e5 ...   ← tablica wektorów ARM (LDR PC,[PC,#0x18])
```

Stringi w środku:

```
Detected IRQ : SiMISC CH0 / CH1
Detected IRQ : ZPD CH1
Detected IRQ : DEFCAM CH0 / CH1
Detected IRQ : DFELINK
CPU IRQ Sequence Start
CPU IRQ : ZPD0
```

Czyli: **kod ARM** (nie MIPS, nie sabin) na małym MCU wewnątrz DFE, obsługujący
kanały `ZPD` (defekt pikseli?), `DEFCAM` i **`DFELINK`** — łącze do SoC.
To dokładnie odpowiada zdaniu z `hardware.rst` o „integrated ARM core".

### 2.2. Kto ładuje `dfe.bin` — i tu jest różnica między modelami

Szukałem referencji do ścieżki:

| model | `/usr/dfe/dfe.bin` w `av-cam.bin` | plik na dysku |
|---|---|---|
| **A6000** | **TAK** (literalna ścieżka) | TAK (65 536 B) |
| **A6300** | **NIE** | **NIE MA** |

> **UWAGA — korekta z 2026-10-25 (patrz `13_DFE_GHIDRA.md` §10):** A6300 **ma**
> firmware front-endu, ale **wbudowany w `av-cam.bin`** pod `0xC1EB00` (nowsza wersja,
> z MMU). A6000 ma *dodatkowo* kopię `dfe.bin` w `av-cam.bin` pod `0xA67F00`
> (bit w bit ta sama co plik). Różnica to **generacja front-endu i sposób ładowania**,
> a nie „jest / nie ma".

A6300 ma natomiast w `av-cam.bin` inny interfejs:

```
DFE Acquire ERR:0x%02x
DfeCamAif%d: SgcParam Not Found
```

(`AIF` = inny model dostępu). Oba modele mają wspólne stringi `CPU APB : DFELINK …`,
`Detected IRQ : DFELINK` — czyli **obsługa łącza DFE w SoC jest w obu**, ale tylko
A6000 ładuje firmware do samego DFE.

### 2.3. Inwentarz układów per model — z zawartości `/usr`

| katalog/plik | A6000 | A6300 | co to |
|---|---|---|---|
| `/usr/dfe/dfe.bin` | ✅ 64 KiB | ❌ | DFE CXD90027 „Regulus" (ARM) |
| `/usr/beaune/ipl.bin` + `firmware.bin` | ❌ | ✅ 18 KB + 2.9 MB | kodek CXD4236 „Beaune" (MIPS, eSOL eBinder) |
| `nflasha3/bonobo.bin` | ❌ | ✅ 172 KB | układ stabilizacji R2J30503LG „Bonobo" (Renesas H8) |
| `nflasha3/sabin/{idt_cam,sa_dfdet,ssboot,ssboot_any}.bin` | ✅ | ✅ (identyczne) | podzbiór DSP ładowany przy starcie |

**Wniosek:** zawartość `/usr` (i `nflasha3`) to **wiarygodny inwentarz układów
pomocniczych danego modelu**. To najszybszy sposób, żeby stwierdzić „co ten model
ma w środku", bez rozbierania — i to działa nawet bez aparatu, na samym firmware.

### 2.4. Czego NIE można z tego wywnioskować

`Backup.bin` **nie jest** inwentarzem. Manifest komponentów (`big_backup.conf` →
`/setting/psd.bin`) wymienia `dfe/dfe.bin` w **obu** modelach, także w A6300, gdzie
tego pliku nie ma. To wspólny szablon listy wersji, nie lista obecnych układów.

---

## 3. Hipoteza: to wyjaśnia różnicę 1080p vs 4K

Sony w tej generacji miał **dwie różne architektury toru obrazu**:

```
A6000:  sensor ──► DFE CXD90027 (Regulus, ARM + własna DRAM) ──► CXD90014 (SoC)
        + osobny firmware dfe.bin, ładowany przez av-cam

A6300:  sensor ──► [front-end zintegrowany / inny tryb] ──► CXD90014 (SoC) ──► Beaune CXD4236
        + firmware beaune/ (MIPS, eSOL) do 4K
```

To spójne z:
- `hardware.rst`: DFE **opcjonalny**; „CXD90014 + Beaune → 4K",
- Wikipedią: α6000 = „unidentified ISP (stacked DRAM)", α6300 nie jest tam wymieniony,
- naszym plikiem: A6000 ładuje `dfe.bin`, A6300 nie ma czego ładować, ale ma Beaune.

⚠️ **Czego to nie dowodzi:** że A6300 fizycznie nie ma front-endu. Dowodzi tylko, że
**nie dostarcza jego firmware** i używa innego interfejsu (`DfeCamAif`). Rozstrzygnięcie
wymagałoby service manuala A6300 albo zdjęć płyty.

---

## 4. Dlaczego to jest ciekawy trop dla RE

`dfe.bin` to **firmware tego elementu, który czyta matrycę**. Jeśli gdziekolwiek w A6000
siedzą „nieużywane tryby sensora" (binning, line-skipping, inne rozdzielczości odczytu,
HDR wieloklatkowy), to właśnie tam — a nie w `av-cam.bin` ani w `sabin/`.

Zalety jako celu RE:
- **mały** (64 KiB), **ARM**, bez kompresji → wchodzi do Ghidry „od razu",
- prosty model przerwań (`SiMISC`, `ZPD`, `DEFCAM`, `DFELINK`) — da się rozpisać,
- nikt tego publicznie nie ruszył (patrz §1.5).

Naturalne kroki, gdyby ktoś chciał to drążyć:
1. Wgrać `dfe.bin` do Ghidry jako ARM (little-endian, base z wektora),
2. znaleźć tabelę trybów odczytu / konfigurację `ZPD` i `DEFCAM`,
3. porównać z DFE z innych modeli CXD90014 (RX10M2 ma ten sam CXD90027 —
   jego `dfe.bin` powinien być dobrym materiałem porównawczym).

---

## 5. Źródła

| źródło | typ | ocena |
|---|---|---|
| `OpenMemories-Docs/hardware.rst` (DFE, codec, power IC) | dokumentacja projektu | **A** |
| Własne rozpakowanie A6000 3.21 i A6300 2.01 | pliki | **A** (patrz `11_MODELE_BLIZNIACZE.md`) |
| Wikipedia „Bionz" (parowanie układów) | encyklopedia, ma braki źródeł | **B** |
| iFixit — Sony a7R II Teardown (CXD4236-1GG) | teardown | **B** |
| Chipworks „Sony CXD4236GG Device Overview" (CWR-1403-802) | płatny raport | **B** (za paywallem) |
| Service manual ILCE-6000 Level 3 (iFixit / photo-parts.com.ua) | dokument Sony | **A** (ale wymaga ręcznego przejrzenia schematów) |
