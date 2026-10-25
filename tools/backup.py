#!/usr/bin/env python3
"""Narzędzie do offline'owej analizy Backup.bin (BK2/BK4) z firmware Sony.

Korzysta z parsera z Sony-PMCA-RE (`pmca/backup`), ale nie wymaga USB ani
zależności USB (importuje tylko sam moduł backup).

Użycie:
  backup.py info  <plik.bin>                 # nagłówek: region, liczba podsystemów/właściwości
  backup.py list  <plik.bin> [--min-size N]  # wszystkie właściwości (id, attr, rozmiar, hex)
  backup.py get   <plik.bin> <id>            # wartość właściwości, np. 0x003c0373
  backup.py known <plik.bin>                 # znane ID z OpenMemories-Platform
  backup.py diff  <a.bin> <b.bin>            # różnice wartości (np. ALLLANG vs J1)

ID właściwości = subsystem << 16 | numer.
"""
import argparse
import os
import sys

PMCA = os.environ.get("PMCA_DIR", "/home/rafal/sony/Sony-PMCA-RE")
sys.path.insert(0, PMCA)

from pmca.backup import BackupFile  # noqa: E402

# Znane ID (z OpenMemories-Platform/api/backup.cpp)
KNOWN = {
    0x003C0373: "rec_limit H (godziny)",
    0x003C0374: "rec_limit M (minuty)",
    0x003C0375: "rec_limit S (sekundy)",
    0x003C04B6: "rec_limit_4k (sekundy, 2B LE)",
    0x003E0005: "model_name (16B)",
    0x00E70000: "model_code (5B)",
    0x00E70003: "serial_number (4B)",
    0x01070148: "pal_ntsc_selector",
    0x01640001: "usb_app_installer",
    0x01660024: "android_platform_version (8B)",
}
for _i in range(0x010D008F, 0x010D00B2):
    KNOWN[_i] = "language slot %d" % (_i - 0x010D008F)


def open_backup(path):
    return BackupFile(open(path, "rb"))


def cmd_info(args):
    b = open_backup(args.file)
    h = b.header
    print(f"plik            : {args.file} ({os.path.getsize(args.file)} B)")
    print(f"revision        : BK{b.revision}")
    print(f"region          : {b.getRegion()!r}")
    print(f"id1 (protection): {b.getId1()}")
    print(f"numSubsystems   : {h.numSubsystems}")
    print(f"numProperties   : {h.numProperties}")
    print(f"dataOffset      : 0x{h.dataOffset:x}")
    print(f"dataSize        : 0x{h.dataSize:x} ({h.dataSize} B)")
    print(f"checksum        : 0x{h.checksum:08x} (zweryfikowany przez parser)")
    print(f"rozmiar logiczny: {b.size} B")


def cmd_list(args):
    b = open_backup(args.file)
    n = 0
    for pid, prop in b.listProperties():
        n += 1
        if args.min_size and len(prop.data) < args.min_size:
            continue
        name = KNOWN.get(pid, "")
        print(f"0x{pid:08x} attr=0x{prop.attr:02x} size={len(prop.data):5d} "
              f"data={prop.data[:24].hex()}{'...' if len(prop.data) > 24 else ''} {name}")
    print(f"\n-- {n} właściwości --", file=sys.stderr)


def cmd_get(args):
    b = open_backup(args.file)
    pid = int(args.id, 0)
    prop = b.getProperty(pid)
    print(f"id     : 0x{pid:08x}  {KNOWN.get(pid, '')}")
    print(f"attr   : 0x{prop.attr:02x}")
    print(f"size   : {len(prop.data)}")
    print(f"data   : {prop.data.hex()}")
    print(f"ascii  : {prop.data.decode('latin1')!r}")


def cmd_known(args):
    b = open_backup(args.file)
    for pid in sorted(KNOWN):
        try:
            prop = b.getProperty(pid)
        except Exception as e:
            print(f"0x{pid:08x} {KNOWN[pid]:32s} -- {e}")
            continue
        print(f"0x{pid:08x} {KNOWN[pid]:32s} attr=0x{prop.attr:02x} "
              f"size={len(prop.data):4d} {prop.data[:20].hex()}")


def cmd_diff(args):
    a, b = open_backup(args.a), open_backup(args.b)
    pa = {pid: p for pid, p in a.listProperties()}
    pb = {pid: p for pid, p in b.listProperties()}
    print(f"A = {a.getRegion()} ({len(pa)} props)")
    print(f"B = {b.getRegion()} ({len(pb)} props)")
    only_a = sorted(set(pa) - set(pb))
    only_b = sorted(set(pb) - set(pa))
    diff = [pid for pid in sorted(set(pa) & set(pb)) if pa[pid].data != pb[pid].data]
    print(f"tylko w A: {len(only_a)}   tylko w B: {len(only_b)}   różne wartości: {len(diff)}")
    for label, ids, src in (("tylkoA", only_a, pa), ("tylkoB", only_b, pb)):
        for pid in ids[:40]:
            print(f"  {label} 0x{pid:08x} {KNOWN.get(pid,'')} {src[pid].data[:16].hex()}")
    for pid in diff[:200]:
        print(f"  DIFF  0x{pid:08x} {KNOWN.get(pid,''):24s} "
              f"A={pa[pid].data[:16].hex()}  B={pb[pid].data[:16].hex()}")
    if len(diff) > 200:
        print(f"  ... i {len(diff) - 200} dalszych różnic")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("info"); p.add_argument("file"); p.set_defaults(f=cmd_info)
    p = sub.add_parser("list"); p.add_argument("file")
    p.add_argument("--min-size", type=int, default=0); p.set_defaults(f=cmd_list)
    p = sub.add_parser("get"); p.add_argument("file"); p.add_argument("id"); p.set_defaults(f=cmd_get)
    p = sub.add_parser("known"); p.add_argument("file"); p.set_defaults(f=cmd_known)
    p = sub.add_parser("diff"); p.add_argument("a"); p.add_argument("b"); p.set_defaults(f=cmd_diff)

    args = ap.parse_args()
    args.f(args)


if __name__ == "__main__":
    main()
