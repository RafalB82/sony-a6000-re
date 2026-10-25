# 15 — Podsumowanie całego rekonesansu

Stan na 2026-10-25. Wszystko poniżej albo zostało sprawdzone na plikach, albo jest
wyraźnie oznaczone jako hipoteza. **Nic nie było testowane na fizycznym aparacie.**

---

## 1. Sprzęt A6000 — potwierdzony schematem Sony

Ze *SERVICE MANUAL LEVEL 3* (ILCE-6000, plik `analysis/a6000-l3.pdf`):

| rola | oznaczenie | układ | uwagi |
|---|---|---|---|
| SoC (BIONZ X) | `IC6000` | pkg `MHZ4G8G01A` = **CXD90014** | 4× Cortex-A5 |
| **DFE (front-end)** | **`IC6200`** | **`CXD90027GF`** „CAMERA SIGNAL PROCESS" | 4 arkusze schematu; „not supplied" |
| power IC | `IC5700` | `MB9AF004BGL` („Darwin", Cortex-M3) | start SoC + RTC |
| inne | — | `CXD9950AK` (×2) | nieustalone |

Sensor: **IMX210** (klasy `C_ImagerCtrl_IMX210E` w `av-cam.bin`).

> Wcześniejsza wersja tego pliku mówiła „Qualcomm CXD90014" (za repo CliffVale) —
> **błędnie**. CXD90014 to Sony BIONZ X.

## 2. Firmware: struktura i co jest ruszalne

Prawdziwa tablica partycji jest **w firmware** (`0300_partconf/partinf.conf`, Sony 2013):

| dev | offset | rozmiar | mount | rola |
|---|---|---|---|---|
| — | `0x00000000` | 256 KiB | — | bootloader |
| nflasha1 | `0x00040000` | 6 MiB | — | SYSTEM (Updater) |
| **nflasha2** | `0x00640000` | 13 MiB | **`/setting`** | ← **`Backup.bin`** |
| nflasha3 | `0x01340000` | 30 MiB | `/system` | **potok AV (`av-cam.bin`)** |
| nflasha5 | `0x03B40000` | 60 MiB | `/wbi` | Warm Boot Image |
| nflasha7 | `0x07C40000` | 4 MiB | `/rootfs` | rootfs |
| nflasha15 | `0x08B40000` | 100 MiB | `/usr` | **Linux userland (cramfs)** |
| nflasha16 | `0x0EF40000` | 82.75 MiB | `/android/system` | |
| **nflasha17** | `0x14200000` | 99.75 MiB | **`/android/data`** | FAT16, APKi |
| nflasha18 | `0x1A5C0000` | 20 MiB | `/lens` | LensData |
| nflasha23 | `0x1B9C0000` | 1 MiB | `/PMBP` | |

Koniec NAND: `0x1BAC0000` = **463.75 MiB**. Wszystko ciągłe, bez dziur.

**Flashowalne przez oficjalny update:** `nflasha3`, `5`, `7`, `15`, `16`.
**Nieruszane:** `nflasha17` (dane) i `nflasha2` (ustawienia).

## 3. Integralność: brak podpisów, jest CRC32

Sprawdzone przez przeliczenie — **wszystkie** manifesty `*.sum` to CRC32:

| plik | CRC32 w manifeście | przeliczone |
|---|---|---|
| `nflasha3` / `5` / `7` / `15` / `16` | `0c047870` / `9cb10112` / `b969856d` / `df198ecd` / `c77af80c` | ✅ |
| `partinf.conf`, `mount.conf`, `darwin_core.bin`, `Backup.bin` (per region) | — | ✅ |

Updater weryfikuje **tylko**: CRC32 + typ LSI (main/sub po power ICU) + pojemność NAND
(`chknandcapa.elf`). **Zero weryfikacji autorstwa i wersji.**

**Round-trip:** `fwtool.py unpack` → `pack` daje plik **bit w bit identyczny** z oryginałem
Sony (`sha256 29aef21a…892f`). Czyli kryptografia jest w pełni odwracalna i **można
zbudować własny, wgrywalny firmware**.

## 4. Co realnie da się zmienić — cztery warstwy

| # | warstwa | co | ryzyko | status |
|---|---|---|---|---|
| 0 | `Backup.bin` | ustawienia | zerowe | działa (OpenMemories-Tweak) |
| 1 | APK PMCA | własny kod, **322 klasy `com.sony.*`** | niskie | działa |
| 2 | root (telnet/adb) | dowolne binarki w Linuksie | średnie | działa |
| 3 | **obrazy partycji** | `/usr`, `/system`, `/rootfs`, `/android/system` | wysokie | **wykonalne** |

### Ustawienia (Backup.bin)
- **11 gotowych `Backup.bin` per region** jest w firmware (`0110_backup/…/CX7750x_*.bin`).
- 17 167 właściwości (16 102 istniejących); regiony różnią się **37–46 wpisami**.
- Znane ID: limit nagrania `0x003c0373-75`, PAL/NTSC `0x01070148`, języki
  `0x010d008f..b1`, format/JPEG `0x01070013/14`, DRO `0x01070104`, Picture Effect
  `0x010706f1`, WB `0x01070016..19`, **clean HDMI `0x01070a47`**.
- Region/język da się ustawić „fabrycznie" przez update: `endupdate.sh` kopiuje
  `backup/*/*/*.bin` do `/setting/Backup.bin`.

### Kod (warstwa 3)
- Własny payload **już działa** na A6000: `updatershell/updaterbody.cpp` ma1co
  (`libupdaterbody_gen3.so`) daje `sh -i`, `PUSH`/`PULL` (też `/dev/nflasha*`),
  `RMEM` (odczyt pamięci), zrzut bootloadera i BootROM-u.
- Ryzyko bricksa: tylko `loader.sum` → `pformat_*.elf` (bootloader).

## 5. DFE — rozpracowany firmware (`dfe.bin`)

- `/usr/dfe/dfe.bin` **65 536 B**, ARM LE, baza **`0x01000000`**, reset `0x01005870`.
- **83 procedury**, 94 stringi. Wszystkie nazwane (`analysis/dfe-names.txt`).
- **To nie jest „głupi front-end"**: obsługuje **ZPD = detekcję fazową AF**
  (`"Hello Regulus: apl_zpd_af_det"`), korekcję defektów na 6 kanałach
  (**DFECAM0–5**), generator timingów (**SSG**), łącze **DFELINK** do BIONZ.
- Duża część kodu to **self-test** (testy APB każdego bloku + testy linii IRQ + stringi
  `>>> Simulation Finished`).
- **Kanał logów: nie UART — bufor w RAM pod `0x0102D000`** (wskaźnik w `0x01005ce4`).
- Mapa rejestrów wyprowadzona z literałów: ZPD `0x01010000`, SSG `0x01080020`,
  SiMISC `0x01088200`, DFECAM0–5 `0x010A0010`…`0x010CF000`, DFELINK `0x010F0000`.
- Kopia `dfe.bin` leży **bit w bit wewnątrz `av-cam.bin`** pod `0xA67F00`.

## 6. Warstwa AV: sabin i wtyczki

- `/usr/sabin`: **68 plików** — 44 programy DSP w kontenerze (magic `aa0a1391`) + 24 tabele.
- Klasa `0x010083` = **rodzina AVC**: 3 enkodery (`performance`, `quality`,
  `performance_plus`) + 2 dekodery. **Nie ustalono, którego używa A6000** — kod jest PIC.
- 4K: `av-cam.bin` referuje 27 plików `sabin`; **25 istnieje, brakuje
  `dcv_psf_table_movie_4k.bin` i `dcv_psf_table_dualrec.bin`** — ale wszystkie
  „tap step" dla 4K **są** dostarczone.
- `/usr/scenario`: **35 wtyczek `.so`** (ELF ARM, `scenario_run`, szyna `osal_*`).
  W tabeli `libsencore.so` jest 27 nazw; brakuje m.in. `*_HDMI_SDI` (brak złącza).
  Można je odpalać pojedynczo przez **`/usr/bin/scenario.elf`**.

## 7. A6300 — czemu ma 4K, a A6000 nie

| | A6000 | A6300 |
|---|---|---|
| SoC (pkg) | `MHZ4G8G01A` | `MCZ4G8G21A` |
| **DFE `IC6200`** | **`CXD90027GF`** | **`CXD90027GF`** ← ten sam |
| **kodek `IC9012`** | **brak** | **`CXD4236-1GG`** ← Beaune |
| power IC | `MB9AF004BGL` | `MB9AF004BGL` |
| `/usr/beaune/` | ❌ | ✅ `ipl.bin` + `firmware.bin` (2.9 MB) |
| `beaune_drv.ko` | ❌ | ✅ |
| programy DSP | 69 | 79 (+10, m.in. tabela 4K) |

**4K jest niemożliwe na A6000 — brak układu Beaune.** Potwierdzone trzema
niezależnymi źródłami: schematem (CXD4236 tylko w A6300), firmware (`beaune/` tylko
w A6300) i tabelą w `hardware.rst` („CXD90014 + Beaune → 4K").

## 8. Czy nowszy DFE z A6300 da się uruchomić w A6000?

| | A6000 | A6300 |
|---|---|---|
| rozmiar | 65 536 B | 65 536 B |
| baza / wektory | `0x01000000` | identyczne |
| tag celu | `20140123_0000_REGULUS` | `20151222_00_1971_REGULUS` |
| MMU | brak śladów | `ICACHE,DCACHE and MMU Enable` (7× CP15 vs 2×) |
| bloki MMIO | 18 | 22 (+5) |
| stringi wspólne | 94 z 97 | |

**Ten sam układ, firmware 2 lata nowszy.** Podmiana jest technicznie realna
(ten sam rozmiar, baza, tag), plik leży w `/usr` → odwracalne reflashem.
Blokery: MMU, 5 dodatkowych bloków rejestrów, sprzężenie z kodem SoC
(`SHD::Regulus`, `Camera::ZPD::Control` w `av-cam.bin`).
**Szansa: ~30–40% na pełne działanie, wyżej na częściowe.** Szczegóły: `14_`.

## 9. Prior art — kto już tą drogą szedł

| kto | co | stan |
|---|---|---|
| **nex-hack** (2012–2014) | odszyfrowanie, repack, **re-encrypt do wgrywalnego pliku** | ✅ działało; tryb `-m modify` **nigdy nie dokończony** |
| **ma1co** | `fwtool.py` (pack dla CXD90014), PMCA-RE, Tweak, Platform, **SA-DSP (Ghidra)**, **qemu**, CI, Symbols | ✅ aktywne |
| **voxivoid / Recipe Lab** | **mapa ID ustawień A6000** (metodą `libObj.so` + diff menu) | ✅ zweryfikowana |
| społeczność | clean HDMI `bk.elf w 0x01070a47 00` (A5000) — **działa też na A6000** | ✅ sprawdzone w `Backup.bin` |
| **nikt** | wgranie zmodyfikowanego obrazu partycji do aparatu | ❌ **brak relacji** |
| **nikt** | `dfe.bin`, sabin, wtyczki `scenario`, mapowanie BKID→ID | ❌ **dziewiczy teren** |

## 10. Pytania otwarte (uszeregowane)

1. **Czy A6000 ładuje DFE z pliku czy z kopii w `av-cam.bin` (0xA67F00)?** Kod PIC,
   Ghidra nie ukończyła 11 MB w limicie. **Rozstrzygalne eksperymentem A/B.**
2. Mapowanie **BKID → ID**: 1058 nazw w firmware, brak tabeli. Metoda znana
   (`libObj.so`), wymaga pracy.
3. Który wariant enkodera AVC wybiera A6000 (`performance`/`quality`/`plus`)?
4. Co robią pozostałe ~16 000 właściwości `Backup.bin`.
5. Czy da się odczytać bufor logów DFE (`0x0102D000`) z SoC — i jak.

## 11. Indeks dokumentów

| plik | treść |
|---|---|
| `01_STAN.md` | co pewne / hipoteza / podejrzane |
| `02_MECHANIZM.md` | 3 tryby USB, `Backup.bin`, ID, protection |
| `03_A6000_FIRMWARE.md` | sprzęt, fwtool, mapa NAND |
| `04_ZRODLA.md` | źródła + ocena A/B/C/D |
| `05_DALEJ.md` | plan, ryzyka |
| `06_CLIFFVALE_OCENA.md` | weryfikacja repo CliffVale |
| `07_FIRMWARE_3.21.md` | co jest w firmware (partycje, 11× Backup.bin) |
| `08_ZMIANY_W_KODZIE.md` | 4 warstwy modyfikacji, dowody CRC32 |
| `09_ENKODERY_I_WTYCZKI.md` | sabin, enkodery, `scenario` |
| `10_PRIOR_ART.md` | kto już próbował |
| `11_MODELE_BLIZNIACZE.md` | A6000 vs A6300, 66 modeli CXD90014 |
| `12_DFE.md` | DFE: sieć + pliki |
| `13_DFE_GHIDRA.md` | analiza Ghidry, MMIO, logi, nazwy |
| `14_DFE_A6300_CZY_ZADZIALA.md` | podmiana DFE A6300→A6000 |

Zasoby: `fw-3.21/`, `fw-a6300/`, `analysis/` (blob A6300, nazwy, service manuale),
`tools/backup.py`, sklonowane repo ma1co.

## 12. Metodyka i zastrzeżenia

- Wszystko pochodzi z **plików** (firmware Sony, schematy Sony, kod ma1co) albo
  z internetu z podaną oceną wiarygodności.
- **Żaden test nie był wykonany na sprzęcie.** „Działa" w tym dokumencie znaczy
  „zaimplementowane i opisane publicznie", nie „sprawdzone przez nas".
- Dwa razy musiałem korygować własne wnioski: „Qualcomm CXD90014" (błędne)
  i „A6300 nie ma DFE" (niepełne — ma, wbudowany w `av-cam.bin`).
