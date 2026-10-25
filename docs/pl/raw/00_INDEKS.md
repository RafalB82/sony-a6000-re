# Sony A6000 (ILCE-6000) — RE: baza wiedzy

Cel: zebrać i uporządkować wiedzę o reverse engineeringu Sony A6000 tak, żeby dało się
na tym pracować (tweakować ustawienia, dumpować firmware, pisać własne appki PMCA),
a nie tylko czytać blogi.

**Status:** faza zbierania informacji. Nic nie zostało jeszcze zweryfikowane na sprzęcie.

## Jak czytać ten katalog

| Plik | Zawartość |
|---|---|
| `01_STAN.md` | Co wiemy na pewno vs. co jest hipotezą. Poziomy pewności. |
| `02_MECHANIZM.md` | **Najważniejsze.** Jak faktycznie działa hak: 3 tryby USB, Backup.bin, ID ustawień, protection. |
| `03_A6000_FIRMWARE.md` | Sprzęt/SoC, fwtool, procedura dumpu, mapa NAND, Android w kamerze. |
| `04_ZRODLA.md` | Linki + ocena wiarygodności każdego źródła. |
| `05_DALEJ.md` | Otwarte pytania, ryzyka, możliwe kierunki. |
| `06_CLIFFVALE_OCENA.md` | Weryfikacja repo CliffVale na materiale: co prawda, co zmyślone. |
| `07_FIRMWARE_3.21.md` | **Najlepsze źródło.** Co jest w rozpakowanym firmware: tablica partycji Sony, 11× Backup.bin per region, mount.conf. |
| `08_ZMIANY_W_KODZIE.md` | **Co realnie da się zmienić w kodzie** + czy SoC ma więcej niż sprzedał Sony. 4 warstwy modyfikacji, dowody na brak podpisów. |
| `09_ENKODERY_I_WTYCZKI.md` | Programy SA DSP (`/usr/sabin`, 44 szt.) i wtyczki scenariuszy (`/usr/scenario`, 35 szt.). Format kontenera, katalog klas, brakujące tabele 4K, `scenario.elf`. |
| `10_PRIOR_ART.md` | **Kto już tą drogą szedł.** nex-hack (repack 2013), ma1co (fwtool/SA-DSP/qemu), co potwierdziłem sam (round-trip bit w bit), czego nikt nie zrobił. |
| `11_MODELE_BLIZNIACZE.md` | **A6000 vs A6300** (ten sam SoC, 4K). Rozstrzyga 4K dowodem z plików (`/usr/beaune/`), porównuje DSP/wtyczki/partycje + mapa ID ustawień z Recipe Lab. |
| `12_DFE.md` | **DFE (Digital Front End)**: co mówi sieć (CXD90027 „Regulus"), co mówi `dfe.bin` (kod ARM, przerwania DFELINK/ZPD/DEFCAM) i dlaczego A6300 go nie ma. |
| `13_DFE_GHIDRA.md` | **`dfe.bin` w Ghidrze**: baza 0x01000000, 83 procedury (wszystkie nazwane), mapa rejestrów MMIO, dekompilacja (APB self-test, ZPD AF-detect, SCC), **kanał logów = bufor RAM 0x0102D000**, korekta o A6300. |
| `14_DFE_A6300_CZY_ZADZIALA.md` | **Czy nowszy DFE z A6300 da się uruchomić w A6000?** Oba `REGULUS`, 64 KiB, ta sama baza; A6300 nowszy (MMU, +5 bloków rejestrów). Werdykt + plan eksperymentów. |
| `15_PODSUMOWANIE.md` | **Całość w jednym miejscu** — sprzęt z service manuali, partycje, CRC32, 4 warstwy, DFE, A6300/4K, prior art, pytania otwarte, indeks. |
| `16_OBIEKTYWY.md` | **Sterowanie obiektywem**: `Camera::Lens`, ODL (aberracja), dane `VX9xxx`, `LensAberrationData.bin`, `adjstctl.elf` (290 komend), zestawienie z protokołem E-mount z dumpów sigrok. |
| `17_OBIEKTYW_MANUALNY.md` | **Obiektyw bez elektroniki**: jakie warunki w firmware blokują AF i potwierdzenie ostrości (`NID_LENS_INFORMATION` → `uc_AF_Impossible`), co działa (peaking, lupa), czego nie da się obejść. |

## Zasoby lokalne

```
fw-3.21/                  # rozpakowany oficjalny firmware 3.21 (Sony) + venv
  fw/firmware.tar_unpacked/0300_partconf/partinf.conf   # prawdziwa tablica partycji
  fw/firmware.tar_unpacked/0110_backup/.../CX7750x_*.bin # 11× Backup.bin per region
tools/backup.py           # CLI do Backup.bin: info / list / get / known / diff
_cliffvale/               # repo CliffVale (do oceny, nie źródło faktów)
```

## Repozytoria źródłowe (sklonowane lokalnie)

```
Sony-PMCA-RE/             # host-side USB toolkit (Python) — app install, updatershell, serviceshell
OpenMemories-Tweak/       # APK tweakujący ustawienia (JNI → OpenMemories-Platform)
OpenMemories-Platform/    # warstwa C/C++: backup, tweaks, usbcmd, bootloader  ← ID ustawień
OpenMemories-Framework/   # SDK/biblioteka do pisania własnych appek PMCA
OpenMemories-AppList/     # apps.yaml — katalog appek instalowalnych przez PMCA-RE
fwtool.py/                # dekryptor/unpacker firmware Sony (+ devices.yml = baza modeli)
```

`OpenMemories-Platform` to najważniejsze z nich technicznie: tam są konkretne ID
ustawień w `Backup.bin` (`api/backup.cpp`) i wartości on/off tweaków (`api/tweaks.cpp`).

## Ustalenia w 5 punktach

1. A6000 to **aparat z Androida w środku** (Android 2.3.7, warstwa "scalar" Sony na wierzchu).
2. SoC **Sony CXD90014 „BIONZ X"** (4× ARM Cortex-A5), firmware **nie jest podpisany
   kryptograficznie** — dlatego updatershell (własny kod w trybie aktualizacji) w ogóle działa.
3. Hack nie polega na patchowaniu firmware, tylko na **zmianie ukrytych ustawień**
   w `Backup.bin` (~15 000 wpisów) przez API samej kamery.
4. Dostęp developerski = telnet (root shell) + adb, uruchamiane z appki Tweak.
5. Ekosystem PMCA jest **martwy od 2025-08-31** (Sony wyłączyło sklep), ale APKi są
   w Internet Archive i nadal instalowalne przez `pmca-console install`.

## Szybki start (bez kamery)

```bash
cd Sony-PMCA-RE
pip install -r requirements.txt
./pmca-console.py --help
```

Pierwsza rzecz do zrobienia z kamerą podłączoną: `./pmca-console.py info`.
