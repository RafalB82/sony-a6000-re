# 07 — Co jest w firmware 3.21 (rozpakowane lokalnie)

To jest **najlepsze źródło prawdy o A6000, jakie mamy** — i nie wymaga kamery.
Wszystko poniżej pochodzi z plików Sony, nie z blogów.

## 7.1 Jak to odtworzyć

```bash
# venv (wymaga pycryptodomex, pyyaml)
cd /home/rafal/sony/fw-3.21
./venv/bin/python /home/rafal/sony/fwtool.py/fwtool.py unpack \
  -f Update_ILCE6000V321/Resources/FirmwareUpdater.app/Contents/Resources/FirmwareData_ILCE6000V321.dat \
  -o fw
```

Weryfikacja źródła (zrobione):
- DMG `sha256 844349ff7edddc294c0fddd90a454848eeda8987b6bf043c9757982b3a42ba3e`
- `FirmwareData_ILCE6000V321.dat` `sha256 29aef21ab9b5c2e98388974ac9749c2cbfb1815273b444e62f2e41398aa8892f`

Struktura wyniku:
```
fw/
├── config.yaml
├── firmware.fdat            # 212 MB
├── firmware.tar             # 212 MB
├── firmware.tar_unpacked/
│   ├── 0100_config/         # mount.conf, big_backup.conf   ← MAPOWANIE PARTYCJI
│   ├── 0110_backup/         # 11× Backup.bin per region     ← JACKPOT (7.4)
│   ├── 0300_partconf/       # partinf.conf                  ← TABLICA PARTYCJI
│   ├── 0600_gps/
│   ├── 0630_ca/
│   ├── 0640_darwin/         # darwin_core.bin (157 KB) — firmware power ICU
│   ├── 0650_prfile/
│   ├── 0700_part_image/     # nflasha3/5/7/15/16 + obrazy rozpakowane
│   └── 0800_appli/          # Android + lens + setting
└── updater.img_unpacked/    # bin, bodylib, config, usr — OS aktualizatora
```

## 7.2 Prawdziwa tablica partycji (`0300_partconf/partinf.conf`)

Wygenerowana przez Sony 2013-08-01. To samo, co widzi kernel jako `/dev/nflashaN`.

| dev | start | rozmiar | MountPoint | FS | Grupa / rola |
|---|---|---|---|---|---|
| — | `0x00000000` | 256 KiB | — | — | bootloader |
| nflasha1 | `0x00040000` | 6 MiB | — | vfat | SYSTEM (Updater) |
| **nflasha2** | `0x00640000` | 13 MiB | **`/setting`** | vfat | SYSTEM (Setting) ← **tu jest `Backup.bin`** |
| nflasha3 | `0x01340000` | 30 MiB | `/system` | raw | SYSTEM (Main) |
| nflasha4 | `0x03140000` | 10 MiB | — | raw | MPR Flash Backup |
| nflasha5 | `0x03B40000` | 60 MiB | `/wbi` | wbi | Warm Boot Image |
| nflasha6 | `0x07740000` | 5 MiB | — | vfat | Jiritsu |
| nflasha7 | `0x07C40000` | 4 MiB | `/rootfs` | raw | Rootfs |
| nflasha10 | `0x08040000` | 5 MiB | `/tmp` | vfat | Work |
| nflasha11 | `0x08540000` | 6 MiB | `/log` | vfat | Log |
| nflasha15 | `0x08B40000` | 100 MiB | `/usr` | raw | User (cramfs) |
| nflasha16 | `0x0EF40000` | 82.75 MiB | `/android/system` | raw | Android (system) |
| **nflasha17** | `0x14200000` | **99.75 MiB** | **`/android/data`** | **vfat** | **Android (data)** ← FAT16 z APK-ami |
| nflasha18 | `0x1A5C0000` | 20 MiB | `/lens` | vfat | LensData |
| nflasha23 | `0x1B9C0000` | 1 MiB | `/PMBP` | prfile | PMBP |
| **koniec** | **`0x1BAC0000`** | | | | **= 463.75 MiB ≈ 486 MB** |

Wszystko jest **ciągłe, bez dziur** — 0x…0410FFFF itd. składa się co do bajtu.
Partyce nflasha8/9/12/13/14/19–22/24–30 mają rozmiar 0.

**Wniosek dla RE:** to jest ostateczna odpowiedź na pytanie „co jest na NAND".
Mapa z CliffVale podaje poprawne starty, ale myli rozmiary partycji z rozmiarami
obrazów w aktualizacji (patrz `06_CLIFFVALE_OCENA.md` §3).

## 7.3 `0100_config/mount.conf` — co gdzie mountuje kernel

```
/dev/nflasha2  /setting        vfat
/dev/nflasha3  /system         raw
/dev/nflasha5  /wbi            wbi
/dev/nflasha7  /rootfs         raw
/dev/nflasha10 /tmp            vfat
/dev/nflasha11 /log            vfat
/dev/nflasha15 /usr            raw
/dev/nflasha16 /android/system raw
/dev/nflasha17 /android/data   vfat   (ClusterSize 16384)
/dev/nflasha18 /lens           vfat
/dev/nflasha23 /PMBP           prfile
```

To domyka wątek z kodu: `updaterbody.cpp` robi `mount_vfat("/dev/nflasha2", "/setting")`,
a `ProtectionTweak` grzebie w `/setting/Backup.bin`. **Backup.bin leży na nflasha2.**

`0100_config/big_backup.conf` → `/setting/psd.bin` (osobny duży backup ustawień).

## 7.4 Najważniejsze odkrycie: 11 gotowych `Backup.bin` (per region)

`0110_backup/SYSMUSASHI-DSLR/DM_UUD3/` zawiera **11 plików po 852 647 B**:

```
CX77500_ALLLANG.bin   CX77501_ALLLANG.bin
CX77500_E38.bin       CX77501_AP2.bin
CX77500_J1.bin        CX77501_CEC.bin
CX77500_KR2.bin       CX77501_CN2.bin
CX77500_UC2.bin       CX77501_IN5.bin
                      CX77501_JE3.bin
```

Są to **prawdziwe pliki Backup.bin w wersji BK4** (magic `BK4` @0x0c, region-string @0xc0,
np. `CX77500_ALLLANG`). Zweryfikowane parserem z Sony-PMCA-RE (`checksum` OK):

```
revision BK4, region 'CX77500_ALLLANG', id1=0
numSubsystems=403, numProperties=17167, istniejących=16102
dataOffset=0x19ce0, dataSize=0xb65c7
```

### Dlaczego to jest duże
1. **Pełna lista 16 102 właściwości z prawdziwymi ID i rozmiarami** — bez kamery.
   To zamyka największe pytanie otwarte z `05_DALEJ.md` („co jest w pozostałych ~15 000 wpisów").
2. **Wartości domyślne** dla każdego regionu → punkt odniesienia do diffowania.
3. **Można porównywać regiony**: ALLLANG vs J1 różnią się zaledwie **37 właściwościami**
   (z 16 102!), ALLLANG vs UC2 — **46**. Czyli cała „regionowość" to garść ID.

Przykład potwierdzający, że rozumiemy format (ALLLANG):
```
0x003e0005 model_name    = "ILCE-6000"
0x003c0373/74/75 rec_limit = {0x00, 0x1d, 0x32} = 0h 29m 50s   ← dokładnie off_value z Tweak
0x010d008f..b1  language slots = wszystkie 0x01 (enabled)
0x00e70000 model_code    = 00 00 06 99 05
0x01070148 pal_ntsc_selector = 0x00
```
W J1 wszystkie sloty językowe poza jednym = `0x02` (disabled) — zgodne z `langs_j1[]`
w `OpenMemories-Platform`.

Nowe, nieznane ID warte zbadania (różnią się między regionami):
`0x01070b2d`, `0x01070b2e`, `0x01070b2f` — w J1 zawierają ASCII typu
`"007-AC0002"`, `"D14-0016001"` (kody wersji sprzętu/firmware dla rynku japońskiego),
w ALLLANG — `"0x00"`. Oraz `0x003c03dd` (diff ALLLANG vs UC2).

### Narzędzie
`tools/backup.py` (napisane tutaj, korzysta z parsera Sony-PMCA-RE):

```bash
B=fw-3.21/fw/firmware.tar_unpacked/0110_backup/SYSMUSASHI-DSLR/DM_UUD3
fw-3.21/venv/bin/python tools/backup.py info  $B/CX77500_ALLLANG.bin
fw-3.21/venv/bin/python tools/backup.py known $B/CX77500_ALLLANG.bin
fw-3.21/venv/bin/python tools/backup.py list  $B/CX77500_ALLLANG.bin --min-size 8
fw-3.21/venv/bin/python tools/backup.py get   $B/CX77500_J1.bin 0x010d008f
fw-3.21/venv/bin/python tools/backup.py diff  $B/CX77500_ALLLANG.bin $B/CX77500_J1.bin
```

## 7.5 Pozostałe katalogi

- **`0640_darwin/darwin_core.bin`** (157 KB) — firmware power ICU **MB9AF004BGL „Darwin"**
  (ARM Cortex-M3), zarządza startem BIONZ i RTC. Osobny cel RE gdyby trzeba było
  zrozumieć sekwencję bootowania / watchdog.
- **`0700_part_image/dev/`** — obrazy partycji: `nflasha3` (initrd), `nflasha5` (WBI),
  `nflasha7` (rootfs), `nflasha15` (cramfs `/usr` — tu siedzi system), `nflasha16`
  (Android system). fwtool dodatkowo je rozpakowuje (`*_unpacked`).
- **`updater.img_unpacked/`** — OS aktualizatora (`bin/ramdisk.img`, `bin/udtrbody.bin`,
  busybox): dokładnie to, co ląduje w kamerze w trybie updatera. Tu szukać odpowiedzi
  „co `updatershell` może, a czego nie".
- **`0800_appli/`** — Android + dane obiektywu + `setting/init_bk.bak`.

## 7.6 Sprzęt A6000 (źródło: OpenMemories-Docs/hardware.rst, klasa A)

| Rola | Układ | Uwagi |
|---|---|---|
| SoC (BIONZ X) | **CXD90014** | 4× ARM Cortex-A5, krypt. „Musashi / Kojiro?", X-2013 |
| DFE (front-end) | CXD90027 „Regulus" | między sensor a BIONZ |
| Power IC | **MB9AF004BGL „Darwin"** | ARM Cortex-M3, start BIONZ + RTC |
| Stabilizacja | R2J30503LG „Bonobo" | Renesas H8 |
| Kodowanie | brak (samo CXD90014) | → max 1080p60; z „Beaune" byłoby 4K |
| Pamięć | NAND + DRAM w MCP/PoP na SoC | dlatego nie widać ich na zdjęciach z rozbiórki |

CXD90014 uruchamia **Linux + µITRON RTOS** (µITRON obsługuje AV/czas rzeczywisty).
Warstwa Android (2.3.7, API 10) to userland appek PMCA siedzący na `/android/*`
(nflasha16 + nflasha17). Czyli „aparat z Androidem w środku" to skrót myślowy —
realnie to Linux + RTOS + Androidowy userland.
