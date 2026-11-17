# Manual work for Punchy Moves

Everything below is what levipack-forge could not convert. Each item has a ready fix path.

## Three ways to close an item

1. **Ignore it** - client-only visuals, key bindings, debug commands: set `"ignore": true` and a reason.
2. **Give a value** - version/capability queries: set `"returns": {"bool": false}` (or int/str/double).
3. **Give the C++ once** - set `"cpp": "..."` (`{0}`, `{1}` = call arguments). It is spliced in on every conversion.

Save the edited `overrides.todo.json` as `overrides/<mod>.json` in the converter repo and re-run.

Nothing to do.
