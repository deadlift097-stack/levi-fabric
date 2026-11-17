# Conversion report: Punchy (3.2b)

* Fabric mod id: `punchy`  ->  C++ namespace `punchy`, class `PunchyMod`
* Entrypoints: client: punchy.fabric.PunchyFabricClient.onInitializeClient
* Java classes in jar: 1218; methods fully converted: 2; stubs left for manual work: 1
* Handled automatically: 6; need a native game hook: 1; plain logic to port: 0
* Config fields imported from static Java fields: 56
* Language files converted: en_US.lang, pt_BR.lang

## What converted automatically
Straight-line entrypoint code: logger / System.out calls, Fabric lifecycle events (started/stopping -> `enable()` / `disable()`), static constants -> typed config.

### Auto-resolved (no manual work)
* `net.fabricmc.loader.api.FabricLoader.getModContainer` - answered from fabric.mod.json ('punchy' is this mod)
* `net.minecraft.network.chat.Component.literal` - text component -> plain string
* `net.fabricmc.fabric.api.resource.ResourceManagerHelper.registerBuiltinResourcePack` - no Bedrock equivalent: resources ship inside the pack, nothing reloads Java listeners
* `java.util.Optional.ifPresent` - callback inlined
* `punchy.client.command.PunchyCommands.register` - 4 client commands exposed as `cmd_*` launcher config fields (values are stored; a native hook must apply them)
* `Mod Menu config screen` - replaced by the typed config the launcher shows (config.json + schema)

## What needs manual work

### Needs a native game hook
* `punchy/fabric/PunchyFabricClient.onInitializeClient()V` - unsupported call punchy.client.PunchyClient.init()V
  * **Game API**: Needs a native hook (`<pl/memory/Hook.hpp>`). Run `levipack-forge symbols ...` and pass --symbols so each stub lists candidate Bedrock symbols, or declare a replacement in overrides.json.

## Bedrock resource pack (client side)
`resource_pack/` holds 230 animations (4 wired to game states), 6 geometries, 22 sounds, 14 textures. See `resource_pack/PACK_REPORT.md`.

## Native hooks
`src/mod/Hooks.cpp` lists every gap above as a hook entry (with Bedrock symbol candidates when `--symbols` is given); it is logged at start-up. Client commands were turned into `cmd_*` launcher config fields (8 fields from 4 commands).

## How to solve the open items without editing generated C++
Fill `overrides.todo.json` (one pre-made entry per open item), save it as `overrides/<mod>.json`, and run the conversion again (`--overrides overrides/<mod>.json`, or the workflow's `overrides` input). Fixes live outside the generated code, so they survive every re-conversion. See MANUAL_WORK.md.

## Not converted (by design)
Java classes other than the entrypoints, mixins, Minecraft Java API calls, textures/models/data packs. Bedrock has no Java classes; every game-facing call needs a native hook via `<pl/memory/Hook.hpp>` (see the symbol candidates printed next to each TODO when `--symbols` is supplied).
