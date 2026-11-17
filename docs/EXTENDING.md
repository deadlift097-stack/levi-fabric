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
