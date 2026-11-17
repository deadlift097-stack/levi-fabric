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
levipack_forge/        classfile parser, bytecode->C++ subset transpiler, symbol index, generator, CLI
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
