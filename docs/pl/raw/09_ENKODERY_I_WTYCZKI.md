# 09 — Programy enkodera (SA DSP) i wtyczki scenariuszy

Szczegółowa analiza `/usr/sabin/` i `/usr/scenario/` z firmware 3.21.
Wszystko **[S]** = odczytane z plików, chyba że oznaczono inaczej.

---

## 1. Programy SA DSP — anatomia `/usr/sabin/`

W katalogu jest **68 plików**:

- **44 programy** w kontenerze Sony (magic `aa0a 1391`)
- **24 pliki danych** (tabele PSF, „tap step" dla Spica, parametry jądra STAR)

### 1.1. Format kontenera — rozpracowany **[S]**

```
offset  pole
0x00    magic   aa 0a 13 91
0x04    wersja  04 00 00 02     (zawsze 0x02000004)
0x08    ID      01 c0 00 02     (unikalny numer wariantu)
0x0c    klasa   83 00 01 00     (rodzaj: kodek/audio/obraz/narzędzie)
0x10    0
0x14    nazwa   "SA_ZM_AVCEP"   (ASCII, ~10 znaków, potem wersja "0x00")
0x18    ...
```

Nazwa koduje: `SA_` + **silnik** + `_` + **moduł**.
Silniki: **ZM** = Zima, **MN** = Minna, **ST** = startup, brak = wspólny.
Moduł: `AVCEP` (AVC Encoder Performance), `AVCEQ` (…Quality), `AVCEPP` (…Performance Plus),
`AVCDP` (AVC Decoder Performance), `AVCDC` (…Compatible) itd.

### 1.2. Katalog wg klasy

| klasa | co to | programy |
|---|---|---|
| `0x010001` | obrazy/NR (Zima) | `SA_STAR`, `SALFNRZ0` (LFNR = light-frame NR), `SA_Z_ST0` (startup) |
| `0x010002` | **audio + JPEG** | `ZM_AACE/AACD` (AAC), `ZM_AC3D`, `ZM_DD51E` (Dolby 5.1), `ZM_LPCME/D`, `ZM_A3E` („integenc" — **to audio, nie wideo!**), `SAJPG*` |
| `0x010003` | narzędzia obrazu | `APOLLO_5`, `SAJPGD_U`, `SAJPGE_U` |
| `0x010004` | AC3 enc+dec, NR Minna | `ZM_ACE&D`, `SALFNRM0`, `SA_Z_MNS` |
| `0x010005` | DCV | `SA_DCV` |
| `0x010007` | detekcja defektów | `SADEFECT` |
| `0x010008` | NR Minna (kanał 1) | `SALFNRM1`, `SA_Z_MN1` |
| `0x01000c` | AF | `SABT` (Bayes tracker) |
| `0x01000f` | narzędzia AV | **`SA_FRC2`** (frame-rate converter), `SA_CECIL`, `SASFTFCS`, `SA_SHAPE`, `SATBOX`, `SA_ZPHD2` |
| **`0x010083`** | **rodzina AVC (wideo)** | **5 programów — patrz §2** |
| `0x02000f` | panorama | `SAPANORM` |
| `0x030001` | BD/BDEX | `SA_BDRO2` |
| `0x03000d` | **SPICA** (główny blok obrazu) | `SA_SPICA` |
| `0x050004` | redukcja szumów | `DRECKKNR` |
| `0x080001` | narzędzia diagnostyczne | `ZITTOOLS` |

**Korekta wcześniejszego założenia:** `sa_integenc.bin` (394 KB) to **enkoder audio A3E**,
a nie „zintegrowany enkoder wideo". Wideo to wyłącznie klasa `0x010083`.

### 1.3. Co z tego wynika

Programy to **kontenery z danymi dla DSP „SA"** (własna ISA, 16 rejestrów — patrz
`hardware.rst`), a nie kod ARM. Ładuje je **`av-cam.bin`** (w `/system`, 11.4 MB) —
to jedyny plik w całym firmware, który zawiera magic `aa0a 1391`. **[S]**

---

## 2. Rodzina AVC — 3 enkodery, 2 dekodery

| plik | nazwa wewn. | ID | rozmiar |
|---|---|---|---|
| `sa_avce_performance_zma.bin` | `SA_ZM_AVCEP` | `0x0200c001` | 190 468 |
| `sa_avce_quality_zma.bin` | `SA_ZM_AVCEQ` | `0x0200c101` | 196 228 |
| `sa_avce_performance_plus_zma.bin` | `SA_ZMAVCEPP` | `0x0200c401` | 198 916 |
| `sa_avcd_performance_zma.bin` | `SA_ZM_AVCDP` | — | 38 660 |
| `sa_avcd_compatible_zma.bin` | `SA_ZM_AVCDC` | — | 55 940 |

Różnica między enkoderami to **jeden bajt ID** (`c0`/`c1`/`c4`) przy prawie identycznym
rozmiarze — czyli trzy warianty tej samej maszyny stanów o różnym bilansie
jakość/obciążenie DSP.

### ⚠️ Czego NIE ustaliłem (i błąd, który popełniłem po drodze)

Chciałem sprawdzić, którego wariantu używa A6000, szukając ID `0x0200c001` w `av-cam.bin`.
Wyszły 3 trafienia i prawie ogłosiłem wniosek „A6000 używa tylko `performance`,
`quality` i `performance_plus` są martwe". **To był fałszywy trop.** Po zrzuceniu
kontekstu okazało się, że to alignment: w `av-cam.bin` stoi tablica 32-bitowych ID
`0x00c001be, 0x00c001c0, 0xfffffc02`, a mój wzorzec `01 c0 00 02` **przecina granicę
dwóch wpisów**. Liczba trafień 0 dla `quality`/`performance_plus` jest więc artefaktem,
nie dowodem.

**Stan faktyczny:** nie wiem statycznie, który wariant jest wybierany. Nazwy modułów
(`AVCEP`/`VCEQ`) **nie występują** jako stringi nigdzie poza samymi plikami `sabin/`,
więc `av-cam.bin` nie wybiera ich po nazwie — prawdopodobnie ładuje wszystkie
i adresuje funkcje przez wewnętrzną tablicę, a wybór wariantu zależy od trybu
nagrywania. **[H]**

Do rozstrzygnięcia potrzebny jest albo disassembly `av-cam.bin` wokół loadera,
albo **eksperyment na kamerze** (§5, Eksperyment 2).

---

## 3. 4K: ścieżka jest, brakuje dwóch tabel

`av-cam.bin` referuje **27 plików** z `/usr/sabin/`. **25 istnieje, 2 nie**:

| brakujący plik | do czego |
|---|---|
| `dcv_psf_table_movie_4k.bin` | tabela PSF dla filmu 4K |
| `dcv_psf_table_dualrec.bin` | tabela PSF dla dual-recording |

Jednocześnie **wszystkie** pliki „tap step" dla 4K **są dostarczone**:

```
spica_musashi_mov_4k_c_tap_step1/2.bin        ✅
spica_musashi_mov_4k_y_tap_step1/2.bin        ✅
spica_musashi_dualrec_4k_c_tap_step1/2.bin    ✅
spica_musashi_dualrec_4k_y_tap_step1/2.bin    ✅
```

Czyli w A6000:
1. **kod** 4K jest w `av-cam.bin` (skompilowany, wspólny dla platformy CXD90014),
2. **współczynniki DSP** dla 4K są na dysku,
3. **brakuje tylko tabel PSF** dla trybu 4K movie i dual-rec,
4. **brakuje układu Beaune** (CXD4236) — i to jest bariera nieusuwalna programowo.

Ciekawostka: `spica_musashi_mov_interlace_*` jest tylko dla jednego kroku (`step1`,
bez `step2`) — czyli ścieżka interlaced też jest niekompletna.

**Wniosek:** nawet gdybyśmy dorobili tabele PSF, enkoder 4K nie ma czym pracować
na A6000. Ale sam blok DSP-owy 4K (odczyt/scalanie z sensora) jest w firmware —
to może być interesujące dla **stills** (np. wieloklatkowa superrozdzielczość),
nie dla wideo.

---

## 4. Wtyczki scenariuszy — `/usr/scenario/`

### 4.1. Czym są **[S]**

35 plików `.so` — **prawdziwe ELF 32-bit ARM, nie stripped**, z eksportem
`scenario_run` i C++ symbolami szyny danych:

```
DataflowInfraReceiver::ReceiveASync / DataflowInfraMsg::GetMsg / DataflowInfraSender
osal_snd_msg, osal_rcv_msg_tmo, osal_snd_sync_direct, osal_valloc_msg_wait
Backup_read   ← scenariusze czytają wprost ustawienia z Backup.bin
```

Każdy `.so` zawiera własną nazwę jako string (np. `CAMERA_SCN_EXTERNAL_RAW_RECORD.so`).
Komunikacja: warstwa `osal_*` (abstrakcja OS) + komunikaty — czyli scenariusz nie
woła API bezpośrednio, tylko wysyła komendy do modułów AV.

### 4.2. Trzy rodziny

| prefiks | co robi | przykłady |
|---|---|---|
| `AVBB_SCN_*` | AV baseband: HDMI, audio, mic, panele EVF, nagrywanie | `START_VIDEO`, `START_HDMI`, `START_MIC`, `L_R_SETTING` |
| `CAMERA_SCN_*` | operacje kamery | `EE_START_STOP` (exposure), `MOVIE_REC_START`, `FACE_REC_DATA`, `SET_ZOOM_DRV`, `**EXTERNAL_RAW_RECORD**` |
| `MPR_SCN_*` | main processor / serwis | `FORMAT`, `GET_TOTAL_LOG`, `GET_CONTENT_COUNT`, `**EXEC_FACTORY_MODE**`, `EXEC_WIFI_TEST`, `FLASH_BACKUP_INIT`, `INSTALL_MAP_DEMOMOVIE` |

**Uwaga:** `MPR_SCN_EXEC_FACTORY_MODE`, `MPR_SCN_EXEC_WIFI_TEST`,
`MPR_SCN_FLASH_BACKUP_INIT` to **funkcje fabryczne obecne w firmware sprzedażowym**.
`MPR_SCN_INSTALL_MAP_DEMOMOVIE.so` ma 126 KB (vs 5–34 KB reszta) — podejrzanie dużo,
jak na coś, co „instaluje film demo"; wartość do sprawdzenia.

### 4.3. Tabela vs zawartość **[S]**

`lib/libsencore.so` („scenario core", 293 KB) zawiera **tabelę 27 nazw**.
Na dysku jest **35 plików**. Różnice:

**W tabeli, ale pliku brak (nie dostarczone dla A6000):**
```
AVBB_SCN_START_HDMI_SDI        ← SDI = wyjście broadcast, A6000 go nie ma
AVBB_SCN_START_HDMI_SDI_SUB
AVBB_SCN_STOP_HDMI_SDI
HMPR_SCN_GET_CONTENT_COUNT     ← rodzina HMPR (Handycam?)
HMPR_SCN_GET_TOTAL_LOG
```

To jest wzorzec, który powtarza się w całym firmware: **kod i tabele są nadzbiorem
dla całej platformy, pliki są podzbiorem per model, a sprzęt jest ostatecznym limitem.**
SDI nie da się włączyć, bo nie ma złącza.

### 4.4. Można je uruchamiać pojedynczo **[S]**

W `/usr/bin/` jest **`scenario.elf`** — gotowy harness:

```
<options> [scenario_name] [size]:[data] ...
    specified scenario name like below
        /usr/scenario/xxxx.so
```

Razem z `lib/libtestcmd_scn.so` (`scenario_run`, ścieżka `/usr/scenario/`) i
`bin/adjstctl.elf`. Ma obsługę wejścia/wyjścia binarnego:
`cmdline_get_ifile`, `cmdline_get_obfile`, `cmdline_read_bindata_to_stdout`,
`cmdline_write_bindata_to_obfile`.

**Praktycznie:** przez telnet można wywołać pojedynczy scenariusz i podać mu dane —
bez reflashu, bez appki. To najbardziej „programistyczny" interfejs do kamery,
jaki jest dostępny wprost z shella.

### 4.5. Własna wtyczka — tak, to możliwe **[H]**

Skoro `.so` to zwykły ELF z `scenario_run` + `osal_*`, można **napisać własny
scenariusz** i wrzucić go do `/usr/scenario/` (w reflashowanym `/usr`). To realna
zmiana kodu na poziomie sterowania AV — głębsza niż appka PMCA, płytsza niż patch
`av-cam.bin`. Wymaga: toolchaina ARM (EABI5, stary glibc 2.4) i dopięcia się do
protokołu `osal_*`. Ryzyko: zły scenariusz może zostawić blok AV w dziwnym stanie —
ale to stan runtime, nie flash, więc restart przywraca normalność.

---

## 5. Co z tym zrobić — eksperymenty uszeregowane

| # | eksperyment | warstwa | ryzyko | czego dowodzi |
|---|---|---|---|---|
| 1 | `scenario.elf /usr/scenario/MPR_SCN_GET_TOTAL_LOG.so` przez telnet | runtime | **zerowe** | że harness działa; wynik = logi/licznik migawki |
| 2 | podmiana `sa_avce_performance_zma.bin` na treść `quality` + CRC32 + reflash `/usr` | flash `/usr` | niskie (rollback = reflash) | który wariant jest używany i czy „quality" w ogóle działa na A6000 |
| 3 | dodanie `dcv_psf_table_movie_4k.bin` (skądś z innego modelu CXD90014) | flash `/usr` | niskie | czy AV zaczyna w ogóle próbować trybu 4K (najprawdopodobniej: błąd „no Beaune") |
| 4 | własny scenariusz `.so` wołający `Backup_read` | flash `/usr` | średnie | dostęp do 16 102 właściwości z poziomu AV |

Eksperyment 2 jest najlepszym stosunkiem wiedzy do ryzyka: **jeden plik, jedna
partycja, pełny rollback**, a rozstrzyga pytanie, którego nie dało się rozstrzygnąć
statycznie.

---

## 6. Otwarte pytania

1. **Który wariant enkodera wybiera A6000?** → eksperyment 2 albo disassembly loadera w `av-cam.bin`.
2. **Czy `quality`/`performance_plus` dają realnie lepszy obraz** na tym samym sprzęcie, czy tylko inny bilans CPU? Nie wiadomo.
3. **`BKID_SDF_QTBL_C` / `BKID_SDF_QTBL_Y` + `BKID_SDF_USE_STD_QTBL`** — w `av-cam.bin` jest
   obsługa **własnych tablic kwantyzacji JPEG** w Backup.bin. Jeśli da się je ustawić,
   to realna zmiana jakości JPEG w aparacie. **Wymaga mapowania nazwa BKID → ID**
   (poniżej).
4. **`ConvertQualityForBKID`** — jakość nagrywania jest zamieniana na właściwość Backup.
   Czyli „jakość" ma reprezentację w Backup.bin → może da się ustawić wartość spoza menu.
5. **Mapowanie BKID → ID**: w firmware jest **1058 różnych nazw `BKID_*`**
   (786 w `lib/libmprctrl.so`). Nie udało się jeszcze wyciągnąć pary (id, nazwa) —
   moja pierwsza próba (szukanie wskaźników na stringi) dała 1430 kandydatów, ale
   **żadnego ze znanych ID**, więc to był szum. Realna droga: disassembly
   `libmprctrl.so` wokół `Backup_read` / tabel deskryptorów. **To najcenniejszy
   pojedynczy trop w całym projekcie** — dałby nazwy dla tysięcy nieznanych ustawień.
