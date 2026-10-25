# 02 — Struktura firmware

Autorytatywna tablica partycji jest **dostarczana w aktualizacji firmware**,
w `0300_partconf/partinf.conf` (wygenerowana przez Sony 2013-08-01). Odpowiada temu,
co kernel widzi jako `/dev/nflashaN`.

## Tablica partycji

| Urządzenie | Start | Rozmiar | Mount | FS | Rola |
|---|---|---|---|---|---|
| — | `0x00000000` | 256 KiB | — | — | bootloader |
| nflasha1 | `0x00040000` | 6 MiB | — | vfat | SYSTEM (Updater) |
| **nflasha2** | `0x00640000` | 13 MiB | **`/setting`** | vfat | **ustawienia — tu leży `Backup.bin`** |
| nflasha3 | `0x01340000` | 30 MiB | `/system` | raw | **potok AV (`av-cam.bin`)** |
| nflasha4 | `0x03140000` | 10 MiB | — | raw | backup MPR |
| nflasha5 | `0x03B40000` | 60 MiB | `/wbi` | wbi | Warm Boot Image |
| nflasha6 | `0x07740000` | 5 MiB | — | vfat | „Jiritsu" |
| nflasha7 | `0x07C40000` | 4 MiB | `/rootfs` | raw | rootfs |
| nflasha10 | `0x08040000` | 5 MiB | `/tmp` | vfat | obszar roboczy (**trwały flash, nie tmpfs**) |
| nflasha11 | `0x08540000` | 6 MiB | `/log` | vfat | logi |
| nflasha15 | `0x08B40000` | 100 MiB | `/usr` | raw | **userland Linuksa (cramfs)** |
| nflasha16 | `0x0EF40000` | 82,75 MiB | `/android/system` | raw | system Androida |
| **nflasha17** | `0x14200000` | 99,75 MiB | **`/android/data`** | vfat | **dane Androida — FAT16, APKi** |
| nflasha18 | `0x1A5C0000` | 20 MiB | `/lens` | vfat | dane obiektywów |
| nflasha23 | `0x1B9C0000` | 1 MiB | `/PMBP` | prfile | PMBP |

Koniec NAND: **`0x1BAC0000` = 463,75 MiB**. Partycje o rozmiarze 0: nflasha8, 9, 12,
13, 14, 19–22, 24–30.

## Co realnie nadpisuje aktualizacja

`0701_part_image_sum/part_image.sum` wymienia dokładnie **pięć** obrazów:

| Obraz | bajty | CRC32 |
|---|---|---|
| `nflasha3` (`/system`) | 11 489 040 | `0c047870` |
| `nflasha5` (`/wbi`) | 42 293 120 | `9cb10112` |
| `nflasha7` (`/rootfs`) | 3 324 495 | `b969856d` |
| `nflasha15` (`/usr`) | 84 042 977 | `df198ecd` |
| `nflasha16` (`/android/system`) | 59 013 103 | `c77af80c` |

`nflasha17` (dane) i `nflasha2` (ustawienia) **nie** są w aktualizacji — dane
i ustawienia przeżywają update. Ustawienia są obsługiwane osobno: `endupdate.sh`
kopiuje `backup/*/*/*.bin` z pakietu do `/setting/Backup.bin`, czyli domyślne
region/języki są wybierane **w momencie flashowania**.

Obrazy są *mniejsze* niż partycje, w których leżą (np. 11,5 MB obrazu w partycji 30 MB).
Reszta partycji czyta się jako `0xFF` — dlatego naiwne mapy zrzutów pokazują „puste
dziury", które w rzeczywistości są partycjami (nflasha4, 6, 10, 11).

## Mechanika aktualizacji (z `updater.img`)

`updater.img_unpacked/config/config.xml` opisuje update jako listę kroków:

| Krok | Skrypt | Co robi |
|---|---|---|
| config | `us_crc32sum.sh` | CRC32 plików konfiguracji |
| config | **`chkfirm.sh`** | **tylko** sprawdza typ LSI main/sub przez power IC |
| config | `edit_mount.sh`, `keep_big_backup.sh` | dopisuje `mount1.conf`, zachowuje `psd.bin` |
| partconf | **`chknandcapa.elf`** | weryfikuje pojemność NAND względem `partinf.conf` |
| partconf | `us_mkfs.sh` | tworzy systemy plików |
| part_image | `us_crc32sum.sh` | CRC32 pięciu obrazów partycji |
| darwin | `us_darwin_firm.sh` | **flashuje power IC** |
| ca | `us_ca_firm.sh` | flashuje układ CA |
| backup | `us_crc32sum_backup.sh` | CRC32 `Backup.bin` |
| loader | **`loader_writer.sh`** → `pformat_normal/safe.elf` | **przepisuje bootloader**, manifest MD5 |

Nie ma kontroli wersji, która blokowałaby downgrade albo zmodyfikowany obraz.

## Wnętrze rozpakowanego drzewa

```
config.yaml                     crypter CXD90014, model 0x41030035, wersja 3.21
firmware.fdat / firmware.tar    payload (212 MB)
firmware.tar_unpacked/
  0100_config/                 mount.conf, big_backup.conf
  0110_backup/                 ← 11 kompletnych Backup.bin, po jednym na region
  0300_partconf/partinf.conf   ← tablica partycji z góry
  0640_darwin/darwin_core.bin  firmware power IC (157 KB, Cortex-M3)
  0700_part_image/dev/         pięć obrazów + rozpakowana zawartość
  0800_appli/                  Android + pliki obiektywów + domyślne ustawienia
updater.img_unpacked/          OS updatera: bin/, bodylib/, config/, usr/
```

`0700_part_image/dev/nflasha15_unpacked_unpacked/` to root Linuksa aparatu:

```
bin/  dfe/  kmod/  lib/  local/  sabin/  sbin/  scenario/  share/  tool/  wlan/
```

Dwa z tych katalogów mają osobne dokumenty: `dfe/` w [05-dfe.md](05-dfe.md),
`sabin/` + `scenario/` w [06-dsp-scenariusze.md](06-dsp-scenariusze.md).
