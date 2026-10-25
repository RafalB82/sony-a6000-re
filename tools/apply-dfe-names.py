# Ghidra (Jython) — zastosuj nazwy z dfe-names.txt do programu dfe.bin
#
# Użycie:
#   1) zaimportuj dfe.bin jako Raw Binary, ARM:LE:32:v7, base 0x01000000
#   2) uruchom ten skrypt (Script Manager) z argumentem = ścieżka do dfe-names.txt
#      albo ustaw NAMES_PATH poniżej
#
# Plik z nazwami: linie "<adres>\t<nazwa>", adresy w formacie 0x...

import os

NAMES_PATH = os.environ.get("DFE_NAMES", "/home/rafal/sony/analysis/dfe-names.txt")

def main():
    path = NAMES_PATH
    args = getScriptArgs()
    if args:
        path = args[0]

    applied = 0
    missing = 0
    f = open(path, "r")
    try:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            addr = toAddr(int(parts[0], 16))
            name = parts[1].strip()
            if getFunctionAt(addr) is None:
                # spoza listy funkcji — pomiń, nie twórz nowych
                missing += 1
                continue
            createLabel(addr, name, True)
            getFunctionAt(addr).setName(name, ghidra.program.model.symbol.SourceType.USER_DEFINED)
            applied += 1
    finally:
        f.close()

    print("dfe: zastosowano %d nazw, pominięto %d" % (applied, missing))

main()
