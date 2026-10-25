# 05 — Co dalej: pytania otwarte i plan

## 5.1 Pytania otwarte

### Bezpieczne, bez kamery
1. ~~**Co siedzi w pozostałych ~15 000 wpisów Backup.bin?**~~ **ZROBIONE** (2026-10-25):
   firmware zawiera 11 gotowych `Backup.bin` per region → znamy **wszystkie 16 102
   istniejące właściwości** (z 17 167 zadeklarowanych) z ID, rozmiarem i atrybutem.
   Narzędzie: `tools/backup.py`. Szczegóły: `07_FIRMWARE_3.21.md` §7.4.
   **Nowe pytanie:** co robią poszczególne ID? Jest ich 16 102 — to nadal dużo pracy,
   ale teraz mamy punkt wyjścia i sposób diffowania (regiony różnią się 37–46 wpisami).
2. **Czym się różni firmware 3.21 od wcześniejszych?** Mamy `fwtool.py` — można zdobyć
   starsze updatery i zdiffować drzewa (`0700_part_image`, `0110_backup`).
3. **Jak wygląda `updater.img`?** Jest rozpakowany lokalnie (`updater.img_unpacked/`:
   `bin/ramdisk.img`, `bin/udtrbody.bin`, busybox) — da się prześledzić, co updater
   robi z NAND i jakie komendy ma jego shell (to rozstrzygnie, czy `pull` istnieje).
4. **Kody regionowe w Backup.bin** — `0x01070b2d/e/f` zawierają w J1 ASCII typu
   `"007-AC0002"`, `"D14-0016001"`; w ALLLANG `"0x00"`. Do rozszyfrowania.
5. **`0640_darwin/darwin_core.bin`** — firmware power ICU (MB9AF004BGL, Cortex-M3).
   Osobny, nietknięty cel RE: sekwencja bootowania, watchdog.
6. **Auth/uprawnienia w API Sony** (HTTP/JSON, porty 8080/61000) — poza trikiem
   z `setPostviewImageSize` wygląda na nieprzebadane.

### Wymagają kamery
6. Potwierdzić `lsusb` = `054c:07c4`, firmware 3.21, region backupu (np. `CE`/`U2`/`E32`).
7. Czy updater mode wchodzi bez problemu na tej sztuce (gotcha z OK).
8. Czy Tweak działa w pełni (bywają wersje fw, gdzie protection nie da się zdjąć).
9. Shutter count (`BKDA` lub EXIF `ImageCount`) — jako punkt odniesienia dla dumpu.

## 5.2 Ryzyka — uszeregowane

| Ryzyko | Poziom | Uwaga |
|---|---|---|
| Zapis do NAND w updatershell | **krytyczny** | jedyny realny sposób na brick. Trzymamy się `pull`/`ls`/`cat`. |
| Instalacja appki PMCA | niski | to normalna appka Androida; najwyżej się nie zainstaluje |
| Tweak (zmiana ustawień) | niski/średni | factory reset częściowo cofa; update firmware też |
| Ożywanie starych APK-ów z archive.org | niski | ale brak podpisu/źródła → nie ufać ślepo |
| Zmiana regionu/protection na `J1` | średni | protection może zostać włączone na stałe (kod to przewiduje) |
| Otwieranie obudowy (IR mod) | wysoki | poza zakresem software-RE, osobny temat |

## 5.3 Proponowana kolejność pracy

**Etap 0 — setup hosta** (0 ryzyka)
```bash
cd ~/sony/Sony-PMCA-RE && pip install -r requirements.txt
./pmca-console.py --help
```
Sprawdzić, czy `libusb` widzi kamerkę po podłączeniu (bez wchodzenia w tryby).

**Etap 1 — off-line, bez kamery** (0 ryzyka, dużo wiedzy)
- Pobrać oficjalny updater 3.21, `fwtool unpack`, obejrzeć drzewo.
- Rozpakować `updater.img` → initrd → prześledzić procedurę zapisu NAND.
- Zdobyć Backup.bin (skądś: z dumpu albo przez `pmca-console backup`) i przepuścić
  przez `print_backup`, żeby zobaczyć pełną listę ID.

**Etap 2 — pierwszy kontakt** (niskie ryzyko)
```bash
./pmca-console.py info            # identyfikacja, API, firmware
./pmca-console.py install -i      # OpenMemories-Tweak
```
Potem w kamerze: Tweak → Developer → WiFi + Telnet + ADB.

**Etap 3 — dump** (średnie ryzyko, tylko read-only)
```bash
./pmca-console.py updatershell -m ILCE-6000   # PAMIĘTAJ O OK NA EKRANIE
# pull /dev/nflasha nflasha
```
Weryfikacja: odtworzyć mapę regionów CliffVale własnymi skryptami i porównać
z rozpakowanym firmware 3.21. To rozstrzygnie, czy jego mapa jest prawdziwa.

**Etap 4 — właściwe RE** (dopiero tutaj)
- `print_backup` na własnym Backup.bin → katalog ID.
- Zmiana pojedynczych ID → obserwacja efektu → notatka.
- Ewentualnie własna appka PMCA (`OpenMemories-Framework`) do rzeczy, których Tweak nie ma.

## 5.4 Kwestia prawna / higiena

- Nie publikować: dumpów NAND (zawierają dane właściciela — WiFi credentials, UUID
  urządzenia), firmware Sony, cudzych APK.
- CliffVale sam to podkreśla i trzyma binaria prywatnie — dobra praktyka do naśladowania.
