# 04 — Magazyn ustawień: `Backup.bin`

Wszystkie ukryte ustawienia Sony leżą w jednym pliku na `nflasha2`
(`/setting/Backup.bin`). Aparat ma własne API do odczytu i zapisu tego pliku — właśnie
z niego korzysta *OpenMemories: Tweak*. Ten dokument opisuje format, znane ID oraz
offline'owy korpus 11 kompletnych plików dostarczanych w firmware.

## 1. Format pliku (rewizja `BK4`)

```
offset  pole
0x00    magic (int32)
0x04    cookie (int32)
0x08    writeComp (int32)
0x0c    revision      — "BK2" lub "BK4"            ← wersja formatu
0x10    numSubsystems
0x14    numProperties
0x18    dataOffset
0x1c    dataSize
0x20    checksum      (suma bajtów z pominięciem 0x20..0x23)
0x28    id1 (int32)   — flaga protection
0x3c    version (0x20)
0xc0    region (0x20) — np. "CX77500_ALLLANG", "CX77500_J1"
```

- `BK2` → wpisy tabeli mają `attr` jako **int8**
- `BK4` → `attr` jako **int16**
- ID właściwości = `subsystem << 16 | index`; bit 0 `attr` = read-only,
  bit 1 = chronione przed `Backup_protect`.

Parser: `pmca/backup/__init__.py` z Sony-PMCA-RE; CLI w `tools/backup.py`.

## 2. Korpus offline: 11 kompletnych plików per region

`0110_backup/SYSMUSASHI-DSLR/DM_UUD3/` (A6000) zawiera po jednym pliku na region,
każdy 852 647 bajtów:

```
CX77500_ALLLANG  CX77500_E38  CX77500_J1  CX77500_KR2  CX77500_UC2
CX77501_ALLLANG  CX77501_AP2  CX77501_CEC  CX77501_CN2  CX77501_IN5  CX77501_JE3
```

Zweryfikowane parserem: `BK4`, `numSubsystems=403`, `numProperties=17167`
(faktycznie istnieje 16 102), `dataOffset=0x19ce0`, `dataSize=0xb65c7`.

**Czyli każde ID i jego wartość domyślna są dostępne bez aparatu.** Pliki regionów
różnią się zaledwie **37–46 właściwościami** (ALLLANG vs J1: 37), więc „regionalność"
to garść ID.

Przykładowe wartości z `CX77500_ALLLANG.bin`:

```
0x003e0005 model_name      = "ILCE-6000"
0x003c0373 rec_limit H     = 0x00
0x003c0374 rec_limit M     = 0x1d      → 0h 29m 50s
0x003c0375 rec_limit S     = 0x32
0x010d008f..b1 language    = 0x01 (włączony) we wszystkich 35 slotach
0x01070148 pal_ntsc        = 0x00
```

## 3. Znane ID

Z `ma1co/OpenMemories-Platform/api/backup.cpp`:

| ID | Rozmiar | Znaczenie |
|---|---|---|
| `0x003c0373` / `74` / `75` | 1 B każdy | limit nagrania H / M / S |
| `0x003c04b6` | 2 B | limit 4K (RX100M4), sekundy |
| `0x003e0005` | 16 B | nazwa modelu |
| `0x00e70000` | 5 B | model code |
| `0x00e70003` | 4 B | numer seryjny |
| `0x01070148` | 1 B | selektor PAL/NTSC |
| `0x010d008f` … `0x010d00b1` | 1 B × 35 | sloty językowe (1 = on, 2 = off) |
| `0x01640001` | 1 B | USB app installer |
| `0x01660024` | 8 B | wersja platformy Android |

Z społeczności (zweryfikowane diffem menu — `voxivoid/recipe-lab-sony-pmca`):

| Ustawienie | ID |
|---|---|
| Creative Style | `0x01070175` (1 standard, 2 vivid, 3 neutral, 6 mono, 14 sepia) |
| Contrast / Saturation / Sharpness | `0x01070178` / `0x01070187` / `0x0107018a` |
| Picture Profile | `0x0107031c` |
| WB mode / Kelvin / A-B / G-M | `0x01070019` / `0x01070018` / `0x01070017` / `0x01070016` |
| WB kopie per-tryb | AWB `0x0107067f`/`0x0107067e`, temp. barwowa `0x01070683`/`0x01070682` |
| Picture Effect | `0x010706f1` (+ `0x010709d8`, `0x010706f3`, `0x010706ee`, `0x010706ef`) |
| Exposure bias | `0x010700b8` + kopia `0x01070c7f` |
| DRO | `0x01070104` + poziom `0x01070775` |
| Quality: format / JPEG | `0x01070013` (+`0x01070aa9`) / `0x01070014` (+`0x01070aaa`) |
| **Overlay HDMI (clean HDMI)** | **`0x01070a47`** — `01` = overlay włączony, `00` = czysty obraz |

ID clean-HDMI pochodzi z opisu społeczności dla A5000 (`bk.elf w 0x01070a47 00`).
Sprawdzone lokalnie: właściwość istnieje w domyślnych A6000, `attr=0x40`, rozmiar 1,
wartość `01`.

## 4. Protection

`is_enabled() == !Backup_get_protection()`, a flaga protection to `id1` pod 0x28,
zapisywana dedykowaną komendą aparatu (`backup_senser_cmd_ID1`), nie zwykłą ścieżką
zapisu właściwości.

Warte zapamiętania (ze źródeł platformy):

- Na Androidzie 2 katalog `/setting` musi istnieć, żeby flaga się utrwaliła;
  OpenMemories tworzy go, zapisuje `Backup.bin`, po czym katalog usuwa.
- Region `J1` (Japonia) pozwala protection tylko *włączyć*. Obejście: chwilowa
  podmiana pola region na `""` przez `Backup_protect`, zmiana flagi, przywrócenie regionu.

## 5. Ustawianie regionu — oficjalnym updaterem

`endupdate.sh` zawiera:

```sh
if [ -e /tmp_updater/updater/update/backup/*/*/*.bin ]; then
    echo "Backup.bin overwrite OK"
    cp /tmp_updater/updater/update/backup/*/*/*.bin /setting/Backup.bin
fi
```

Czyli domyślne region/języki są aplikowane **w momencie flashowania z pakietu**.
Przepakowanie aktualizacji z `CX77500_ALLLANG.bin` w środku to „fabryczny" sposób na
wszystkie języki — bez hackowania protection.

## 6. Narzędzie

```bash
python tools/backup.py info  <plik.bin>                  # nagłówek: region, liczby, checksum
python tools/backup.py list  <plik.bin> [--min-size N]   # wszystkie właściwości
python tools/backup.py get   <plik.bin> 0x010d008f       # jedna właściwość
python tools/backup.py known <plik.bin>                  # tabela z góry
python tools/backup.py diff  <a.bin> <b.bin>             # np. ALLLANG vs J1
```

## 7. Problem otwarty

Firmware zawiera **1058 różnych nazw `BKID_*`** (786 w `libmprctrl.so`), czyli nazwy
właściwości *są* w binariach — ale publiczne mapowanie nazwa → numeryczne ID nie
istnieje. Wydobycie go dałoby nazwy tysiącom z 16 102 właściwości. To najcenniejsza
otwarta pozycja; patrz [10-pytania-otwarte.md](10-pytania-otwarte.md).
