# 08 — Modele bliźniacze i sprawa 4K

A6000 nie jest sam: **66 modeli** w `fwtool.py/devices.yml` stoi na tej samej platformie
CXD90014. Porównanie z najbliższym krewnym, A6300, rozstrzyga sprawę 4K na podstawie
schematów Sony.

## 1. Rodzina (wybór)

| Model | Model code | API PMCA | 4K? |
|---|---|---|---|
| **ILCE-6000** | `0x41030035` | 2.4 | ❌ |
| ILCE-5100 | `0x42030036` | 2.7 | ❌ |
| ILCE-5000 | `0x41030012` | 2.3 | ❌ |
| **ILCE-6300** | `0x61030034` | 2.15 | ✅ |
| ILCE-6500 | `0x61030035` | 2.17 | ✅ |
| ILCE-7 / 7R / 7S | `0x41030013` / `0x41030034` / `0x42030032` | 2.3 / 2.3 / 2.6 | ❌ |
| ILCE-7M2 / 7RM2 / 7SM2 | `0x51030031` / `0x51030034` / `0x51030041` | 2.10 / 2.14 / 2.14 | RM2 ✅ |
| DSC-RX100M3 / M4 / M5 | `0x41020022` / `0x51020034` / `0x61020023` | 2.6 / 2.14 / 2.16 | M4/M5 ✅ |
| DSC-RX10M2 / M3, RX1RM2, RX0 | `0x51020038` / `0x61020032` / `0x51020035` / `0x61020010` | 2.14 / 2.15 / 2.14 | część ✅ |

Ten sam SoC, różne matryce i różne układy pomocnicze — odcinane per model przez
konfigurację i przez to, co fizycznie przylutowano.

## 2. A6000 vs A6300, ze schematów Sony

| | A6000 | A6300 |
|---|---|---|
| pakiet SoC | `MHZ4G8G01A` | `MCZ4G8G21A` |
| **DFE `IC6200`** | **`CXD90027GF`** | **`CXD90027GF`** — identyczny |
| **Kodek `IC9012`** | **brak** | **`CXD4236-1GG`** — „Beaune" |
| Power IC `IC5700` | `MB9AF004BGL` | `MB9AF004BGL` |
| Matryca | 24,3 MP | 24,2 MP, miedź (nowy układ) |
| `/usr/dfe/dfe.bin` | ✅ 64 KiB | ❌ (firmware front-endu wbudowany w `av-cam.bin` pod `0xC1EB00`) |
| `/usr/beaune/{ipl,firmware}.bin` | ❌ | ✅ 18 KB + 2,9 MB |
| `beaune_drv.ko` | ❌ | ✅ |
| Programy DSP w `/usr/sabin` | 69 plików | 79 plików (A6000 ⊂ A6300) |
| Offsety partycji | nflasha15 @ `0x08B40000` | nflasha15 @ `0x08640000` |

**4K na A6000 jest niemożliwe, bo układ kodeka Beaune nie jest na płycie.**
Trzy niezależne potwierdzenia:

1. Schemat Sony: `CXD4236` występuje 14× w manualu A6300, 0× w manualu A6000.
2. Firmware: `/usr/beaune/` i `beaune_drv.ko` istnieją tylko w A6300.
3. Dokumentacja: notatki OpenMemories podają „CXD90014 + Beaune → 4K (30 fps)".

Firmware AV A6000 nadal zawiera kod 4K (patrz [06-dsp-scenariusze.md](06-dsp-scenariusze.md))
— po prostu nie ma czym kodować.

## 3. Wspólne matryce — założenie obalone

`dcv_psf_table_movie.bin` i `dcv_psf_table_still.bin` są **bit w bit identyczne**
w A6000 i A6300 i oba oznaczone `IMX210` — mimo że matryca A6300 to inny układ. Czyli
tabele PSF są tabelami *przetwarzania*, nie kalibracją per-sensor. A6300 dodatkowo
dostarcza `dcv_psf_table_movie_4k.bin` (ten sam rozmiar 10 728 bajtów).

## 4. Czy nowszy firmware DFE z A6300 da się uruchomić w A6000?

Rozsądne pytanie, skoro układ jest ten sam.

| Cecha | A6000 (2014) | A6300 (2015) |
|---|---|---|
| rozmiar | 65 536 B | 65 536 B |
| baza / układ wektorów | `0x01000000`, identyczny | identyczny |
| tag builda | `20140123_0000_REGULUS` | `20151222_00_1971_REGULUS` |
| adres resetu | `0x01005870` | `0x0100C000` |
| stringi wspólne | 94 z 97 | |
| MMU | brak śladów | `ICACHE,DCACHE and MMU Enable`, 7 instr. CP15 vs 2 |
| bloki MMIO (wyrównane) | 18 | 22 (+`0x01013100`, `0x01014000`, `0x01014B00`, `0x01016000`, `0x01016D00`) |
| podobieństwo bajtowe (bloki 16 B) | Jaccard 0,178 | |

Oba obrazy celują w ten sam układ (`REGULUS`) i są zgodne rozmiarem i adresem bazowym;
plik leży w `/usr`, więc podmiana jest odwracalna reflashem.

Blokery:

1. **MMU** — build 2015 konfiguruje MMU; jeśli rewizja krzemu w A6000 się różni,
   firmware padnie przed czymkolwiek.
2. **Pięć dodatkowych bloków rejestrów** — może nie istnieć na starszej rewizji; zapisy
   będą ignorowane albo wywołają błąd szyny.
3. **Sprzężenie z kodem SoC** — `av-cam.bin` A6000 zawiera `SHD::Regulus` i
   `Camera::ZPD::Control`, które programują rejestry Regulusa według mapy z 2014 r.
4. **Inna ścieżka ładowania** — A6300 używa `DfeCamAif` / `DFE Acquire`, nie ładowania
   z pliku.

Realny scenariusz: aparat wstaje, ale nie inicjuje matrycy lub AF. Ryzyko bricksa jest
niskie, bo plik leży w `/usr`.

**Przed próbą:** ustalić, czy A6000 uruchamia DFE z `/usr/dfe/dfe.bin`, czy z kopii
wbudowanej w `av-cam.bin` pod `0xA67F00`. Tani test A/B to rozstrzyga: podmienić
`/usr/dfe/dfe.bin` na celowo uszkodzoną kopię (i poprawić CRC32); jeśli aparat zachowuje
się identycznie, liczy się kopia wbudowana.

## 5. Co się nie przenosi

- Układ partycji się różni (nflasha3 ma 30 MiB w A6000 vs 20 MiB w A6300; nflasha15
  i nflasha17 są przesunięte), więc całych obrazów nie da się zamieniać.
- `av-cam.bin` różni się rozmiarem (11,4 MB vs 13,4 MB) i treścią.
- Zbiór DSP się różni (A6000 jest podzbiorem).
