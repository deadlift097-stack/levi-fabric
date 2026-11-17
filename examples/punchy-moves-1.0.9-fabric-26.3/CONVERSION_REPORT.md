# Conversion report: Punchy Moves (1.0.9)

* Fabric mod id: `punchy_moves`  ->  C++ namespace `punchy_moves`, class `PunchyMovesMod`
* Entrypoints: main: punchymoves.fabric.PunchyMovesFabric.onInitialize
* Java classes in jar: 362; methods fully converted: 2; stubs left for manual work: 0
* Handled automatically: 9; need a native game hook: 0; plain logic to port: 0
* Config fields imported from static Java fields: 32
* Language files converted: en_US.lang, pt_BR.lang

## What converted automatically
Straight-line entrypoint code: logger / System.out calls, Fabric lifecycle events (started/stopping -> `enable()` / `disable()`), static constants -> typed config.

### Auto-resolved (no manual work)
* `net.fabricmc.loader.api.FabricLoader.getModContainer` - answered from fabric.mod.json ('punchy_moves' is this mod)
* `java.util.Optional.orElseThrow` - unwrapped at convert time
* `net.fabricmc.loader.api.FabricLoader.isModLoaded` - folded to false: 'jei' cannot be loaded next to a native Bedrock mod
* `punchymoves.client.compat.SpatialGuiSettings.setJeiLoaded` - plain Java helper without game calls: inlined
* `net.fabricmc.loader.api.Version.getFriendlyString` - answered from fabric.mod.json
* `punchymoves.client.MovesClient.initialize` - ignored on purpose (Java game-version query + update notification; nothing to check on Bedrock)
* `net.fabricmc.fabric.api.resource.ResourceManagerHelper.get` - no Bedrock equivalent: resources ship inside the pack, nothing reloads Java listeners
* `new punchymoves.fabric.PunchyMovesFabric$1` - object token only (no native state needed)
* `net.fabricmc.fabric.api.resource.ResourceManagerHelper.registerReloadListener` - no Bedrock equivalent: resources ship inside the pack, nothing reloads Java listeners

## What needs manual work
* nothing flagged

## Bedrock resource pack (client side)
`resource_pack/` holds 0 animations (0 wired to game states), 0 geometries, 0 sounds, 0 textures. See `resource_pack/PACK_REPORT.md`.

## Native hooks
`src/mod/Hooks.cpp` lists every gap above as a hook entry (with Bedrock symbol candidates when `--symbols` is given); it is logged at start-up. Client commands were turned into `cmd_*` launcher config fields (0 fields from 0 commands).

## How to solve the open items without editing generated C++
Fill `overrides.todo.json` (one pre-made entry per open item), save it as `overrides/<mod>.json`, and run the conversion again (`--overrides overrides/<mod>.json`, or the workflow's `overrides` input). Fixes live outside the generated code, so they survive every re-conversion. See MANUAL_WORK.md.

## Not converted (by design)
Java classes other than the entrypoints, mixins, Minecraft Java API calls, textures/models/data packs. Bedrock has no Java classes; every game-facing call needs a native hook via `<pl/memory/Hook.hpp>` (see the symbol candidates printed next to each TODO when `--symbols` is supplied).
