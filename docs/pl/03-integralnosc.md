# 03 — Integralność i flashowanie

W skrócie: **firmware CXD90014 nie jest podpisany kryptograficznie.** Integralność to
manifesty CRC32, które każdy może przeliczyć, a zmodyfikowany firmware da się złożyć
bit w bit tak samo jak Sony. Właśnie dlatego A6000 w ogóle przyjmuje własny kod.

## 1. Manifesty to CRC32, nie podpisy

Każdy plik `*.sum` ma format `flag,crc32,size,mode,uid,gid,user,group,-1,-1,ścieżka`.
Wszystkie poniższe przeliczone i zgodne:

| Plik | CRC32 w manifeście | Przeliczone |
|---|---|---|
| `0100_config/big_backup.conf` | `a7bb789e` | ✅ |
| `0100_config/mount.conf` | `046aef0c` | ✅ |
| `0300_partconf/partinf.conf` | `cc4f9b08` | ✅ |
| `0640_darwin/darwin_core.bin` | `9ff7148c` | ✅ |
| `0700_part_image/dev/nflasha3` | `0c047870` | ✅ |
| `…/nflasha5` | `9cb10112` | ✅ |
| `…/nflasha7` | `b969856d` | ✅ |
| `…/nflasha15` | `df198ecd` | ✅ |
| `…/nflasha16` | `c77af80c` | ✅ |
| `0110_backup/…/CX77500_ALLLANG.bin` | `f1cf1892` | ✅ |

Żadnego RSA, ECDSA ani łańcucha podpisów. Rodziny, w których firmware *jest* podpisany
(CXD90045, CXD90057), są poza zasięgiem — dlatego A6000 jest wyjątkowo „hakowalny"
jak na Sony.

## 2. Cały update da się odtworzyć bit w bit

```bash
fwtool.py unpack -f FirmwareData_ILCE6000V321.dat -o fw
fwtool.py pack -c fw/config.yaml -f fw/firmware.tar -u fw/updater.img -o repack
```

| Plik | Rozmiar | SHA-256 |
|---|---|---|
| oryginał Sony | 212 988 056 | `29aef21ab9b5c2e98388974ac9749c2cbfb1815273b444e62f2e41398aa8892f` |
| przepakowany | 212 988 056 | **identyczny** |

To najmocniejszy wynik w tym repozytorium: kryptografia jest w pełni odwracalna, więc
*każda* modyfikacja payloadu idzie tą samą drogą i daje plik przechodzący CRC32 oraz
kontrolę modelu.

`config.yaml` z rozpakowania dokumentuje też tożsamości USB zapisane w pakiecie:
normalna `054c:07c4`, updater `054c:03e2`, model `0x41030035`, wersja `3.21`.

## 3. Co updater faktycznie sprawdza

Trzy bramki, wszystkie z `updater.img_unpacked/config/` i `bin/`:

1. **CRC32** każdego komponentu (`us_crc32sum*.sh`).
2. **LSI main vs sub** (`chkfirm.sh`) — porównuje typ power IC raportowany przez
   `ud_get_power_ic_type.elf` z obecnością `config/sub.conf`.
3. **Pojemność NAND** (`chknandcapa.elf`) względem `partinf.conf`.

Nie ma weryfikacji autorstwa ani wersji, która blokowałaby obraz zmodyfikowany
lub starszy.

## 4. Co jest flashowalne i gdzie jest ryzyko

Aktualizacja dotyka tylko `nflasha3`, `5`, `7`, `15`, `16`
(patrz [02-struktura-firmware.md](02-struktura-firmware.md)).

| Cel | Ryzyko | Komentarz |
|---|---|---|
| `nflasha15` (`/usr`) | **najniższe** | 84 MB userlandu; błąd odwracalny reflashem |
| `nflasha16` (`/android/system`) | niskie | system Androida |
| `nflasha3` (`/system`) | średnie | potok AV; bez niego brak podglądu i nagrywania |
| `nflasha7` (`/rootfs`) | wyższe | rootfs Linuksa |
| `loader_sum` → `pformat_*.elf` | **krytyczne** | przepisuje bootloader — tu się robi brick |
| `us_darwin_firm.sh` | wysokie | firmware power IC; zły obraz = brak bootu |

**Zasada:** pierwsze eksperymenty powinny nieść wyłącznie `part_image`, bez
`loader_sum`, `darwin_sum` i `partconf`.

## 5. Własny kod już działa na tym aparacie

To nie hipoteza. `Sony-PMCA-RE/updatershell/updaterbody.cpp` to kod firmy trzeciej,
który aparat wykonuje w trybie updatera:

```cpp
bool UpdaterBodyImpl::Execute(RingBuffer *buffer, CallbackInterface *interface) {
    mount_vfat("/dev/nflasha2", "/setting");
    usbshell_loop();
    umount("/setting");
    return true;
}
```

`pack.py` pakuje go w cramfs `.dat` z nagłówkiem z
`updatershell/fdat/CXD90014/ILCE-6000.hdr`; `Makefile` buduje
`libupdaterbody_gen3.so` (GEN=3 = CXD90014).

Udostępniany shell (`usbshell.cpp`):

| Komenda | Operacja |
|---|---|
| `SHEL` | `popen2("sh","-i")` — interaktywny shell |
| `PULL` / `PUSH` | odczyt/zapis **dowolnego pliku**, także `/dev/nflasha*` |
| `RMEM` | odczyt **dowolnej pamięci** |
| `BLDR` | odczyt bootloadera |
| `BKRD`/`BKWR`/`BKSY`/`BKDA`/`BKDW`/`BKPR` | `Backup.bin`: odczyt/zapis/sync/protection |
| `AMNT`/`AUMT` | montowanie `/android/data` |

Na poziomie CLI: `info`, `shell`, **`bootrom`**, `bootloader`, `push`, `pull`,
`install`, `bk r|w|patch|s|lock|unlock`, `tweak`.

## 6. Praktyczna recepta na przebudowę

```
1. Zmodyfikuj plik w rozpakowanym obrazie (np. coś w /usr)
2. Przebuduj cramfs:  fwtool.archive.cramfs.writeCramfs(...)
3. Przelicz CRC32 obrazu i popraw part_image.sum
4. fwtool.py pack → własny .dat
5. pmca-console firmware <dat>   (albo updatershell + push + komendy zapisu)
6. Podawaj tylko part_image; loader/darwin/partconf zostaw w spokoju
```

## 7. Zastrzeżenia

- Wszystko powyżej to analiza statyczna pakietu aktualizacji. **Żaden zmodyfikowany
  obraz nie został wgrany** w trakcie tej pracy.
- Przejście bramek CRC32 i modelu jest konieczne, ale nie wystarczające: zły obraz
  może zostawić aparat bez podglądu lub bez AF.
- `updatershell` potrafi zapisywać; zapis w złe miejsce = brick. Używane były wyłącznie
  komendy read-only (`pull`, `ls`, `cat`).
