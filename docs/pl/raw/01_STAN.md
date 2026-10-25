# 01 — Stan wiedzy: co pewne, co hipoteza

Ostatnia aktualizacja: 2026-10-25. Nic nie zweryfikowano na fizycznym sprzęcie.

## Pewne (z kodu źródłowego / oficjalnych tabel)

| Fakt | Źródło |
|---|---|
| ILCE-6000: architektura **CXD90014**, model code `0x41030035`, API PMCA **2.4** | `fwtool.py/devices.yml:400` (lokalnie) |
| CXD90014 wspiera **updatershell** | `OpenMemories-Docs/devices.rst` (lista `updatershellKeys`) |
| Wszystkie modele wspierają **serviceshell** | tamże |
| PMCA = Android **2.3.7** (API level 10), akceptowane certyfikaty debug i release | README Sony-PMCA-RE |
| Firmware CXD90014 rozpakowywalny fwtool.py | `fwtool.py/README.md` |
| Struktura `Backup.bin`: nagłówek `BK2`/`BK4` @0x0c, `id1` (flaga protection) @0x28, `region` @0xc0 | `pmca/backup/__init__.py` |
| ID ustawień: limit nagrania `0x003c0373-75`, limit 4K `0x003c04b6`, PAL/NTSC `0x01070148`, języki `0x010d008f..b1`, protection osobne API | `OpenMemories-Platform/api/backup.cpp` |
| Wartości limitu nagrania: off `{0,29,50}` (29m50s), on `{13,1,0}` (13h01m); licznik 90 kHz, teoretyczne max 13h15m21s | tamże, komentarz w `tweaks.cpp` |
| Języki: 35 slotów, `1` = włączony, `2` = wyłączony; regiony mapowane na tablice (np. `J1` = tylko japoński, `ALLLANG` = wszystkie) | `api/backup.hpp`, `api/backup.cpp` |
| Limit 4K (RX100M4): 2 bajty LE, off `0x012c` (300 s), on `0x7fff` | `api/tweaks.cpp` |
| Tweak nie parsuje pliku sam — używa API kamery (`Backup_read`/`Backup_write` → libBackup), więc protection egzekwuje firmware | `api/backup.cpp` |
| Region **J1**: protection można tylko *włączyć*, nie wyłączyć; obejście = `AdvancedProtectionTweak` (podmiana regionu na `""` przez `Backup_protect`, zmiana flagi, przywrócenie regionu) | `api/tweaks.cpp` |
| Sklep PMCA: płatne zakupy do 2023-09-30, **całkowite wyłączenie 2025-08-31** | Sony art. 00289030 (za blogiem) |
| A6400 **nie** wspiera instalacji appek PMCA (issue #381 / #733) — to inna generacja | blog + issues |

## Prawdopodobne, ale niesprawdzone u nas

| Twierdzenie | Pewność | Uwaga |
|---|---|---|
| A6000 ma USB ID `054c:07c4` w trybie MSC (updater: `054c:03e2`) | wysoka | nie sprawdzone na sprzęcie, sprawdzić `lsusb` |
| Firmware A6000 ostatni = **3.21** | potwierdzone pośrednio | to firmware, który rozpakowaliśmy; stan na kamerze sprawdzić w menu |
| Raw dump NAND = 483 MB, `pull /dev/nflasha` | średnia | NAND wg `partinf.conf` ma 463.75 MiB = 486 MB; procedura z jednego źródła |
| Wejście w updater mode wymaga **fizycznego naciśnięcia OK** na ekranie kamery | wysoka | potwierdzone też przez innych; bez tego timeout ~5 min |
| A6000 nie ma czystego HDMI (bug "beauty filter") → potrzebna appka HDMICam | średnia | wymaga testu na żywo |

## Sprawdzone empirycznie 2026-10-25 (firmware 3.21 rozpakowany lokalnie)

Pełny opis: `07_FIRMWARE_3.21.md`, ocena repo CliffVale: `06_CLIFFVALE_OCENA.md`.

- **Oficjalny firmware da się pobrać bez kamery** i rozpakować `fwtool.py` — hashe DMG i `.dat` zgodne z podanymi przez CliffVale.
- **Prawdziwa tablica partycji jest w firmware** (`0300_partconf/partinf.conf`): 15 partycji,
  ciągłe od `0x00000000` do `0x1BAC0000` (463.75 MiB). `Backup.bin` leży na **nflasha2** (`/setting`),
  Android `/data` to **nflasha17** (`0x14200000`, 99.75 MiB) — potwierdza trop CliffVale.
- **W firmware jest 11 gotowych `Backup.bin` (BK4), po jednym na region** — 17 167 właściwości,
  16 102 istniejących. Regiony różnią się tylko 37–46 właściwościami. To zamyka pytanie
  „co jest w pozostałych 15 000 wpisów" — mamy pełną listę ID bez kamery.
- Zweryfikowane wartości domyślne: `rec_limit = {0, 29, 50}` (29m50s), `model_name = "ILCE-6000"`,
  region `CX77500_ALLLANG` itd. — zgodne z kodami z `OpenMemories-Platform`.
- **CXD90014 to NIE Qualcomm** — to Sony BIONZ X, 4× ARM Cortex-A5 (OpenMemories-Docs/hardware.rst).

## Sprawdzone 2026-10-25 — modyfikowalność kodu (`08_ZMIANY_W_KODZIE.md`)

- **Firmware nie jest podpisany.** Wszystkie manifesty `*.sum` to **CRC32** — przeliczyłem
  je dla wszystkich 5 obrazów partycji, `config`, `partinf.conf`, `darwin_core.bin`
  i `Backup.bin`: zgodne. Nie ma RSA/ECDSA.
- **Updater weryfikuje tylko:** CRC32 + typ LSI (main/sub, po power ICU) + pojemność NAND.
  Zero sprawdzania autorstwa czy wersji.
- **Własny kod już działa na A6000:** `updatershell/updaterbody.cpp` to payload ma1co
  (`libupdaterbody_gen3.so`), który kamera wykonuje; daje `sh -i`, `PUSH`/`PULL`
  dowolnych plików (także `/dev/nflasha*`), `RMEM` (odczyt pamięci), zrzut bootloadera.
- **Flashowalne przez update:** tylko `nflasha3` (/system), `5` (/wbi), `7` (/rootfs),
  `15` (/usr), `16` (/android/system). `nflasha17` (dane) i `nflasha2` (Backup.bin)
  nie są ruszane.
- **Region/język da się ustawić „fabrycznie" przez update** — `endupdate.sh` kopiuje
  `backup/*/*/*.bin` do `/setting/Backup.bin`; wgranie fdat z `CX77500_ALLLANG.bin`
  daje wszystkie języki bez hackowania protection.
- **4K jest niemożliwe na A6000** — potok AV obsługuje enkoder „Beaune" (CXD4236),
  ale A6000 go nie ma (1080p60 = samo CXD90014). Sensor to **IMX210**.

## Niepewne / podejrzane

- **CliffVale/sony-a6000-firmware-research**: sprawdzone 2026-10-25 na materiale —
  **offsepty prawdziwe, opis częściowo zmyślony**. Metoda i starty partycji zgodne
  z `partinf.conf` Sony, ale tabela „byte-identical verification" jest wyliczona
  z zaokrągleń (nie zmierzona), mapa myli rozmiar obrazu z firmware z rozmiarem
  partycji, a „trailing 187.47 MB" jest błędne (realnie 21 MiB: LensData + PMBP).
  Szczegóły i dowody: `06_CLIFFVALE_OCENA.md`. **Nie używać jako źródła faktów.**
- Blog docodethatmatters (część "research", sierpień 2026) sam deklaruje, że jest
  "mostly automated researched reviewed" — czyli streszczenie cudzych źródeł,
  miejscami z błędami (miesza A6000 z A6400, "A6000: Likely compatible").
- Twierdzenie, że A6000 ma bug z beauty filter na HDMI — nie znalazłem źródła
  pierwotnego poza tym blogiem.
- Procedura `pull /dev/nflasha`: **potwierdzona w kodzie** — `pull`/`push` to komendy
  hosta (`pmca/platform/__init__.py`), a po stronie kamery odpowiadają im komendy
  `PULL`/`PUSH` w `updatershell/usbshell.cpp`. Wcześniejsza uwaga o „niezweryfikowane"
  była błędna.

## Czego jeszcze nie wiemy

Zobacz `05_DALEJ.md`.
