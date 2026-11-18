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
    c.add_argument("--symbols", help="symbol index (.txt), libminecraftpe.so, the zip containing it, or a *.symbols.json (default: the bundled DB)")
    c.add_argument("--mod-id")
    c.add_argument("--overrides", help="overrides.json with fixes for unsupported calls (survives re-conversion)")

    s = sub.add_parser("symbols", help="work with the Bedrock symbol index")
    ss = s.add_subparsers(dest="scmd", required=True)
    i = ss.add_parser("index", help="build symbols.txt from libminecraftpe.so / zip")
    i.add_argument("src"); i.add_argument("-o", "--out", default="symbols.txt")
    q = ss.add_parser("search", help="find mangled names containing all given identifiers")
    q.add_argument("index"); q.add_argument("names", nargs="+"); q.add_argument("-n", type=int, default=20)

    pm = sub.add_parser("pack-merge", help="merge resource_pack/player.entity.patch.json into the vanilla player.entity.json")
    pm.add_argument("patch"); pm.add_argument("vanilla"); pm.add_argument("-o", "--out", required=True)

    pi = sub.add_parser("pack-install", help="copy resource_pack/ into resources/minecraft_resource_packs/<Name>/ so the .levipack ships it")
    pi.add_argument("project", help="generated project folder (contains levipack.project.json)")
    pi.add_argument("--force", action="store_true", help="install even if the pack has no content besides the manifest")

    lt = sub.add_parser("live-test", help="generate the on-device proof project: hooks Item::getAttackDamage and adds N")
    lt.add_argument("-o", "--out", default="live-test"); lt.add_argument("--bonus", type=int, default=3)
    lt.add_argument("--mc-versions"); lt.add_argument("--symbols", help="a *.symbols.json (default: the bundled DB)")

    a = ap.parse_args(argv)
    if a.cmd == "live-test":
        from .livetest import generate
        r = generate(a.out, a.bonus, a.mc_versions, a.symbols)
        print(json.dumps(r, indent=2)); print(f"\nRead {r['out']}/LIVE_TEST.md, then build (push to GitHub: live-test workflow, or scripts/package.ps1).")
    elif a.cmd == "convert":
        from .generator import convert
        r = convert(a.jar, a.out, a.mc_versions, a.symbols, a.mod_id, a.overrides)
        print(json.dumps(r, indent=2))
        print(f"\nNext: read {r['out']}/CONVERSION_REPORT.md, then build (see README).")
    elif a.cmd == "pack-merge":
        from .bedrock_pack import merge_player_entity
        v = json.load(open(a.vanilla, encoding="utf-8-sig"))
        m = merge_player_entity(v, json.load(open(a.patch, encoding="utf-8")))
        json.dump(m, open(a.out, "w", encoding="utf-8"), indent=1)
        print(f"merged -> {a.out}")
    elif a.cmd == "pack-install":
        import pathlib
        from .bedrock_pack import install_pack
        proj = pathlib.Path(a.project)
        meta = proj / "levipack.project.json"
        mid = json.loads(meta.read_text())["mod_id"] if meta.exists() else proj.resolve().name
        dst = install_pack(proj, mid, only_if_content=not a.force)
        print(f"installed -> {dst}" if dst else "nothing to install (no resource_pack/ or it only has a manifest)")
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
