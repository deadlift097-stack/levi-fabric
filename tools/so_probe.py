#!/usr/bin/env python3
"""
so_probe.py - inspects libminecraftpe.so (aarch64 ELF) for the levipack hook work.
Usage:
  python3 so_probe.py libminecraftpe.so                       # report + symbols.json skeleton
  python3 so_probe.py libminecraftpe.so --classes Item,Actor,Mob,Player,GameMode,BlockLegacy,ScreenController
  python3 so_probe.py libminecraftpe.so --sig 0x1234abc       # ARM64 masked signature for a function
Needs: pip install pyelftools
Writes: symbols.json (build_id, vtables, exported hits). Not yet run against your .so - report any error text.
"""
import sys, re, json, struct, argparse
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection

def load(path):
    f = open(path, 'rb'); e = ELFFile(f); return f, e

def build_id(e):
    for s in e.iter_sections():
        if s.name == '.note.gnu.build-id':
            for n in s.iter_notes():
                if n['n_type'] == 'NT_GNU_BUILD_ID': return n['n_desc']
    return None

def v2off(e, va):
    for seg in e.iter_segments():
        if seg['p_type'] == 'PT_LOAD' and seg['p_vaddr'] <= va < seg['p_vaddr'] + seg['p_filesz']:
            return va - seg['p_vaddr'] + seg['p_offset']
    return None

def mangle_name(c):
    parts = c.split('::')
    body = ''.join(str(len(x)) + x for x in parts)
    return body if len(parts) == 1 else 'N' + body + 'E'

def rodata_names(f, e, want=None):
    """Find Itanium typeinfo-name strings for the wanted classes by direct byte search -> {mangled: va}"""
    out = {}
    secs = [s for s in e.iter_sections() if s.name in ('.rodata', '.data.rel.ro')]
    for s in secs:
        data = s.data(); base = s['sh_addr']
        for c in (want or []):
            needle = b'\x00' + mangle_name(c).encode() + b'\x00'
            i = data.find(needle)
            while i != -1:
                out.setdefault(mangle_name(c), base + i + 1)
                i = data.find(needle, i + 1)
    return out

def demangle(t):
    res = []; s = t
    i = 1 if t.startswith('N') else 0
    while i < len(s) and s[i].isdigit():
        j = i
        while j < len(s) and s[j].isdigit(): j += 1
        n = int(s[i:j]); res.append(s[j:j+n]); i = j + n
    return '::'.join(res) if res else t

def reloc_map(e):
    """Vectorised: returns dict-like object with .get(va). RELATIVE + ABS64 vs symbol."""
    import numpy as np
    dt = np.dtype([('off','<u8'),('info','<u8'),('add','<i8')])
    offs=[]; vals=[]
    dyn = e.get_section_by_name('.dynsym')
    symv = None
    for sec in e.iter_sections():
        if sec.name == '.rela.dyn':
            arr = np.frombuffer(sec.data(), dtype=dt)
            typ = arr['info'] & 0xffffffff; sym = arr['info'] >> 32
            m = (sym == 0) & ((typ == 1027) | (typ == 8))
            offs.append(arr['off'][m]); vals.append(arr['add'][m].astype('<u8'))
            m2 = (sym != 0) & ((typ == 257) | (typ == 1))
            if m2.any():
                if symv is None:
                    symv = np.frombuffer(dyn.data(), dtype=np.dtype([('n','<u4'),('i','u1'),('o','u1'),('sh','<u2'),('v','<u8'),('sz','<u8')]))['v']
                offs.append(arr['off'][m2]); vals.append((symv[sym[m2]] + arr['add'][m2].astype('<u8')))
    o = np.concatenate(offs) if offs else np.zeros(0,'<u8'); v = np.concatenate(vals) if vals else np.zeros(0,'<u8')
    order = np.argsort(o); o = o[order]; v = v[order]
    class RM:
        def get(self, va, default=None):
            i = np.searchsorted(o, va)
            return int(v[i]) if i < len(o) and o[i] == va else default
        def __contains__(self, va): return self.get(va) is not None
        def __getitem__(self, va): return self.get(va)
    rm = RM(); rm.o = o; rm.v = v
    return rm

def read_slots(f, e, rm, targets):
    """vectorised: for every 8-byte slot in data sections, resolved value in targets -> {value: [slot_va]}"""
    import numpy as np
    tg = np.array(sorted(targets), dtype='<u8'); hits = {}
    for s in e.iter_sections():
        if s.name in ('.data.rel.ro', '.data.rel.ro.local', '.data'):
            base = s['sh_addr']; data = s.data(); n = len(data) // 8
            arr = np.frombuffer(data[:n*8], dtype='<u8').copy()
            lo, hi = base, base + n * 8
            i0 = np.searchsorted(rm.o, lo); i1 = np.searchsorted(rm.o, hi)
            idx = ((rm.o[i0:i1] - base) // 8).astype(np.int64)
            arr[idx] = rm.v[i0:i1]
            pos = np.searchsorted(tg, arr); pos[pos >= len(tg)] = 0
            m = tg[pos] == arr
            for j in np.nonzero(m)[0]:
                hits.setdefault(int(arr[j]), []).append(base + int(j) * 8)
    return hits, rm

def find_vtables(f, e, want):
    names = rodata_names(f, e, want)
    sel = dict(names)
    rm = reloc_map(e)
    hits, _ = read_slots(f, e, rm, set(sel.values()))
    typeinfo = {}
    for t, nva in sel.items():
        for slot in hits.get(nva, []):
            typeinfo.setdefault(demangle(t), []).append(slot - 8)   # typeinfo = {vptr, name, ...}
    ti_set = {x for v in typeinfo.values() for x in v}
    hits2, _ = read_slots(f, e, rm, ti_set) if ti_set else ({}, rm)
    text = e.get_section_by_name('.text'); lo, hi = text['sh_addr'], text['sh_addr'] + text['sh_size']
    vt = {}
    for cls, tis in typeinfo.items():
        for ti in tis:
            for slot in hits2.get(ti, []):
                vptr = slot + 8                  # vptr points after offset_to_top + typeinfo
                first = vslot(f, e, rm, vptr, 0); ott = vslot(f, e, rm, slot - 8, 0)
                if first and lo <= first < hi and ott is not None and (ott < 0x10000 or ott > 0xFFFFFFFFFFF00000):
                    vt.setdefault(cls, []).append(vptr)
    return vt, rm, e

def vslot(f, e, rm, vptr, i):
    va = vptr + 8 * i
    if va in rm: return rm[va]
    o = v2off(e, va)
    if o is None: return None
    f.seek(o); return struct.unpack('<Q', f.read(8))[0]

def mask_sig(f, e, va, n=12):
    o = v2off(e, va); f.seek(o); words = struct.unpack('<%dI' % n, f.read(4 * n))
    toks = []; prev_adrp = False
    for w in words:
        m = 0
        if (w & 0x7C000000) == 0x14000000: m = 0x03FFFFFF              # B / BL
        elif (w & 0x9F000000) == 0x90000000: m = 0x60FFFFE0 & 0xFFFFFFFF; m = 0x60FFFFE0  # ADRP imm
        elif (w & 0x3B000000) == 0x18000000: m = 0x00FFFFE0            # LDR literal
        elif (w & 0x7E000000) == 0x34000000: m = 0x00FFFFE0            # CBZ/CBNZ
        elif (w & 0xFF000010) == 0x54000000: m = 0x00FFFFE0            # B.cond
        elif (w & 0x7E000000) == 0x36000000: m = 0x0007FFE0            # TBZ/TBNZ
        elif prev_adrp and ((w & 0x7F800000) == 0x11000000 or (w & 0x3B000000) == 0x39000000):
            m = 0x003FFC00                                              # ADD/LDR/STR imm12 after ADRP
        prev_adrp = (w & 0x9F000000) == 0x90000000
        b = struct.pack('<I', w); mb = struct.pack('<I', m)
        toks += ['??' if mb[k] else '%02X' % b[k] for k in range(4)]
    return ' '.join(toks)

def sig_unique(f, e, sig):
    pat = b''.join(b'.' if t == '??' else re.escape(bytes([int(t, 16)])) for t in sig.split())
    c = 0
    for s in e.iter_sections():
        if s.name == '.text':
            c += len(re.findall(pat, s.data(), re.S))
    return c

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('so')
    ap.add_argument('--classes', default='Item,Actor,Mob,Player,GameMode,BlockLegacy,ScreenController,Container,BlockActor,Dimension,Level,ClientInstance,Minecraft')
    ap.add_argument('--sig'); a = ap.parse_args()
    f, e = load(a.so)
    print('machine:', e['e_machine'], '| class:', e.elfclass)
    if a.sig:
        va = int(a.sig, 0); s = mask_sig(f, e, va)
        print('sig:', s); print('matches in .text:', sig_unique(f, e, s)); return
    bid = build_id(e); print('build-id:', bid)
    dyn = e.get_section_by_name('.dynsym')
    names = [s.name for s in dyn.iter_symbols()] if dyn else []
    mc = [n for n in names if n.startswith('_ZN') and ('4Item' in n or '5Actor' in n or '6Player' in n)]
    print('.dynsym entries:', len(names), '| game-looking Itanium names:', len(mc))
    print('.symtab present:', e.get_section_by_name('.symtab') is not None)
    want = set(a.classes.split(','))
    vt, rm, _ = find_vtables(f, e, want)
    out = {'build_id': bid, 'abi': 'arm64-v8a', 'vtables': {}, 'exports_sample': mc[:50]}
    for c in sorted(want):
        lst = vt.get(c, [])
        print(f'{c:18s} vtables: ' + (', '.join(hex(v) for v in lst) if lst else 'NOT FOUND (RTTI missing or nested name)'))
        if lst:
            out['vtables'][c] = {'rva': [hex(v) for v in lst],
                                 'slots0_8': [hex(vslot(f, e, rm, lst[0], i) or 0) for i in range(8)]}
    json.dump(out, open('symbols.json', 'w'), indent=2); print('wrote symbols.json')

if __name__ == '__main__': main()
