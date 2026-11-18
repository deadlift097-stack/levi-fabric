"""Verified vtable-slot data for a specific libminecraftpe.so build.

Everything here was read from the binary (see docs/HOOKING.md); nothing is guessed.
Slots are keyed by the library's sha256 because Bedrock has no build-id and every
game update moves addresses. Itanium ABI: slots 0/1 are the two destructors.
"""
from __future__ import annotations
import json, pathlib
from importlib import resources as _res

DATA = "libminecraftpe-4de40e1d.symbols.json"

# Item slots confirmed by reading what the code does (ARM64) on build 4de40e1d...
# name -> (slot, target RVA from vtables_dump.txt, C++ signature, evidence)
VERIFIED_ITEM_SLOTS = {
    "getDescriptionId":   (5,  0x107999cc, "std::string const& (*)(void*)", "add x0,x0,#0x90 ; ret"),
    "getMaxUseDuration":  (6,  0x107a1284, "int (*)(void*, void*)",        "ldr w0,[x0,#0x114] ; ret"),
    "setMaxDamage":       (27, 0x107a0c88, "void* (*)(void*, int)",        "strh w1,[x0,#0x110] ; ret"),
    "canBeDepleted":      (33, 0x1079c2d8, "bool (*)(void*)",              "short@0x110 > 0 && flag@0x112 bit2"),
    "getMaxDamage":       (37, 0x1079f1d8, "int (*)(void*)",               "ldrh w0,[x0,#0x110] ; ret"),
    "getAttackDamage":    (38, 0x1079f1e0, "int (*)(void*)",               "mov w0,wzr ; ret"),
    "getAttackDamageBonus": (39, 0x1079f1e8, "float (*)(void*)",           "movi d0,#0 ; ret"),
    "isHandEquipped":     (40, 0x1079f28c, "bool (*)(void*)",              "ldrb [x0,#0x112]; ubfx #1"),
}

# Java (Yarn/Mojang) method name -> verified Item slot name
JAVA_TO_ITEM = {
    "getAttackDamage": "getAttackDamage", "getMaxDamage": "getMaxDamage", "getMaxCount": None,
    "getMaxUseTime": "getMaxUseDuration", "isDamageable": "canBeDepleted",
    "isHandEquipped": "isHandEquipped", "getTranslationKey": "getDescriptionId",
}


def load(path=None) -> dict:
    if path:
        return json.loads(pathlib.Path(path).read_text())
    return json.loads(_res.files("levipack_forge").joinpath("data", DATA).read_text())


def vptr(db: dict, cls: str, index: int = 0):
    v = db.get("vtables", {}).get(cls) or []
    return int(v[index]["vptr_rva"], 16) if index < len(v) else None


def item_hook_for(java_call: str):
    """'net.minecraft.item.Item.getAttackDamage()F' -> (name, slot, target_rva, sig) or None."""
    import re
    m = re.search(r"([\w.$]+)\.(\w+)\(", java_call)
    if not m or not m.group(1).endswith("Item"):
        return None
    name = JAVA_TO_ITEM.get(m.group(2))
    if not name:
        return None
    slot, rva, sig, _ = VERIFIED_ITEM_SLOTS[name]
    return name, slot, rva, sig


def cpp_table(db: dict) -> str:
    """C++ rows for the generated Hooks.cpp (only verified slots)."""
    base = vptr(db, "Item")
    return "\n".join(
        f'        {{"Item::{n}", {base:#x}, {s}, {r:#x}, nullptr}},'
        for n, (s, r, _sig, _e) in VERIFIED_ITEM_SLOTS.items())


# Item field offsets read from the getters/setters above (build 4de40e1d...). MSVC/Amethyst offsets do NOT apply.
ITEM_LAYOUT = {"maxDamage_u16": 0x110, "flags_u8": 0x112, "maxUseDuration_i32": 0x114}


def cpp_layout() -> str:
    """C++ accessors for the verified Item fields (raw offsets; only valid when the build check passed)."""
    return "\n".join(f"constexpr size_t kItem_{k.rsplit('_', 1)[0]} = {v:#x};" for k, v in ITEM_LAYOUT.items())
