# 03 — A6000: sprzęt, firmware, dump, mapa NAND

## 3.1 Sprzęt i tożsamość

| | |
|---|---|
| Model | ILCE-6000 (A6000), premiera 2014-02-11 |
| SoC | **Sony CXD90014 „BIONZ X"** — 4× ARM Cortex-A5, krypt. „Musashi / Kojiro?" |
| Uwaga | **to NIE Qualcomm** — `CXD` to prefiks Sony; tak podaje `OpenMemories-Docs/hardware.rst` |
| USB (MSC) | `054c:07c4`; tryb updatera `054c:03e2` (do potwierdzenia `lsusb`) |
| OS wewnątrz | Linux + **µITRON RTOS** (AV) + Android 2.3.7 (API 10) jako userland appek |
| API PMCA | 2.4 |
| Model code w Backup.bin | `0x41030035` |
| Ostatni firmware | **3.21** |
| NAND | 463.75 MiB (`0x00000000`–`0x1BAC0000`), 15 partycji — patrz `07_FIRMWARE_3.21.md` |
| Matryca | 24.3 MP APS-C, wyjście max 1080p60 (brak 4K, brak S-Log) |

## 3.2 fwtool.py — rozpakowanie oficjalnego firmware (bez kamery)

To najbezpieczniejszy punkt startowy: **nie dotykasz aparatu**.

```bash
# 1. Pobierz oficjalny updater ze strony Sony (Update_ILCE6000V321.exe / .dmg)
# 2. Rozpakuj
fwtool unpack -f Update_ILCE6000V321.exe -o out/
```

Co wypluwa (dla CXD90014):
```
out/
├── config
├── backup/            # regiony backupu
├── 0700_part_image/   # nflasha3, nflasha5, nflasha7, nflasha15, nflasha16
├── 0800_appli/        # Android + obiektyw + ustawienia
└── updater.img        # VMLINUX.BIN, INITRD.IMG, busybox  ← firmware aktualizatora
```

Obsługiwane kryptery (z `fwtool.py/README.md`): `CXD90045`, `CXD90014`, `CXD4132`,
`CXD4120`, `CXD4115`, `CXD4105/MB8AC102`, plus formaty "Msfirm", DSLR, "ASH".
Input może być też dumpem z `dd if=/dev/nflasha`.

⚠️ Sony serwuje updatery z 403 na `curl` — linki CDN trzeba odzyskać z Wayback
(tak twierdzi CliffVale; nie sprawdzone).

## 3.3 Dump NAND z kamery (updatershell)

```bash
pmca-console updatershell -m ILCE-6000
# >>> NATYCHMIAST naciśnij OK na ekranie kamery ("Reset device OK")
# w shellu:
pull /dev/nflasha    nflasha      # ~483 MB, kilka minut
pull /dev/bootloader boot1        # 96 KB
quit
```

**Kluczowa pułapka:** ekran "Reset device OK" to NIE factory reset, tylko zgoda na
wejście w tryb aktualizacji. Bez fizycznego kliknięcia OK shell wisi i kończy się
`Operation timed out` po ~5 min. To najczęstszy powód "nie działa".

Po `quit` kamera wraca do MSC, nic nie zostało zapisane.

## 3.4 Mapa NAND

**Nie używaj mapy z CliffVale** — jest zmieszana z rozmiarami obrazów z firmware
i zawiera błędy w wierszach „gap"/"trailing" (`06_CLIFFVALE_OCENA.md` §3).

Autorytatywna tablica partycji jest **w samym firmware**:
`fw-3.21/fw/firmware.tar_unpacked/0300_partconf/partinf.conf` (+ `0100_config/mount.conf`).
Pełna tabela 15 partycji z offsetami, rozmiarami i mount pointami: `07_FIRMWARE_3.21.md` §7.2.

Skrót tego, co najważniejsze:

| dev | offset | rozmiar | rola |
|---|---|---|---|
| nflasha2 | `0x00640000` | 13 MiB | `/setting` ← **Backup.bin** |
| nflasha3 | `0x01340000` | 30 MiB | `/system` (Main) |
| nflasha5 | `0x03B40000` | 60 MiB | `/wbi` (Warm Boot Image) |
| nflasha7 | `0x07C40000` | 4 MiB | `/rootfs` |
| nflasha15 | `0x08B40000` | 100 MiB | `/usr` (cramfs — system) |
| nflasha16 | `0x0EF40000` | 82.75 MiB | `/android/system` |
| nflasha17 | `0x14200000` | 99.75 MiB | `/android/data` (FAT16) |
| nflasha18 | `0x1A5C0000` | 20 MiB | `/lens` |
| nflasha23 | `0x1B9C0000` | 1 MiB | `/PMBP` |

Regiony, które w dumpie wyglądają jak „puste 0xFF", to najczęściej **prawdziwe
partycje, których firmware nie wysyła** (nflasha4 MPR backup, nflasha6 Jiritsu,
nflasha10 `/tmp`, nflasha11 `/log`) — nie „nieużywane miejsce".

## 3.5 Co jest w Androidowym `/data`

To najbardziej wartościowa część dumpu — bo to **stan runtime**, a nie firmware:

```
/data/
├── APP/      # 5 APK-ów: OpenMemories Tweak, AppStore, FocusBracket,
│             #            BetterManual, TimeLapse
├── BACKUP/   # BK1.BAK, BK2.BAK (1.3 MB) — ALE to backupy pakietów Androida,
│             #            NIE backup ustawień kamery (patrz niżej)
├── LIB/      # natywne biblioteki per-app + usługi com.sony.scalar.*
├── MISC/WIFI/   # wpa_supplicant configs (WPS / Wi-Fi Direct)
├── MISC/DHCP/   # dnsmasq, dhcpcd leases
├── SYSTEM/BATTER~1BIN  # kalibracja baterii
├── DALVIK*/     # cache dex
└── PROPERTY/    # persist.*
```

### Ważna pułapka: shutter count
`BK1.BAK`/`BK2.BAK` w dumpie **nie zawierają licznika migawki** — to backupy appek.
Prawdziwy backup ustawień idzie przez komendę USB **`BKDA`**, czyli:
`pmca-console backup` + fizyczne OK na kamerze.

Alternatywnie shutter count jest w EXIF ARW jako `ImageCount`.

## 3.6 Region backupu i "japońskość"

`Backup.bin` ma pole `region` @0xc0. Od niego zależy, które języki są dopuszczone.
Wartości z kodu: `ALLLANG`, `AP2`, `AU2`, `CA2`, `CE`, `CE3`, `CE7`, `CEC`, `CEH`,
`CN1`, `CN2`, `E32`, `E33`, `E37`, `E38`, `EA8`, `HK1`, `IN5`, `J1`, `JE3`, `KR2`,
`RU2`, `RU3`, `TW6`, `U2`, `UC2`.

- `J1` = tylko japoński, protection tylko do włączenia (nie wyłączenia)
- `ALLLANG` = wszystkie 35 slotów na `1`

## 3.7 Czego A6000 NIE ma (żeby nie tracić czasu)

- 4K (max 1080p60), brak S-Log2/3, brak wbudowanego intervalometru
- brak zasilania po USB podczas pracy → tylko dummy battery NP-FW50 / AC-PW20
- brak czystego HDMI z menu (A6400 to ma, A6000 nie) → appka `dired/PMCA-HDMICam`
- brak wbudowanego GPS (Sony nigdy nie wypuścił modułu dla tej linii)
