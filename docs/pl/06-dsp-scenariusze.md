# 06 — Programy DSP AV i wtyczki scenariuszy

W `/usr` są dwa niezależne mechanizmy rozszerzeń:

- **`sabin/`** — 44 programy dla układu „SA DSP" + 24 tabele danych
- **`scenario/`** — 35 wtyczek (`.so`) sterujących operacjami AV

Oba to zwykłe pliki w obrazie `nflasha15` (`/usr`), więc oba da się podmienić,
reflashingując tę partycję.

## 1. `sabin/` — programy DSP

68 plików. 44 to programy w kontenerze Sony z magic `aa 0a 13 91`; 24 to dane
(tabele PSF, zestawy współczynników „tap step", parametry jądra).

### Format kontenera

```
0x00  magic      aa 0a 13 91
0x04  wersja     04 00 00 02
0x08  ID wariantu  np. 0x0200c001
0x0c  klasa      np. 0x010083
0x14  nazwa      "SA_ZM_AVCEP…"
```

Nazwa koduje silnik + moduł: `SA_` + silnik (`ZM` = Zima, `MN` = Minna) + moduł
(`AVCEP`, `AVCEQ`, `SPICA`, …).

### Klasy

| Klasa | Zawartość |
|---|---|
| `0x010083` | **rodzina AVC: 3 enkodery + 2 dekodery** |
| `0x010002` | kodeki audio (AAC, AC3, Dolby 5.1, LPCM) + JPEG |
| `0x01000f` | narzędzia AV: **`SA_FRC2`** (konwersja klatek), CECIL, SHAPE, TBOX |
| `0x010001`/`0x010004`/`0x010008` | redukcja szumów (LFNR) Zima / Minna 0 / Minna 1 + startupy |
| `0x03000d` | **SPICA** — główny blok przetwarzania obrazu |
| `0x01000c` | `SABT` — Bayes tracker (AF) |

Uwaga: `sa_integenc.bin` (394 KB) to enkoder **audio** (klasa `0x010002`), nie
„zintegrowany enkoder wideo" — łatwe do błędnego odczytania.

### Rodzina AVC

| Plik | Nazwa wewnętrzna | ID |
|---|---|---|
| `sa_avce_performance_zma.bin` | `SA_ZM_AVCEP` | `0x0200c001` |
| `sa_avce_quality_zma.bin` | `SA_ZM_AVCEQ` | `0x0200c101` |
| `sa_avce_performance_plus_zma.bin` | `SA_ZMAVCEPP` | `0x0200c401` |
| `sa_avcd_performance_zma.bin` | `SA_ZM_AVCDP` | — |
| `sa_avcd_compatible_zma.bin` | `SA_ZM_AVCDC` | — |

Trzy warianty enkodera tej samej maszyny stanów, różniące się jednym bajtem ID i kilkoma
kilobajtami. **Którego wariantu używa A6000 — nie ustalono.** Firmware AV (`av-cam.bin`)
jest PIC i nie referuje nazw wariantów; naiwne szukanie ID w `av-cam.bin` daje fałszywe
trafienia, bo wzorzec przecina sąsiednie wpisy 32-bitowej tablicy. Potrzebny jest
porządny disassembly albo eksperyment z podmianą.

### 4K: ścieżka istnieje, brakuje dwóch tabel

`av-cam.bin` referuje 27 plików z `/usr/sabin/`. 25 istnieje. Brakuje:

```
dcv_psf_table_movie_4k.bin
dcv_psf_table_dualrec.bin
```

A jednak **wszystkie** zestawy „tap step" dla 4K są dostarczone
(`spica_musashi_mov_4k_{c,y}_tap_step*`, `dualrec_4k_*`). Czyli kod 4K jest
skompilowany i prawie uzbrojony — brakuje tabeli PSF dla trybu oraz, co krytyczne,
układu kodeka Beaune (patrz [08-modele-blizniacze.md](08-modele-blizniacze.md)).

Dla porównania A6300 dostarcza `dcv_psf_table_movie_4k.bin` i 10 dodatkowych programów
DSP (`sa_bayes_tracker_edge`, `sa_integdec`, `sa_motionshot`, `sa_nlg`, `sa_seg`,
`sa_zoom_nr`, …). Jego zbiór DSP jest nadzbiorem zbioru A6000.

## 2. `scenario/` — wtyczki

35 shared objects, ARM EABI5, nie stripped, każdy eksportuje `scenario_run`
i komunikuje się przez warstwę `osal_*` (klasy C++ `DataflowInfra*`). Część czyta
`Backup_read` bezpośrednio, czyli scenariusz może czytać ustawienia.

Trzy rodziny:

| Prefiks | Rola | Przykłady |
|---|---|---|
| `AVBB_SCN_*` | AV baseband: HDMI, audio, mikrofon, panele EVF, nagrywanie | `START_VIDEO`, `START_HDMI`, `START_MIC`, `L_R_SETTING` |
| `CAMERA_SCN_*` | operacje kamery | `EE_START_STOP`, `MOVIE_REC_START`, `FACE_REC_DATA`, `SET_ZOOM_DRV`, `EXTERNAL_RAW_RECORD` |
| `MPR_SCN_*` | main processor / serwis | `FORMAT`, `GET_TOTAL_LOG`, `GET_CONTENT_COUNT`, `**EXEC_FACTORY_MODE**`, `EXEC_WIFI_TEST`, `FLASH_BACKUP_INIT` |

Funkcje fabryczne (`EXEC_FACTORY_MODE`, `EXEC_WIFI_TEST`, `FLASH_BACKUP_INIT`) są obecne
w firmware sprzedażowym.

### Tabela a dostarczone pliki

`lib/libsencore.so` ma tabelę **27** nazw scenariuszy; dostarczonych jest **35** plików.
W tabeli, ale niedostarczone: `AVBB_SCN_*_HDMI_SDI*` (wyjście SDI — A6000 nie ma złącza)
oraz `HMPR_SCN_GET_TOTAL_LOG` / `GET_CONTENT_COUNT`.

Ten wzorzec powtarza się w całym firmware: **kod i tabele to nadzbiór platformy, pliki
to podzbiór per model, a sprzęt jest ostatecznym limitem.**

### Uruchamianie pojedynczego scenariusza

`/usr/bin/scenario.elf` to gotowy harness:

```
<options> [scenario_name] [size]:[data] ...
    specified scenario name like below
        /usr/scenario/xxxx.so
```

z helperami I/O binarnego (`cmdline_get_ifile`, `cmdline_read_bindata_to_stdout`,
`cmdline_write_bindata_to_obfile`). W połączeniu z root shellem (OpenMemories-Tweak
udostępnia telnet/adb) to najbardziej „programistyczny" interfejs do aparatu bez
reflashu.

### Własna wtyczka

Skoro scenariusz to zwykły ELF eksportujący `scenario_run` i mówiący po `osal_*`,
własną wtyczkę można wrzucić do `/usr/scenario/` w reflashowanym `/usr`. To realna
zmiana kodu na poziomie sterowania AV — głębsza niż APK, płytsza niż patch
`av-cam.bin` — i dotyka tylko stanu runtime, nie flashu.

## 3. Podzbiór startowy

`nflasha3/sabin/` (w `/system`) trzyma mały podzbiór ładowany przy starcie:
`idt_cam.bin`, `sa_dfdet.bin`, `ssboot.bin`, `ssboot_any.bin` — identyczny w A6000
i A6300.

## 4. Otwarte pozycje

- Który wariant enkodera AVC jest aktywny i czy `quality`/`performance_plus` poprawiłyby
  jakość obrazu na tym korpusie.
- Czy 5 dodatkowych bloków rejestrów i dodatkowe programy DSP z A6300 da się w ogóle
  wykorzystać bez układu Beaune.
- Nikt publicznie nie przeanalizował ani jednego programu `sabin`, choć istnieje
  specyfikacja procesora do Ghidry (`ma1co/SA-DSP`).
