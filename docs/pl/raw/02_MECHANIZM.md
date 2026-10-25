# 02 — Mechanizm: jak to właściwie działa

Wszystko poniżej wyprowadzone z kodu (`Sony-PMCA-RE`, `OpenMemories-Platform`,
`OpenMemories-Tweak`), nie z blogów.

## 2.1 Trzy niezależne drogi wejścia

Aparat wystawia przez USB trzy różne interfejsy. To najważniejsze rozróżnienie
w całym ekosystemie — ludzie mylą je i dlatego tutoriale "nie działają".

| Tryb | Kto inicjuje | Co daje | Ograniczenia |
|---|---|---|---|
| **App Installer** (PMCA/MSC) | normalna praca aparatu | instalacja APK jako appki w menu | tylko modele z PMCA; wymaga Android subsystem |
| **Updater mode** (`updatershell`) | `pmca-console updatershell` | powłoka w firmware *aktualizatora*, dostęp do `/dev/nflasha` | tylko gdy firmware **niepodpisany** (CXD90014 itd.); CXD90045/90057 odpadają |
| **Service mode** (`serviceshell`, "senser mode") | `pmca-console serviceshell` | kod w *działającym* systemie, dump firmware | wymaga custom driverów USB (Zadig/libusb) |

A6000 (CXD90014) łapie się na **wszystkie trzy** — to najlepsza możliwa sytuacja.

### App Installer — co dokładnie robi
1. APK jest konwertowany do formatu Sony (`apk2spk`) — `.spk`.
2. Wysyłany po PTP do aparatu, aparat instaluje go w `/data/app`.
3. Akceptowane są certyfikaty debug **i** release (nie trzeba podpisywać jako Sony).
4. Appka pojawia się w "Application List".

To jest **nie** modyfikacja firmware — to instalacja normalnej appki Androida.
Dlatego ryzyko bricksa jest tu najmniejsze.

### Updater mode — dlaczego działa
Sony ma drugą partycję bootowalną do aktualizacji firmware. `updatershell` podmienia
payload aktualizacji na własny shell. Firmware aparatu pozostaje **nietknięty**
(dopóki nic nie zapiszesz). Na CXD90014 nie ma weryfikacji podpisu → shell się uruchamia.

⚠️ Shell ma też komendy zapisu (`push`, komendy firmware update). Zapis w złe miejsce
= brick. My używamy wyłącznie **read-only** (`pull`, `ls`, `cat`).

## 2.2 Gdzie naprawdę siedzą "ukryte funkcje": Backup.bin

Cały OpenMemories-Tweak nie patchuje kodu. On **zmienia wartości w pliku ustawień**
`Backup.bin`, do którego Sony nie daje UI.

### Struktura pliku (z `pmca/backup/__init__.py`)

```
offset  pole
0x00    magic (int32)
0x04    cookie (int32)
0x08    writeComp (int32)
0x0c    revision  — string "BK2" lub "BK4"   ← wersja formatu
0x10    numSubsystems
0x14    numProperties
0x18    dataOffset
0x1c    dataSize
0x20    checksum
0x28    id1  (int32)   ← flaga protection
0x3c    version (0x20)
0xc0    region (0x20)  ← np. "U2", "CE", "J1", "ALLLANG"
```

- `BK2` → wpisy tabeli właściwości mają `attr` jako **int8**
- `BK4` → `attr` jako **int16** (nowsze modele)
- `attr == 1` → `BACKUP_ATTR_READ_ONLY` (zapis zwraca `-BACKUP_ERROR_READ_ONLY`)

### Adresowanie właściwości
ID to 32-bit: **subsystem (górne 16 bitów) | numer węzła (dolne 16 bitów)**.
`Backup_write(id >> 16, id, ...)` — subsystem jest wyciągany z samego ID.

Znane ID (z `OpenMemories-Platform/api/backup.cpp`):

| ID | Rozmiar | Znaczenie |
|---|---|---|
| `0x003c0373` / `74` / `75` | 1 B każdy | limit nagrania: godziny / minuty / sekundy |
| `0x003c04b6` | 2 B | limit nagrania 4K (RX100M4), sekundy LE |
| `0x003e0005` | 16 B | nazwa modelu (string) |
| `0x01070148` | 1 B | selektor PAL/NTSC (0/1) |
| `0x010d008f` … `0x010d00b1` | 1 B × 35 | sloty językowe: 1=on, 2=off |
| `0x01640001` | 1 B | "USB app installer" |
| `0x01660024` | 8 B | wersja platformy Android |
| `0x00e70000` | 5 B | model code |
| `0x00e70003` | 4 B | numer seryjny |

W Backup.bin jest **17 167 zadeklarowanych wpisów** (16 102 faktycznie istniejących
w domyślnym pliku z firmware). Znamy znaczenie ~10. To jest główne pole
do własnego RE — i mamy już punkt wyjścia: `07_FIRMWARE_3.21.md` §7.4.

### Protection — dlaczego "Disable Protection" w ogóle istnieje
`is_enabled()` protection = `!Backup_get_protection()`, a `Backup_get_protection()`
czyta `id1` z danych presetu. Zapis flagi idzie przez osobne polecenie
`backup_senser_cmd_ID1` (a nie przez normalny zapis właściwości).

Sztuczki z kodu, warte zapamiętania:
- Na Androidzie 2 trzeba **stworzyć `/setting`, zapisać `Backup.bin`, potem katalog usunąć** —
  inaczej flaga się nie ustawi. Na Androidzie 4 `/android` jest read-only i wywołanie
  "cicho zawodzi", ale flaga ustawia się i tak.
- Region `J1` (Japonia): protection da się tylko **włączyć**. Wyłączenie wymaga
  sztuczki: `Backup_protect(0, ..., region="")` → `Backup_set_protection()` → przywrócenie
  regionu. To jest cała różnica między `tweak_protection` a `tweak_protection_advanced`.

## 2.3 Uprawnienia, które daje Tweak

| Funkcja | Mechanizm |
|---|---|
| telnet :23 | Tweak odpala `telnetd`; przez wifi dostajesz root shell |
| adb :5555 | Tweak odpala własne `adbd` (skompilowane z AOSP `system/core`, patrz `jni/Android.mk`) |
| `android_console.sh` | wejście w normalny shell Androida (nie tylko busybox updatera) |
| dump firmware | `dd if=/dev/nflasha of=... bs=1M` |

Ważne: Tweak **nie daje roota w sensie Androida** — cała appka i tak chodzi jako
użytkownik systemowy. "Root shell" to po prostu shell procesu o tych uprawnieniach.

## 2.4 Ścieżka od zera do root shella (kolejność)

```
1. pmca-console install -i        → instaluje OpenMemories-Tweak (APK)
2. w kamerze: Application List → Tweak
3. Developer tab → Enable Wifi  (i podnieś "Power save start time"!)
4. Developer tab → Enable Telnet
5. telnet <ip_kamery>
```

Bez kroku 3 telnet nie ma jak się połączyć, a kamera zaśnie po kilku minutach
(`DisableWiFiOnSuspend.java` w źródleTweak obchodzi częściowo ten problem).

## 2.5 Dlaczego to wszystko przestało być "wygodne"

Sony wyłączyło sklep PMCA 2025-08-31 → nie da się już pobrać oryginalnych appek
(Smart Remote Control, Time-lapse, FTP Uploader). Ale:
- APKi są zarchiwizowane na Internet Archive (`sony-playmemories-camera-apps`),
- instalacja przez `pmca-console install` **nadal działa** — to protokół lokalny, nie sklep.

Czyli A6000 jest dziś *bardziej* modowalny niż nowsze body, bo cały toolchain działa offline.
