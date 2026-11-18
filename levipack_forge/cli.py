from __future__ import annotations
import argparse, json, sys
from . import __version__


def main(argv=None):
    ap = argparse.ArgumentParser(prog="levipack-forge", description="Fabric mod (.jar) -> LeviLauncher Android .levipack project")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("convert", help="convert a Fabric jar into a buildable native-mod project")
    c.add_argument("jar"); c.add_argument("-o", "--out", default="out")
    c.add_argument("--mc-versions", help='JSON array for the manifest, e.g. \'["1.26.*"]\'')
    c.add_argument("--symbols", help="symbol index (.txt), libminecraftpe.so or the zip containing it")
    c.add_argument("--mod-id")
    c.add_argument("--overrides", help="overrides.json with fixes for unsupported calls (survives re-conversion)")

    s = sub.add_parser("symbols", help="work with the Bedrock symbol index")
    ss = s.add_subparsers(dest="scmd", required=True)
    i = ss.add_parser("index", help="build symbols.txt from libminecraftpe.so / zip")
    i.add_argument("src"); i.add_argument("-o", "--out", default="symbols.txt")
    q = ss.add_parser("search", help="find mangled names containing all given identifiers")
    q.add_argument("index"); q.add_argument("names", nargs="+"); q.add_argument("-n", type=int, default=20)

    v = sub.add_parser("vtable", help="show verified vtable slots for the bundled (or given) symbols.json")
    v.add_argument("--db", help="symbols.json from tools/so_probe.py")

    d = sub.add_parser("vtdiff", help="slots where DERIVED overrides BASE in a vtable dump (calibration aid)")
    d.add_argument("dump"); d.add_argument("base"); d.add_argument("derived")
    d.add_argument("--only-shapes", action="store_true", help="show only slots recognised as tiny getters/constants")

    k = sub.add_parser("slotguess", help="candidate Itanium slots for an Amethyst (MSVC) vfunc index")
    k.add_argument("dump"); k.add_argument("cls"); k.add_argument("index", type=int)
    k.add_argument("--want", help='shape filter, e.g. "returns 0" or "getter"')

    pm = sub.add_parser("pack-merge", help="merge resource_pack/player.entity.patch.json into the vanilla player.entity.json")
    pm.add_argument("patch"); pm.add_argument("vanilla"); pm.add_argument("-o", "--out", required=True)

    a = ap.parse_args(argv)
    if a.cmd == "convert":
        from .generator import convert
        r = convert(a.jar, a.out, a.mc_versions, a.symbols, a.mod_id, a.overrides)
        print(json.dumps(r, indent=2))
        print(f"\nNext: read {r['out']}/CONVERSION_REPORT.md, then build (see README).")
    elif a.cmd == "vtable":
        from . import vtable
        db = vtable.load(a.db)
        print(f"build sha256 {db['sha256']}  ({db.get('mc_version_string')})")
        for cls, vs in db["vtables"].items():
            print(f"{cls:14} " + ", ".join(f"{x['vptr_rva']}({x['slots']})" for x in vs))
        print("\nverified Item slots:")
        for n, (s_, r, sig, ev) in vtable.VERIFIED_ITEM_SLOTS.items():
            print(f"  [{s_:3}] {n:22} {r:#x}  {sig}   <- {ev}")
    elif a.cmd == "vtdiff":
        from . import vtdump
        dump = vtdump.parse(a.dump)
        for i, kind, rva, ins in vtdump.diff(dump, a.base, a.derived):
            sh = vtdump.shape(ins)
            if a.only_shapes and not sh:
                continue
            print(f"[{i:3}] {kind:8} {rva:#x}  {sh or ins[:60]}")
    elif a.cmd == "slotguess":
        from . import vtdump
        for i, rva, sh, ins in vtdump.candidates(vtdump.parse(a.dump), a.cls, a.index, a.want):
            print(f"[{i:3}] {rva:#x}  {sh or '-':28} {ins}")
    elif a.cmd == "pack-merge":
        from .bedrock_pack import merge_player_entity
        v = json.load(open(a.vanilla, encoding="utf-8-sig"))
        m = merge_player_entity(v, json.load(open(a.patch, encoding="utf-8")))
        json.dump(m, open(a.out, "w", encoding="utf-8"), indent=1)
        print(f"merged -> {a.out}")
    else:
        from .symbols import SymbolIndex, build_index
        if a.scmd == "index":
            syms = build_index(a.src)
            open(a.out, "w").write("\n".join(syms) + "\n")
            print(f"{len(syms)} symbols -> {a.out}")
        else:
            for s_ in SymbolIndex.load(a.index).search(*a.names, limit=a.n):
                print(s_)
    return 0


if __name__ == "__main__":
    sys.exit(main())
