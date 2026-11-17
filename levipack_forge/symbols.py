"""Bedrock symbol index built from libminecraftpe.so (or a zip containing it).

The mangled-name regex works on stripped and even truncated binaries, so the
index is usable with partial uploads. Hints are heuristic: Java (Yarn/Mojang)
names do not always equal Bedrock's C++ names.
"""
from __future__ import annotations
import re, struct, zlib, pathlib

_SYM = re.compile(rb"_ZN[0-9A-Za-z_]{6,400}")


def rescue_zip(path, member_suffix=".so"):
    """Yield (name, bytes, complete) for members of a possibly truncated zip."""
    d = pathlib.Path(path).read_bytes()
    i = 0
    while True:
        i = d.find(b"PK\x03\x04", i)
        if i < 0:
            return
        _, flag, comp, _, _, _, cs, us, nl, el = struct.unpack("<HHHHHIIIHH", d[i + 4:i + 30])
        name = d[i + 30:i + 30 + nl].decode("utf-8", "replace")
        start = i + 30 + nl + el
        if comp == 0:
            yield name, d[start:start + us], True
            i = start + us
            continue
        dec = zlib.decompressobj(-15)
        out = b""; pos = start; ok = True
        while pos < len(d) and not dec.eof:
            try:
                out += dec.decompress(d[pos:pos + (1 << 20)])
            except zlib.error:
                ok = False; break
            pos += 1 << 20
        yield name, out, ok and dec.eof
        i = start + max(cs, 1) if cs < len(d) else len(d)
        if not dec.eof:
            return


def build_index(path):
    p = pathlib.Path(path)
    blobs = []
    if p.suffix == ".zip":
        for name, data, _ in rescue_zip(p):
            if name.endswith(".so"):
                blobs.append((name, data))
    else:
        blobs.append((p.name, p.read_bytes()))
    syms = set()
    for name, data in blobs:
        if "minecraftpe" not in name and len(blobs) > 1:
            continue
        syms.update(m.group().decode() for m in _SYM.finditer(data))
    return sorted(syms)


class SymbolIndex:
    def __init__(self, symbols):
        self.symbols = list(symbols)

    @classmethod
    def load(cls, path):
        p = pathlib.Path(path)
        if p.suffix in (".zip", ".so"):
            return cls(build_index(p))
        return cls(l.strip() for l in p.read_text().splitlines() if l.strip())

    def search(self, *needles, limit=8):
        keys = [f"{len(n)}{n}" for n in needles if n]
        out = [s for s in self.symbols if all(k in s for k in keys)]
        return out[:limit]

    def hints_for(self, what: str):
        # "unsupported call net.minecraft.entity.player.PlayerEntity.jump()V"
        m = re.search(r"call ([\w.$]+)\.(\w+)\(", what)
        if not m:
            return []
        cls = m.group(1).rsplit(".", 1)[-1]
        return self.search(cls, m.group(2), limit=3)
