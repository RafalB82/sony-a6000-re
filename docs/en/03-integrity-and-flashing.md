# 03 — Integrity and flashing

The short version: **CXD90014 firmware is not cryptographically signed.** Integrity is
a CRC32 checksum manifest that anyone can recompute, and a modified firmware can be
rebuilt byte-identically to Sony's. This is why an A6000 can run custom code at all.

## 1. Manifests are CRC32, not signatures

Every `*.sum` file in the update has the format
`flag,crc32,size,mode,uid,gid,user,group,-1,-1,path`. All of these were recomputed
and matched:

| File | CRC32 in manifest | Recomputed |
|---|---|---|
| `0100_config/big_backup.conf` | `a7bb789e` | ✅ |
| `0100_config/mount.conf` | `046aef0c` | ✅ |
| `0300_partconf/partinf.conf` | `cc4f9b08` | ✅ |
| `0640_darwin/darwin_core.bin` | `9ff7148c` | ✅ |
| `0700_part_image/dev/nflasha3` | `0c047870` | ✅ |
| `0700_part_image/dev/nflasha5` | `9cb10112` | ✅ |
| `0700_part_image/dev/nflasha7` | `b969856d` | ✅ |
| `0700_part_image/dev/nflasha15` | `df198ecd` | ✅ |
| `0700_part_image/dev/nflasha16` | `c77af80c` | ✅ |
| `0110_backup/…/CX77500_ALLLANG.bin` | `f1cf1892` | ✅ |

No RSA, no ECDSA, no SHA-based signature chain. Model families where the firmware
*is* signed (CXD90045, CXD90057) are explicitly out of reach — see the Sony-PMCA-RE
README — which is why the A6000 is unusually hackable for a Sony.

## 2. The whole update can be rebuilt byte-identically

```bash
fwtool.py unpack -f FirmwareData_ILCE6000V321.dat -o fw
fwtool.py pack -c fw/config.yaml -f fw/firmware.tar -u fw/updater.img -o repack
```

| File | Size | SHA-256 |
|---|---|---|
| Sony original | 212 988 056 | `29aef21ab9b5c2e98388974ac9749c2cbfb1815273b444e62f2e41398aa8892f` |
| repacked | 212 988 056 | **identical** |

This is the strongest single result in this repository: the crypto is fully
reversible, so *any* modification of the payload takes the same path and produces a
file that passes CRC32 and the model check.

`config.yaml` produced by unpacking also documents the USB identities baked into the
package: normal `054c:07c4`, updater `054c:03e2`, model `0x41030035`, version `3.21`.

## 3. What the updater actually checks

Only three gates, all from `updater.img_unpacked/config/` and `bin/`:

1. **CRC32** of each component (`us_crc32sum*.sh`).
2. **Main vs sub LSI** (`chkfirm.sh`) — compares the power-IC type reported by
   `ud_get_power_ic_type.elf` against the presence of `config/sub.conf`.
3. **NAND capacity** (`chknandcapa.elf`) against `partinf.conf`.

There is no authorship check and no version check that would block a modified or
older image.

## 4. What is flashable, and where the risk is

An update touches only `nflasha3`, `5`, `7`, `15`, `16` (see
[02-firmware-layout.md](02-firmware-layout.md)).

| Target | Risk | Comment |
|---|---|---|
| `nflasha15` (`/usr`) | **lowest** | 84 MB Linux userland; failure is recoverable by reflashing |
| `nflasha16` (`/android/system`) | low | Android system |
| `nflasha3` (`/system`) | medium | AV pipeline; camera without it does not record or preview |
| `nflasha7` (`/rootfs`) | higher | Linux root filesystem |
| `loader_sum` → `pformat_*.elf` | **critical** | rewrites the bootloader — this is where bricks happen |
| `us_darwin_firm.sh` | high | power IC firmware; wrong image = no boot |

**Rule of thumb:** the first experiments should ship only `part_image`, without
`loader_sum`, `darwin_sum` or `partconf`.

## 5. Custom code already runs on this camera

Not a hypothesis. `Sony-PMCA-RE/updatershell/updaterbody.cpp` is third-party code that
the camera executes in updater mode:

```cpp
bool UpdaterBodyImpl::Execute(RingBuffer *buffer, CallbackInterface *interface) {
    mount_vfat("/dev/nflasha2", "/setting");
    usbshell_loop();
    umount("/setting");
    return true;
}
```

`pack.py` wraps it into a cramfs `.dat` with the header from
`updatershell/fdat/CXD90014/ILCE-6000.hdr`; the `Makefile` builds
`libupdaterbody_gen3.so` (GEN=3 = CXD90014).

The shell it exposes (`usbshell.cpp`) provides:

| Command | Operation |
|---|---|
| `SHEL` | `popen2("sh","-i")` — interactive shell |
| `PULL` / `PUSH` | read/write **any file**, including `/dev/nflasha*` |
| `RMEM` | read **arbitrary memory** |
| `BLDR` | read the bootloader |
| `BKRD`/`BKWR`/`BKSY`/`BKDA`/`BKDW`/`BKPR` | `Backup.bin` read/write/sync/protection |
| `AMNT`/`AUMT` | mount/unmount `/android/data` |

and at CLI level: `info`, `shell`, **`bootrom`**, `bootloader`, `push`, `pull`,
`install`, `bk r|w|patch|s|lock|unlock`, `tweak`.

## 6. Practical rebuild recipe

```
1. Modify a file inside the unpacked image (e.g. something in /usr)
2. Rebuild the cramfs:  fwtool.archive.cramfs.writeCramfs(...)
3. Recompute CRC32 of the image and update part_image.sum
4. fwtool.py pack → your own .dat
5. pmca-console firmware <dat>   (or updatershell + push + write commands)
6. Ship only part_image; leave loader/darwin/partconf alone
```

## 7. Caveats

- All of the above is static analysis of the update package. **No modified image was
  ever flashed in the course of this work.**
- Passing the CRC32 and model gates is necessary, not sufficient: a wrong image can
  still leave the camera without preview or AF.
- `updatershell` can write; writing to the wrong region bricks the device. Only
  read-only commands (`pull`, `ls`, `cat`) were ever exercised here.
