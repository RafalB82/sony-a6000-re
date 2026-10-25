# 08 — Realna zmiana w kodzie: co można, jak, i co siedzi w sprzęcie

Odpowiedź na dwa pytania: **(A)** co realnie da się zmienić w kodzie (nie w ustawieniach),
**(B)** czy CXD90014/A6000 ma możliwości, których Sony nie sprzedał w firmware.

Wszystko poniżej sprawdzone na rozpakowanym firmware 3.21 i kodzie źródłowym ma1co.
Poziom pewności oznaczam: **[S]** sprawdzone bezpośrednio, **[W]** wynika z kodu Sony,
**[H]** hipoteza do przetestowania.

---

## A. Co realnie da się zmienić

### Podsumowanie: cztery warstwy, rosnące możliwości i rosnące ryzyko

| # | Warstwa | Co zmieniasz | Ryzyko | Status |
|---|---|---|---|---|
| 0 | `Backup.bin` | ustawienia (limity, języki, protection) | zerowe | **zrobione** przez OpenMemories-Tweak |
| 1 | APK PMCA | własny kod w Androidzie, 322 klasy API Sony | niskie | **działa, instalowalne** |
| 2 | runtime root | dowolne binarki w działającym Linuksie (telnet/adb) | średnie | **działa** |
| 3 | obrazy partycji | podmiana `/usr`, `/system`, `/rootfs`, `/android/system` | **wysokie** | **wykonalne** (patrz A.3) |

Warstwa 3 to jest ta „prawdziwa zmiana w kodzie" — i tu mam twarde dowody, że
**nic nie jest podpisane kryptograficznie**.

---

### A.1. Warstwa 1 — własna appka (najbezpieczniejszy „prawdziwy kod")

Aparat akceptuje **dowolny APK** podpisany certyfikatem debug albo release
(Android 2.3.7, API 10). Do dyspozycji jest **322 klasy API Sony** (`com.sony.*`)
— `OpenMemories-Framework/stubs/src/main/jasmin/`: **[S]**

| pakiet | klas |
|---|---|
| `com.sony.scalar.hardware` | 102 |
| `com.sony.scalar.sysutil.didep` | 46 |
| `com.sony.scalar.media` | 42 |
| `com.sony.scalar.provider` | 36 |
| `com.sony.scalar.widget` | 14 |
| `com.sony.scalar.graphics[.imagefilter]` | 21 |
| `com.sony.scalar.hardware.avio` | 9 |
| `com.sony.scalar.meta`, `sysutil`, `sysnetutil` | 10 |

Najciekawsze praktycznie: **`com.sony.scalar.media.MediaRecorder`** z
`Parameters`, `VideoSource`, `TimeCodeInfo`, `StreamBuffer`, `OnStreamWriteListener`.
Czyli appka może **skonfigurować własny recorder** (a nie tylko użyć trybów z UI)
i przechwytywać strumień. To najbardziej obiecujący kierunek „zmiany zachowania
nagrywania bez ruszania firmware" — **[H]** czy da się wymusić profil/bitrate
szerszy niż w menu (ogranicza to enkoder w `/usr/sabin/`, patrz B.3).

Co już tym sposobem zrobiono (istniejące appki): clean HDMI (`PMCA-HDMICam`),
intervalometer (`TimeLapse`), bracketowanie ostrości (`FocusBracket`),
ręczne sterowanie (`BetterManual`), FTP upload.

**Ograniczenie:** appka siedzi w Androidzie, nie ma dostępu do `/dev/nflasha*`
ani do potoku AV (BIONZ/SA DSP). To userland.

---

### A.2. Warstwa 2 — root w działającym systemie

OpenMemories-Tweak odpala `telnetd` (:23) i własne `adbd` (:5555) → **dowolny kod
w Linuksie kamery**. Do tego `bin/android_console.sh` (jest w `/usr/bin/` — **[S]**).

Co to daje:
- odczyt/zapis `/setting` (**nflasha2**, vfat — trwałe),
- `/tmp` = **nflasha10** (vfat, 5 MiB) — uwaga: to partycja flash, nie tmpfs, więc
  pliki tam **przetrwają restart**; wygodne na „małe trwałe modyfikacje bez reflashu",
- podmiana plików w `/system` (nflasha3) i `/android/*` — jeśli system plików
  na to pozwoli (raw/vfat tak, cramfs nie),
- **nie** da się zmienić `/usr` — to cramfs (tylko odczyt), trzeba reflashu (A.3).

To jest warstwa do eksperymentów: można testować zmiany „na żywo", a dopiero
sprawdzone przenosić do obrazu partycji.

---

### A.3. Warstwa 3 — podmiana firmware (i dlaczego to jest wykonalne)

#### A.3.1. Integralność = CRC32, nie podpis **[S]**

Sprawdziłem wszystkie manifesty `*.sum` z firmware i **przeliczyłem CRC32** —
zgadzają się co do bitu:

| plik | CRC32 w manifeście | moje CRC32 |
|---|---|---|
| `config/big_backup.conf` | `a7bb789e` | ✅ |
| `config/mount.conf` | `046aef0c` | ✅ |
| `partconf/partinf.conf` | `cc4f9b08` | ✅ |
| `darwin/darwin_core.bin` | `9ff7148c` | ✅ |
| `part_image/dev/nflasha3` | `0c047870` | ✅ |
| `part_image/dev/nflasha5` | `9cb10112` | ✅ |
| `part_image/dev/nflasha7` | `b969856d` | ✅ |
| `part_image/dev/nflasha15` | `df198ecd` | ✅ |
| `part_image/dev/nflasha16` | `c77af80c` | ✅ |
| `backup/…/CX77500_ALLLANG.bin` | `f1cf1892` | ✅ |

Format manifestu: `flag,crc32,size,mode,uid,gid,user,group,-1,-1,sciezka`.
**Wniosek: nie ma podpisów RSA/ECDSA. Jest suma kontrolna, którą sami policzymy.**
To jest dokładnie to, co odróżnia CXD90014 od CXD90045/90057 (tam firmware jest
podpisany — patrz README Sony-PMCA-RE).

#### A.3.2. Co updater faktycznie weryfikuje **[W]**

Z `updater.img_unpacked/config/config.xml` + `bin/*.sh`:

| krok | skrypt | co robi |
|---|---|---|
| config | `us_crc32sum.sh` | CRC32 plików config |
| config | **`chkfirm.sh`** | **tylko sprawdza, czy fdat jest dla main czy sub LSI** (po typie power ICU: Charon/CA/Piroshiki/Darwin) |
| config | `edit_mount.sh`, `keep_big_backup.sh` | dokleja `mount1.conf`, zachowuje `psd.bin` |
| updater | `us_crc32sum.sh` | CRC32 obrazu updatera |
| appli | `us_crc32sum_appli.sh` | CRC32 appli |
| part_image | `us_crc32sum.sh` | CRC32 obrazów partycji |
| partconf | **`chknandcapa.elf`** | sprawdza pojemność NAND vs `partinf.conf` |
| partconf | `us_mkfs.sh` | tworzy systemy plików |
| darwin | `us_darwin_firm.sh` | **flashuje power ICU (MB9AF004BGL)** |
| ca | `us_ca_firm.sh` | flashuje układ CA |
| prfile / accsy / backup | `us_crc32sum*.sh` | CRC32 odpowiednich plików |
| loader | **`loader_writer.sh`** → `pformat_normal/safe.elf` | **przepisuje bootloader**, MD5 z `loader_mpt.md5` |

Czyli bramki są trzy: **CRC32 + typ LSI + pojemność NAND**. Żadnej weryfikacji
autorstwa. **Nie ma sprawdzania wersji** (jest `VERSKIP` jako tryb, ale to nie blokada).

#### A.3.3. Co jest w ogóle flashowalne **[S]**

`part_image.sum` zawiera **dokładnie 5 obrazów** (i tylko te są podmieniane):

| obraz | partycja | mount | rozmiar | rola |
|---|---|---|---|---|
| `nflasha3` | 30 MiB | `/system` | 11.49 MB | **potok AV** (`av-cam.bin`, 11.4 MB!) |
| `nflasha5` | 60 MiB | `/wbi` | 42.29 MB | Warm Boot Image |
| `nflasha7` | 4 MiB | `/rootfs` | 3.32 MB | rootfs |
| `nflasha15` | 100 MiB | `/usr` | 84.04 MB | **cały Linux userland (cramfs)** |
| `nflasha16` | 82.75 MiB | `/android/system` | 59.01 MB | Android system |

**Nie są ruszane:** `nflasha17` (`/android/data`, dane użytkownika) i `nflasha2`
(`/setting`, `Backup.bin`) — czyli **dane i ustawienia przeżywają update**.

#### A.3.4. Dowód, że własny kod już tam działa **[S]**

To nie teoria. `Sony-PMCA-RE/updatershell/` to **własny payload ma1co**, który
kamera wykonuje w trybie updatera:

```cpp
// updatershell/updaterbody.cpp — TO SIĘ WYKONUJE NA KAMERZE
bool UpdaterBodyImpl::Execute(RingBuffer *buffer, CallbackInterface *interface) {
    mount_vfat("/dev/nflasha2", "/setting");
    usbshell_loop();          // własny protokół USB
    umount("/setting");
    return true;
}
```

`pack.py` pakuje to jako cramfs → `.dat` → nagłówek `fdat/CXD90014/ILCE-6000.hdr`.
`Makefile` buduje `libupdaterbody_gen3.so` (GEN=3 = CXD90014). Czyli **A6000
przyjmuje i uruchamia nie-Sony kod w kontekście updatera** — to jest fakt, nie hipoteza.

Co ten shell potrafi (`usbshell.cpp`) **[S]**:

| cmd | operacja |
|---|---|
| `SHEL` | `popen2("sh","-i")` → **interaktywny shell** |
| `PULL` / `PUSH` | odczyt/zapis **dowolnego pliku** (także `/dev/nflasha*`) |
| **`RMEM`** | odczyt **dowolnego obszaru pamięci** (`offset`,`size`) |
| `BLDR` | odczyt **bootloadera** (bloki) |
| `BKRD`/`BKWR`/`BKSY`/`BKDA`/`BKDW`/`BKPR` | odczyt/zapis/sync/protection `Backup.bin` (przez API jądra) |
| `AMNT`/`AUMT` | montowanie/odmontowanie `/android/data` |

A na poziomie CLI `updatershell` daje: `info`, **`shell`**, **`bootrom`** (zrzut BootROM!),
`bootloader`, `push`, `pull`, `install`, `bk r|w|patch|s|lock|unlock`, `tweak`.

#### A.3.5. Ścieżka praktyczna zmiany kodu

```
1. Modyfikujesz plik w rozpakowanym obrazie (np. /usr/bin/... albo /usr/sabin/...)
2. Przebudowujesz cramfs:  fwtool.archive.cramfs.writeCramfs(...)   [jest w fwtool.py]
3. Przeliczasz CRC32 obrazu i wpisujesz do part_image.sum
4. fwtool pack → własny .dat (nagłówek z fdat/CXD90014/ILCE-6000.hdr)
5. pmca-console firmware <dat>    albo    updatershell → push + komendy zapisu
6. Kamera robi update; loader zostaje nietknięty (jeśli nie dasz loader.sum)
```

#### A.3.6. Gdzie jest ryzyko bricksa **[W]**

| operacja | ryzyko |
|---|---|
| podmiana `nflasha15` (`/usr`) | **niskie** — najbezpieczniejszy cel: 84 MB userlandu, w razie błędu kamera wstanie w tryb updatera |
| podmiana `nflasha3` (`/system`, AV) | średnie — bez AV pipeline kamera nie nagrywa/prędykowo nie działa |
| podmiana `nflasha7` (`/rootfs`) | wyższe — to rootfs Linuksa |
| **`loader.sum` / `pformat_*.elf`** | **krytyczne** — przepisuje bootloader; tu się robi brick |
| `us_darwin_firm.sh` | wysokie — power ICU startuje SoC; zły firmware = brak bootu |

**Zasada:** przy pierwszych próbach nie podawać w fdat ani `loader_sum`, ani `darwin_sum`,
ani `partconf` — tylko `part_image` z jednym zmienionym obrazem.

---

## B. Czy SoC oferuje więcej niż Sony sprzedał w A6000

### B.1. Co jest w środku **[S]**

| element | ustalenie | źródło |
|---|---|---|
| SoC | Sony **CXD90014** „BIONZ X", 4× Cortex-A5 | `hardware.rst` |
| Sensor | **IMX210**, klasy `C_ImagerCtrl_IMX210E`, `ImagerDrvParam_IMX210E` | `nflasha3/av-cam.bin` |
| Enkoder wideo | wewnętrzny **ZIMA** (inicjalizacja 60i/50i, 60p/50p) | `av-cam.bin` |
| Drugi enkoder | **Beaune** (CXD4236) — obsługiwany w kodzie, ale… | `av-cam.bin`: `[SYNCSETMODE] MC0/MC1 (0:Zima 1:Beaune 2:NONE)` |
| DFE | CXD90027 „Regulus", firmware `dfe/dfe.bin` (65 KB) | `/usr` |
| DSP | **SA** — programy „sabin" (`sa_apce*`, `sa_avce*`, `sa_aac*`) | `/usr/sabin/` |
| Power IC | MB9AF004BGL „Darwin" (Cortex-M3), `darwin_core.bin` | firmware |

### B.2. 4K: **nie da się** — i to nie jest ograniczenie firmware **[S]**

Kod AV jest **wielomodelowy**: ta sama binarka `av-cam.bin` obsługuje enkoder
wewnętrzny („Zima") i zewnętrzny („Beaune"), a wybór jest robiony w runtime
(`SYNCSETMODE MC0/MC1`). Ale `hardware.rst` jest jednoznaczne:

```
CXD90014            → 1080p (60fps)
CXD90014 + Beaune   → 4K     (30fps)
```

A6000 to **1080p60**, więc **Beaune nie jest zamontowany**. 4K wymagałoby
dolutowania CXD4236 + ścieżek na PCB — nie da się tego zrobić z firmware.
Ewentualne stringi „4K" w UI (`string_*.uxc`) są wspólne dla całej platformy
(A7R II, RX100M4 mają Beaune) — **string ≠ możliwość**.

### B.3. Co platforma ma, a A6000 nie używa

| obserwacja | interpretacja |
|---|---|
| **4 różne programy enkodera** wideo/audio: `sa_avce_performance_zma`, `quality_zma`, `performance_plus_zma`, `sa_avcd_*` | trzy warianty enkodera AVC **są dostarczone**, ale **nie wiadomo, którego używa A6000** — `av-cam.bin` nie referuje ich po nazwie. Szczegóły i mój fałszywy trop: `09_ENKODERY_I_WTYCZKI.md` §2 |
| UI zawiera stringi S-Log / XAVC / 120p / 2160 | wspólna baza stringów całej rodziny CXD90014 **[S]** |
| `scenario/` — 35 wtyczek `.so` (HDMI, movie rec, panel EVF, mic) | zachowanie trybów jest **konfigurowalne przez scenariusze**, nie zaszyte **[H]** |
| `av-cam.bin` ma klasy sterowników konkretnego sensora | podmiana sensora = inny sterownik; A6000 ma tylko IMX210 **[S]** |

**Wniosek:** oprogramowanie jest bogatsze niż to, co A6000 pokazuje w menu, ale
bogactwo jest odcinane **sprzętem** (brak Beaune) albo **konfiguracją**
(model code / region w `Backup.bin`, zestaw `scenario/*.so`). To, co da się
realistycznie odblokować, to rzeczy zależne od konfiguracji, nie od układów.

### B.4. Realistyczna lista: co da się odblokować, a co nie

| funkcja | da się? | dlaczego |
|---|---|---|
| limit 30 min nagrania | ✅ zrobione | wpis w `Backup.bin` (`0x003c0373–75`) |
| języki (35 slotów) | ✅ zrobione | `0x010d008f–b1` + region |
| brak ekranu NTSC | ✅ zrobione | `0x01070148` |
| czyste HDMI | ✅ (appka) | `PMCA-HDMICam` — to userland, nie firmware |
| **region / język na stałe przez update** | ✅ **nowe** | `endupdate.sh` **kopiuje `backup/*/*/*.bin` do `/setting/Backup.bin`** — czyli wgraj fdat z `CX77500_ALLLANG.bin` i kamera dostanie wszystkie języki „fabrycznie" **[S]** |
| intervalometer | ✅ (appka) | `TimeLapse` |
| własny bitrate/profil nagrywania | ⚠️ **[H]** | przez `com.sony.scalar.media.MediaRecorder` z appki; ogranicza enkoder ZIMA |
| S-Log2/3 na A6000 | ⚠️ **[H]** mało prawdopodobne | wymaga tablic gamma w potoku; obecność stringów nic nie dowodzi |
| 4K / 2160p | ❌ | brak Beaune (sprzęt) |
| 120p | ❌ [H] | sensor/enkoder; brak dowodu na obsługę w AV kodzie A6000 |
| 10-bit / wyższa głębia | ❌ [H] | potok AV + zapis ARW; brak śladów w konfiguracji |
| szybszy USB / USB3 | ❌ | sprzęt (USB 2.0) |
| zmiana zachowania AF, EFCS itp. | ⚠️ | przez `Backup.bin` (ID nieznane) — pole do eksploracji 16 102 wpisów |

---

## C. Co bym zrobił jako pierwsze doświadczenie (bezpieczne)

Cel: **udowodnić, że podmiana kodu działa**, minimalnym ryzykiem.

1. Weź `nflasha15` (`/usr`, cramfs) — najbezpieczniejszy cel.
2. Dodaj coś **nieszkodliwego i widocznego**: np. plik `/usr/bin/hello.sh`
   albo wpis w istniejącym skrypcie startowym, który zapisze marker do `/tmp`
   (`/tmp` = nflasha10, przeżywa restart → dowód).
3. Przebuduj cramfs (`fwtool.archive.cramfs`), przelicz CRC32, popraw `part_image.sum`.
4. Zbuduj fdat **tylko z `part_image`** (bez `loader_sum`, bez `darwin_sum`, bez `partconf`).
5. Wgraj, uruchom kamerę, sprawdź marker.

Jeśli marker jest — mamy potwierdzenie pełnego łańcucha „modyfikacja → flash → działa",
i dopiero wtedy sensowne jest grzebanie w `av-cam.bin` czy `sabin/`.

Warunek wstępny: kamera + kabel + w pełni naładowany akumulator (`part_image`
to ~200 MB zapisu; przerwanie = ryzyko).

---

## D. Czego jeszcze nie wiemy

1. **Czy updater sprawdza coś poza CRC32** — `uc_crc32sum.elf -s -c` może robić
   coś więcej niż CRC (np. sprawdzać rozmiar/sektory). Do zdisasemblowania:
   `bin/uc_crc32sum.elf` (10 KB, ARM) i `chknandcapa.elf`.
2. **`nflasha3` (`av-cam.bin`)** — 11.4 MB kodu AV z symbolami C++ (`N6Camera6Imager6IMX210…`).
   Nietknięte pole RE: tu siedzą tryby sensora, PSF, być może nieużywane ścieżki.
3. **Korelacja model_code ↔ funkcje** — czy A6000 i A7 różnią się tylko `Backup.bin`,
   czy też `scenario/*.so`. Jeśli tylko ustawieniami → podmiana model_code mogłaby
   odblokować funkcje UI (ale ryzyko: inny sensor w A7 → awarie).
4. **`RMEM`** — odczyt pamięci w updaterze; potencjalnie najkrótsza droga do
   zrzutu kluczy/stanu secure boot (razem z `bootrom`).
5. **`us_darwin_firm.sh`** — Darwin jest flashowalny; co by się stało z inną wersją?
   (wysokie ryzyko, ale to jedyny układ „poniżej" SoC).
