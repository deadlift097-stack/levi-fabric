# levipack-forge

Turn a **Fabric (Java) mod `.jar`** into a **LeviLauncher Android native-mod project** that GitHub Actions
builds into a `.levipack` for Minecraft Bedrock.

It is built on the official *LeviLauncher Android mod template* (kept untouched in
`reference/levilauncher-android-mod-template`, and copied into every generated project):
`preload-native` manifest, `PL_REGISTER_MOD` lifecycle (`load/enable/disable/unload`), typed
`pl::config` config + schema, preloader-android 0.2.2, NDK 28.2, arm64-v8a + armeabi-v7a.

## Quick start

```bash
pip install -e .
levipack-forge convert my-mod.jar -o out --mc-versions '["1.26.*"]'
cat out/CONVERSION_REPORT.md        # what was converted, what is a TODO
cd out && ./scripts/package.ps1 -Abi all   # or push `out` to GitHub and let Actions build
```

Or fully in the cloud: put the jar in `mods/`, run the **Convert Fabric mod -> .levipack** workflow
(`Actions` tab). You get the `.levipack` files, the report and the generated C++ project as artifacts.

## Closing the "needs manual work" items (v0.2)

Every item the converter used to flag is now sorted into one of three buckets in `CONVERSION_REPORT.md`:

| Bucket | What happens |
|---|---|
| **Auto-resolved** | `FabricLoader` / `ModContainer` / `ModMetadata` / `Optional` calls are folded into constants from `fabric.mod.json` (`isModLoaded("other-mod")` -> `false`, version -> the manifest version). Resource-reload listeners and builtin resource packs are dropped as having no Bedrock equivalent. Text components / resource ids become plain strings. Plain-Java helpers that never touch the game are inlined. All of it is listed, nothing is dropped silently. |
| **Needs a native game hook** | Code that touches Minecraft/Fabric-API classes (transitively). Stub is emitted as `// GAP(levipack-forge)`, the report gives a category (commands, rendering, keybinds, ...) and a concrete way to solve it, and the mod logs one runtime warning so the gap is visible in-game. |
| **Plain logic to port** | Branches/loops/objects outside the transpiler subset. |

**No C++ editing needed:** `overrides.todo.json` is generated with one entry per open item. Decide per item
(`ignore`, `returns`, or `cpp`), save it as `overrides/<jar-name>.json`, re-run. The fixes live outside the generated
code, so re-converting a new mod version never loses them. See `overrides/README.md` and the generated `MANUAL_WORK.md` checklist.

```bash
levipack-forge convert mods/punchy-3.2b-fabric-26.3.jar -o out --overrides overrides/punchy-3.2b-fabric-26.3.json
```

Honest limit: code that really drives the Java game (rendering, animation, input) has no Bedrock counterpart to
translate to; it needs native hooks or a Bedrock resource/behavior pack. The tool makes those items explicit,
safe at runtime and fixable from data files instead of hand-edited C++.

## Native hooks + client-side Bedrock resource pack (v0.3)

Every conversion now also produces:

| Output | What it is |
|---|---|
| `resource_pack/` | A **client-side Bedrock resource pack** (`manifest.json`, animations, geometries, sounds, textures, `.lang`). Blockbench-style Java animations are re-targeted to Bedrock names and bones (`right_arm` -> `rightArm`, ...). Animations that match a game state (sprint, swim, jump, riding...) get a generated animation controller with a Molang condition; the rest are listed in `pack_map.todo.json`. `player.entity.patch.json` is merged into Mojang's vanilla `player.entity.json` by `levipack-forge pack-merge` (the workflow does it and uploads a `.mcpack`). |
| `src/mod/Hooks.cpp` | A native **hook registry**: one row per Java feature with no automatic equivalent, with Bedrock symbol candidates when you pass `--symbols`, logged at start-up, plus one `HOOK-POINT` where the verified hook goes (`<pl/memory/Hook.hpp>`). |
| `cmd_*` config fields | Java client commands (`/punchy pos x y z`, ...) become typed launcher config fields. They reserve slots before static constants fill the config. The value is stored; a hook has to apply it. |
| `resource_pack/PACK_REPORT.md` | What was converted, a self-check that every id resolves inside the pack, dropped bones, unmapped animations, non-convertible items. |

`overrides/<jar>.json` also accepts `animation_conditions` (`{"anim_name": "molang"}` or `"ignore"`) and `bone_map`.
`overrides/punchy-*.json` are the real overrides for the two bundled mods; `*.example.json` are kept untouched.

```bash
levipack-forge convert mods/punchy-3.2b-fabric-26.3.jar -o out --overrides overrides/punchy-3.2b-fabric-26.3.json --symbols symbols.txt
levipack-forge pack-merge out/resource_pack/player.entity.patch.json vanilla/player.entity.json -o out/resource_pack/entity/player.entity.json
```

Status: unit-tested structure and self-check only; **not tested in-game**. Mods that compute animation in Java code
(Punchy Moves) have no Bedrock animation data to convert, so their pack is nearly empty and the work stays in hooks.

## What it really converts

Java and Bedrock are different games with different engines. There is no Java runtime inside Bedrock,
so a Fabric mod cannot be translated 1:1. levipack-forge converts what has a faithful native equivalent and
**flags everything else instead of guessing**:

| Java (from bytecode) | Becomes |
|---|---|
| `fabric.mod.json` id/name/version/authors/icon | `manifest.json`, CMake defaults, package icon |
| `ModInitializer.onInitialize` straight-line code | C++ in `enable()` (`TODO` after the first loop/branch) |
| SLF4J / Log4j `LOGGER.info/warn/error(...)`, `System.out.println` | `getLogger().info/warn/error(...)` (fmt `{}` kept) |
| `ServerLifecycleEvents` / `ClientLifecycleEvents` started/stopping | inlined into `enable()` / `disable()` |
| static `boolean/int/long/double/String` fields | typed `ModConfig` + `config.json` + schema (editable in the launcher) |
| `assets/*/lang/*.json` | `resources/texts/*.lang` (**experimental**: packaged, not verified that the launcher reads it) |
| Everything touching Minecraft Java classes, mixins, items/blocks/entities, textures/models, data packs | **`TODO(levipack-forge)` stub** + line in `CONVERSION_REPORT.md` |

For game-facing stubs you need native hooks (`<pl/memory/Hook.hpp>`, `Signature.hpp`). Supply Bedrock's
symbols and each TODO lists candidate mangled names:

```bash
levipack-forge symbols index minecraft_so_file.zip -o symbols.txt   # works on stripped/truncated libs too
levipack-forge symbols search symbols.txt Player jump
levipack-forge convert my-mod.jar -o out --symbols symbols.txt
```

Symbol hints are heuristic (Yarn/Mojang names are not always Bedrock's names). Check them against the
exact Bedrock version before hooking.

## Layout

```
levipack_forge/        classfile parser, bytecode->C++ subset transpiler, solutions (fix advice), symbol index, generator, CLI
overrides/             per-mod fixes for unsupported calls (survive re-conversion)
examples/              sample reports generated from the two bundled jars
levipack_forge/template/   the official template files used for every generated project
reference/             pristine copy of the uploaded template
.github/workflows/     ci.yml (tests), convert.yml (jar -> .levipack in the cloud)
tests/                 unit tests + a compiled sample Fabric mod
```

## Status / honesty

* Parser, transpiler subset, generator, symbol index: unit-tested (`pytest`).
* The generated C++ follows the template's API exactly but has **not been compiled against the Android NDK
  in this repo's authoring environment** (no NDK/network there). Run the workflow once and fix anything it reports.
* The mod-menu API (`<pl/ModMenu.hpp>`) is not used; the typed config is what the launcher exposes.
