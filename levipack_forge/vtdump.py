"""Parser/analysis for tools/so_probe.py-style vtable dumps (docs/vtables_dump.txt).

Used to calibrate slots: diff a subclass against its base (overrides) and recognise
tiny getters by their first instructions. Findings must still be confirmed with a test hook.
"""
from __future__ import annotations
import re, pathlib

_HDR = re.compile(r"=== (\S+)\s+vptr RVA (0x[0-9a-f]+)\s+slots (\d+)")
_SLOT = re.compile(r"\s+\[(\d+)\] (0x[0-9a-f]+)\s+(.*)")

# (regex on first instructions, label)
SHAPES = [
    (r"^mov w0, wzr ; ret", "returns 0/false"),
    (r"^mov w0, #0x1 ; ret", "returns 1/true"),
    (r"^mov x0, xzr ; ret", "returns nullptr/0"),
    (r"^movi d0, #0+ ; ret", "returns 0.0f"),
    (r"^ret\b", "empty (void no-op)"),
    (r"^ldrh w0, \[x0, #(0x[0-9a-f]+)\] ; ret", "getter (u16) @ \\1"),
    (r"^ldr[bhs]* [wx]0, \[x0, #(0x[0-9a-f]+)\] ; ret", "getter of field @ \\1"),
    (r"^add x0, x0, #(0x[0-9a-f]+) ; ret", "returns &field @ \\1"),
    (r"^str[bhs]* [wsx]1, \[x0, #(0x[0-9a-f]+)\] ; ret", "setter of field @ \\1"),
]


def parse(path):
    """-> {class: [ {vptr, slots:{i:(rva, insns)}} ]}"""
    out, cur = {}, None
    for line in pathlib.Path(path).read_text().splitlines():
        m = _HDR.match(line)
        if m:
            cur = {"vptr": int(m.group(2), 16), "slots": {}}
            out.setdefault(m.group(1), []).append(cur)
            continue
        m = _SLOT.match(line)
        if m and cur is not None:
            cur["slots"][int(m.group(1))] = (int(m.group(2), 16), m.group(3).strip())
    return out


def shape(insns: str):
    for rx, label in SHAPES:
        m = re.match(rx, insns)
        if m:
            return m.expand(label)
    return None


def diff(dump, base, derived):
    """Slots where `derived` has a different target than `base` = derived's overrides (plus new slots)."""
    b, d = dump[base][0]["slots"], dump[derived][0]["slots"]
    rows = []
    for i, (rva, ins) in sorted(d.items()):
        if i not in b:
            rows.append((i, "new", rva, ins))
        elif b[i][0] != rva:
            rows.append((i, "override", rva, ins))
    return rows


def candidates(dump, cls, amethyst_idx, want=None, spread=(1, 2, 3)):
    """Candidate Itanium slots for an Amethyst/MSVC index (shift is +1..+3, not constant).
    `want` optionally filters by a shape substring such as 'returns 0'."""
    s = dump[cls][0]["slots"]
    rows = []
    for sh in spread:
        i = amethyst_idx + sh
        if i in s:
            sp = shape(s[i][1]) or ""
            if want is None or want in sp:
                rows.append((i, s[i][0], sp, s[i][1][:50]))
    return rows
