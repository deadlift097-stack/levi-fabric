# Bedrock resource pack (punchy) - client side

* animations: 230 converted, 4 wired to game states automatically, 226 left unmapped
* geometries: 6; sounds: 22; textures: 14; languages: en_US, pt_BR

Install: zip the `resource_pack/` folder as `.mcpack` (CI does this) or import it with the launcher. The animations are merged into the vanilla `player.entity.json` with `levipack-forge pack-merge` (the CI workflow does this automatically). **Not tested in-game.**

## Self-check
* all ids resolve inside the pack

## Bones with no vanilla Bedrock counterpart (dropped from animations)
* `camera` (5 animations): map it in `overrides/<jar>.json` -> `bone_map`

## Animations not wired to a game state yet
Give each one a Molang condition in `animation_conditions` (see `pack_map.todo.json`):
`attack`, `attack_1`, `attack_1-bk`, `attack_2`, `attack_3`, `attack_4`, `attack_5`, `attack_combo_double_1`, `attack_combo_double_2`, `attack_critical`, `attack_critical-bk`, `attack_dois-bk`, `attack_mace`, `attack_spear`, `attack_spear_v2`, `attack_spear_v2-bk`, `attack_tes-bk`, `attack_test`, `attack_trident`, `climb`, `climb2`, `crawl`, `disable_punchy_moves_fall`, `disable_punchy_moves_idle`, `disable_punchy_moves_walk`, `disable_punchy_moves_walk_backward`, `disable_punchy_moves_walk_left`, `disable_punchy_moves_walk_right`, `drink_end`, `drink_end2`, `drink_loop`, `drink_loop2`, `drink_start`, `drink_start2`, `dry_out_left`, `dry_out_left-bk`, `dry_out_right`, `dry_out_right-bk`, `dry_out_right-bk2`, `eat_end`, `eat_end2`, `eat_loop`, `eat_loop2`, `eat_start`, `eat_start2`, `falling_in_water`, `full_block_mining_end`, `full_block_mining_loop`, `full_block_mining_start`, `golden_dandelion_inspect`, `golden_dandelion_inspect3`, `hamster_dismount`, `hamster_head_shoulder`, `hamster_main_hand_shoulder`, `hamster_off_hand_shoulder`, `hamster_pet`, `hamster_pet2`, `hamster_throw_abbort`, `hamster_throw_abbort_head`, `hamster_throw_abbort_left_shoulder`, `hamster_throw_abbort_right_shoulder`, `hamster_throw_charge-test`, `hamster_throw_charge_head`, `hamster_throw_charge_left_shoulder`, `hamster_throw_charge_right_shoulder`, `hamster_throw_release`, `hand_in`, `hand_in-bk`, `hand_in_daggers`, `hand_in_punchy_cake`, `hand_in_punchy_gift`, `hand_in_spear`, `hand_in_spear-bk`, `hand_in_swo2rd-bk`, `hand_in_sword`, `hand_in_sword_pose_test`, `hand_out`, `hand_out-bk`, `hand_out_punchy_cake`, `hand_out_punchy_cake_placed` ...

## Not convertible
* animation oar_rest: unknown key 'oar' dropped
* resourcepacks/punchy/assets/punchycake/punchy/model_parts_items/animations/punchy_cake_item.animation.json: custom-item animation (needs a Bedrock item attachable)
* resourcepacks/punchy/assets/punchycake/punchy/model_parts_items/animations/punchy_gift_item.animation.json: custom-item animation (needs a Bedrock item attachable)
* resourcepacks/punchy/assets/punchycake/punchy/model_parts_items/definitions/punchy_birthday_candle.json: Java item model-part definition (Bedrock needs an item + attachable JSON)
* resourcepacks/punchy/assets/punchycake/punchy/model_parts_items/definitions/punchy_birthday_one.json: Java item model-part definition (Bedrock needs an item + attachable JSON)
* resourcepacks/punchy/assets/punchycake/punchy/model_parts_items/definitions/punchy_cake.json: Java item model-part definition (Bedrock needs an item + attachable JSON)
* resourcepacks/punchy/assets/punchycake/punchy/model_parts_items/definitions/punchy_gift.json: Java item model-part definition (Bedrock needs an item + attachable JSON)

