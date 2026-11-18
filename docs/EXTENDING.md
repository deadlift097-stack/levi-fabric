# Extending the transpiler

* Call mapping lives in `Transpiler._call` (`levipack_forge/transpile.py`). Add a rule that returns C++ lines
  appended to `lines`; return a stack value if the Java method returns something.
* Unsupported bytecode must call `self._todo(...)` so it shows up in the report. Never drop code silently.
* Typical next steps: string concatenation (`StringConcatFactory`), `if (config.flag)` guards mapped to
  `mConfig` checks, command registration, item-use / tick events via `pl::memory::Hook`.

## v0.2 routing order in `Transpiler._call`

1. `overrides.json` (user fixes always win) 2. `_fabric` (Loader/metadata/Optional folded from fabric.mod.json)
3. `_tokens` (Component/Identifier -> string) 4. `_by_design` (no Bedrock equivalent, reported) 5. `_inline`
(in-jar helpers with no game calls and no branches) 6. stub: `gap` if it touches the game, else `manual`.
Add advice for a new category in `levipack_forge/solutions.py` (`RULES`).

## v0.3 modules
* `commands.py` - Brigadier command tree -> `cmd_*` config fields.  * `hooks.py` - Hooks.h/.cpp registry.
* `bedrock_pack.py` - resource pack; edit `STATE_RULES` (animation name -> Molang) and `BONE_MAP` (Java rig -> Bedrock bones).

## v0.4 vtable hooks (Android, measured)
* `vtable.py` holds the **verified** Item slots for build sha256 `4de40e1d…` (`docs/HOOKING.md`, `docs/vtables_dump.txt`).
  Amethyst's MSVC indices do not transfer; add a slot only after reading its code in the dump and confirming with a test hook.
* Generated `Hooks.cpp` finds the module base from `/proc/self/maps` and only returns a slot target when it equals the
  expected RVA, so a different game build disables native hooks instead of crashing.
* New game build: run `tools/so_probe.py`, add `data/libminecraftpe-<sha8>.symbols.json`, recalibrate slots.
* Not done yet: subclass vtables (swords), non-virtual functions (Minecraft::update, registerItems), and the actual
  inline-hook call (`HOOK-POINT`), which needs the LeviLauncher Hook API verified on a device.

## Calibrating more slots (v0.4+)
* `levipack-forge vtdiff docs/vtables_dump.txt Actor Mob --only-shapes` lists Mob's overrides/new slots, tiny getters labelled.
* `levipack-forge slotguess docs/vtables_dump.txt Item 35 --want "returns 0"` lists Android candidates for an Amethyst index (shift +1..+3).
* Add a confirmed slot to `VERIFIED_ITEM_SLOTS` in `vtable.py`; the test suite cross-checks it against the dump.
