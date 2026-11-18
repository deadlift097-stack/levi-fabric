# Bedrock resource pack (punchy_moves) - client side

* animations: 0 converted, 0 wired to game states automatically, 0 left unmapped
* geometries: 0; sounds: 0; textures: 0; languages: en_US, pt_BR

Install: the pack ships **inside the `.levipack`** at `resources/minecraft_resource_packs/<Name>/` (`levipack-forge pack-install <project>`; `convert` runs it, and the CI workflow runs it again after `pack-merge`). It can also be zipped as a standalone `.mcpack` (CI does this). The animations are merged into the vanilla `player.entity.json` with `levipack-forge pack-merge` (the CI workflow does this automatically). **Not tested in-game.**

## Nothing to convert
This mod computes its animation in Java code, so there is no Bedrock animation data inside the jar. The pack only carries language files / icon. Author Bedrock animations by hand, or implement the behavior behind a native hook (see Hooks.cpp).

## Self-check
* all ids resolve inside the pack

## Not convertible
* assets/punchy_moves/shaders/core/entity_dither.fsh: Java GLSL shader (Bedrock uses materials; needs a native hook or a .material port)

