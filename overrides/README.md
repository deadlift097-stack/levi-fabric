# overrides

Fixes for things the converter cannot translate, kept **outside** the generated C++ so they survive every
re-conversion. One file per mod, named after the jar: `overrides/<jar-name>.json`.
The *Convert* workflow picks `overrides/<jar-name>.json` up automatically; locally use `--overrides`.

`*.example.json` files are suggestions and are **not** applied until you rename them to `.json`.

```json
{
  "calls": {
    "net.fabricmc.loader.api.FabricLoader.isModLoaded": { "returns": { "bool": false } },
    "some.mod.UpdateChecker.check": { "ignore": true, "reason": "no update server on Bedrock" },
    "some.mod.Feature.apply": { "cpp": "self.getLogger().info(\"applied {0}\");" }
  }
}
```

Key = `owner.method` (dotted) or `owner.method(descriptor)` to pick one overload.

| field | effect |
|---|---|
| `ignore: true` | drop the call; stays listed in the report as "ignored on purpose" with your `reason` |
| `returns: {"bool"/"int"/"str"/"double": v}` | fold the call to a constant |
| `cpp` | C++ spliced in place of the call (`{0}`, `{1}` = constant call arguments) |

`overrides.todo.json` (generated next to every conversion) already contains one empty entry per open item.
