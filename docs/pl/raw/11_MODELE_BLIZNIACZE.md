# 11 — Modele bliźniacze: co daje porównanie z A6300

Pomysł: A6000 nie jest sam — na CXD90014 jest **66 modeli**. Porównałem firmware A6000 3.21
z **A6300 2.01** (ten sam SoC, ale **ma 4K**). Wynik rozstrzyga pytanie o 4K
**twardo, z plików**, a nie z tabelki.

---

## 1. Rodzina CXD90014 (z `fwtool.py/devices.yml`) — 66 modeli

Najbliżsi krewni (model code, wersja API PMCA):

| model | model code | PMCA | 4K? | uwagi |
|---|---|---|---|---|
| **ILCE-6000** | `0x41030035` | 2.4 | ❌ | nasz |
| **ILCE-5100** | `0x42030036` | 2.7 | ❌ | **bliźniak** — ta sama matryca, inny korpus |
| ILCE-5000 | `0x41030012` | 2.3 | ❌ | „jeden w dół" |
| **ILCE-6300** | `0x61030034` | 2.15 | ✅ | **jeden w górę** — porównany niżej |
| ILCE-6500 | `0x61030035` | 2.17 | ✅ | jak A6300 + IBIS |
| ILCE-7 / 7R / 7S | `0x41030013` / `34` / `42030032` | 2.3 / 2.3 / 2.6 | ❌ | pełna klatka, ta sama platforma |
| ILCE-7M2 / 7RM2 / 7SM2 | `0x51030031` / `34` / `41` | 2.10 / 2.14 / 2.14 | RM2 ✅ | |
| DSC-RX100M3 / M4 / M5 | `0x41020022` / `0x51020034` / `0x61020023` | 2.6 / 2.14 / 2.16 | M4/M5 ✅ | M4 = ten sam problem limitu 4K |
| DSC-RX10M2 / M3, RX1RM2, RX0 | `0x51020038` / `0x61020032` / `0x51020035` / `0x61020010` | 2.14 / 2.15 / 2.14 / — | część ✅ | |
| FDR-*/HDR-* (kamery) | różne | 2.5–2.15 | — | ta sama architektura, inny userland |

Wniosek: to **jedna platforma sprzętowo-programowa** z różnymi matrycami, układami
dodatkowymi i konfiguracją. Dlatego porównanie z A6300 jest miarodajne.

---

## 2. A6000 3.21 vs A6300 2.01 — pełne porównanie

### 2.1. Co jest **identyczne**

| element | wynik |
|---|---|
| SoC (z `chassis` w updaterze) | `CXD90014` w obu |
| `dcv_psf_table_movie.bin` | **ten sam SHA256** |
| `dcv_psf_table_still.bin` | **ten sam SHA256** |
| nagłówek tabel PSF | `IMX210` w obu → **ta sama rodzina matrycy** |
| wtyczki `/usr/scenario` | **35 plików, ta sama lista**, bez różnic |

**To ważne:** scenariusze **nie** są mechanizmem odcinania 4K. Warstwa wtyczek jest
wspólna i niezmieniona.

### 2.2. Co jest **różne**

| element | A6000 | A6300 |
|---|---|---|
| `av-cam.bin` (kod AV) | 11 427 236 B | 13 382 836 B |
| referencje do `sabin/` | 29 | 31 (+2 tabele „macro") |
| programy w `/usr/sabin` | 69 plików | **79 plików** |
| enkodery AVC | `performance` 190 KB, `quality` 196 KB, `pp` 199 KB | **227 / 231 / 228 KB** |
| **katalog `/usr/beaune/`** | **BRAK** | **`ipl.bin` (18 892 B) + `firmware.bin` (2 938 324 B)** |
| katalog `/usr/dfe/` | `dfe.bin` (65 536 B) | **BRAK** |
| nflasha3 | 30 MiB @ `0x01340000` | 20 MiB @ `0x01340000` |
| nflasha15 (`/usr`) | 100 MiB @ `0x08B40000` | 100 MiB @ `0x08640000` |
| nflasha17 (`/android/data`) | @ `0x14200000` | @ `0x13D00000` |

### 2.3. Programy DSP, które ma **tylko** A6300 (10 sztuk)

```
dcv_psf_table_movie_4k.bin      ← tabela 4K (10 728 B, ten sam rozmiar co movie)
sa_aaclcenc_aaclcdec.bin        ← AAC enc+dec w jednym
sa_bayes_tracker_edge.bin       ← AF „edge" (lepszy AF A6300)
sa_integdec.bin
sa_motionshot.bin
sa_nlap.bin
sa_replacer.bin
sa_seg.bin
sa_smod.bin
sa_zoom_nr.bin
```

**A6000 nie ma ani jednego pliku, którego nie ma A6300** — zbiór A6000 jest
podzbiorem A6300. To klasyczny model „platforma + wycinanka z listy plików".

---

## 3. Rozstrzygnięcie sprawy 4K — jest układ, nie tylko tabela

Do tej pory mieliśmy: „brakuje tabeli PSF" + „wg tabeli hardware 4K wymaga Beaune".
Teraz mamy **dowód z plików**:

```
A6300 /usr/beaune/ipl.bin       18 892 B   "eSOL-eBinder-B", "ipl_SYS", "SW_VER_03_20_04"
A6300 /usr/beaune/firmware.bin  2 938 324 B  "SW_VER_03_20_04", kod startowy 0x00010000
A6000                            — BRAK katalogu beaune
```

To dokładnie odpowiada opisowi z `OpenMemories-Docs/hardware.rst`:

> „These chips contain MIPS CPUs and software is developed using eSOL eBinder.
> There are always two binaries: **ipl** is the loader, which decompresses the actual
> application contained in the second binary."

Czyli **A6300 ma fizyczny układ Beaune (CXD4236)**, a A6000 nie. Bez tego układu
4K nie ma czym kodować — **4K na A6000 jest niemożliwe, i to jest ograniczenie sprzętowe,
teraz potwierdzone nie tabelką, a zawartością firmware.**

Ciekawostka odwrotna: A6000 ma `dfe/dfe.bin` (DFE = CXD90027 „Regulus"), a A6300
**nie ma go jako pliku** — ale ma własny, nowszy blob front-endu wbudowany w `av-cam.bin`
pod `0xC1EB00` (z MMU). Szczegóły i korekta: `13_DFE_GHIDRA.md` §10.
**nie ma katalogu dfe w ogóle** — czyli DFE w A6300 jest rozwiązany inaczej
(lub jego firmware leży gdzie indziej). Warto sprawdzić, jeśli ktoś będzie drążył
potok obrazu.

---

## 4. Ale… tabela 4K jest zgodna z naszą matrycą

Zaskoczenie: `dcv_psf_table_movie.bin` A6000 i A6300 są **bit w bit identyczne**,
a `dcv_psf_table_movie_4k.bin` z A6300 ma **dokładnie ten sam rozmiar** (10 728 B)
i ten sam nagłówek `IMX210`.

- A6300 `movie` vs `movie_4k`: **6 690 z 10 728 bajtów** różnicy
- A6000 `movie` vs A6300 `movie_4k`: **też 6 690** (bo pliki `movie` są identyczne)

Czyli **tabela 4K to wariant trybu tej samej matrycy**, a nie inny sensor.
Gdyby ktoś chciał zrobić eksperyment „wrzucę tabelę 4K do A6000 i zobaczę, co się stanie" —
tabela jest merytorycznie właściwa. Test jest sensowny jako **diagnostyka**
(czy AV w ogóle próbuje wejść w tryb 4K), ale nie da 4K, bo brakuje Beaune.

**Aktualizacja planu z `09_ENKODERY_I_WTYCZKI.md`:** eksperyment 3 („dorzucić tabelę 4K")
ma teraz źródło pliku — A6300 2.01 — i znany wynik negatywny (brak układu).

---

## 5. Co jeszcze daje rodzina: ekosystem RE na bliźniakach

### 5.1. `voxivoid/recipe-lab-sony-pmca` — **mapa ID ustawień A6000**

Najważniejsze znalezisko tego rekonesansu. Aktywny projekt (jeden autor, **ma A6000**),
który zrobił dokładnie to, co w `09` nazwałem „najcenniejszym tropem": rozpisał
**mapę slotów ustawień**, metodą „disassembling the camera app's parameter registration
in **`libObj.so`**" — czyli tego samego pliku, w którym ja znalazłem 237 nazw `BKID_`.

Zweryfikowane (metodą diffu menu) ID z ich dokumentacji:

| ustawienie | ID |
|---|---|
| Creative Style | `0x01070175` (1 standard, 2 vivid, 3 neutral, 6 mono, 14 sepia) |
| Contrast / Saturation / Sharpness | `0x01070178` / `0x01070187` / `0x0107018a` |
| Picture Profile no. | `0x0107031c` |
| WB mode / Kelvin / A-B / G-M | `0x01070019` / `0x01070018` / `0x01070017` / `0x01070016` |
| WB kopie per-tryb (AWB, temp) | `0x0107067f`/`0x0107067e`, `0x01070683`/`0x01070682` |
| Picture Effect | `0x010706f1` (+ `0x010709d8`, `0x010706f3`, `0x010706ee`, `0x010706ef`) |
| Exposure bias | `0x010700b8` + kopia `0x01070c7f` |
| DRO | `0x01070104` + poziom `0x01070775` |
| Quality: format / JPEG level | `0x01070013` (+`0x01070aa9`) / `0x01070014` (+`0x01070aaa`) |

Wszystkie w przestrzeni `0x0107xxxx` — tej samej co hack clean-HDMI (`0x01070a47`)
i NTSC (`0x01070148`). **To pierwsza publiczna, zweryfikowana mapa ID dla A6000.**

Dodatkowo (potwierdza moje ustalenia): kompatybilne body wg autora to
A6000, A6300, A6500, A5100, A7 II, A7S II — z adnotacją, że *„the setting IDs
were found on an A6000 and may sit elsewhere on another body"*, czyli **ID potrafią
się przesuwać między modelami**.

### 5.2. Otwarte ścieżki na bliźniakach

| temat | stan |
|---|---|
| **A5100** (bliźniak matrycowy) | brak dedykowanego RE; OpenMemories-Tweak działa (PMCA 2.7) |
| **A6500** | działa Tweak (PMCA 2.17), brak analizy firmware |
| **A6300** | **nikt nie opisał unpacku** — a to najciekawszy model (4K + ten sam SoC) |
| **RX100M4** | jedyny model z tweakiem limitu 4K w OpenMemories-Tweak |
| **A7/A7R/A7S** | PMCA 2.3, dużo appek, brak analizy AV |

---

## 6. Co z tego wynika praktycznie

1. **4K — temat zamknięty.** Nie z powodu firmware, tylko braku układu Beaune.
   Potwierdzone plikami (`beaune/ipl.bin` + `firmware.bin` tylko w A6300).
2. **Wtyczki scenariuszy nie są mechanizmem gatingu** — identyczne w obu modelach.
   To podnosi wartość hipotezy, że można je podmieniać/własne pisać.
3. **Nie da się „przenieść" A6300 do A6000**: inny układ partycji (nflasha3 20 vs 30 MiB,
   przesunięcia nflasha15/16/17), inny `av-cam.bin`, inny zestaw DSP. To inna maszyna
   na wspólnej platformie.
4. **Mapa ID ustawień istnieje i jest zweryfikowana** — można ją rozszerzać,
   bo znamy metodę (`libObj.so` + diff menu).
5. **Eksperyment z tabelą 4K ma źródło** (A6300 2.01), ale sens tylko diagnostyczny.

---

## 7. Materiały lokalne

```
fw-a6300/                      # rozpakowany A6300 2.01 (Update_ILCE6300V201.exe, 250 MB)
fw-3.21/                       # A6000 3.21
OpenMemories-Symbols/          # bin2elf.py + baza symboli (11 starych modeli, bez A6000)
OpenMemories-CI/               # runner do emulacji w QEMU
```

Dostęp do firmware A6300 (do reprodukcji):
`https://support.d-imaging.sony.co.jp/download/NEX/Ni7RZHz1oz/Update_ILCE6300V201.exe`
(link wyciągnięty z archiwum strony Sony; `curl` z UA przeglądarki działa).
