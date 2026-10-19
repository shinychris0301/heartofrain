# Task 08 (GATED) — Mobile texture compression

**Do not run this task unless `docs/codex/DECISIONS.md` D12 says `CONFIRMED`.** If it does not, reply
"D12 not confirmed" and stop.

Read `AGENTS.md` and FINDINGS PRJ-03. Branch: `codex/08-mobile-textures`.

## Part A — report first (no file changes)

Produce a table of every `AssetPostprocessor` under `Unity/Assets` that touches textures. For each one give:
- the path scope;
- what it forces;
- which validator menus reject compressed textures (for example, `App/PreLevel/Editor/PreLevelReview.cs`
  and `App/EndLevel/Editor/EndLevelReview.cs`), with the exact condition each one checks.

Also list textures larger than 2048 px on either side (read the PNG header bytes, not the `.meta`).

## Part B — implement

- In each project import policy that currently sets `overridden=false` for `"Android"` / `"iPhone"`, set a
  platform override instead:
  `overridden=true`, `format=TextureImporterFormat.<D12 block size, default ASTC_6x6>`,
  `compressionQuality=100`, and `maxTextureSize` equal to the default platform's `maxTextureSize`.
  Leave the default and `"Standalone"` settings uncompressed, exactly as today.
- Update the validators so that they check the **default** platform settings only, and accept compressed
  Android/iOS overrides. Keep every other check they perform.
- Do not change `M48/Editor/M48TextureImport.cs`; it already does this for M48 textures.
- Do not edit `.png.meta` files by hand. Unity rewrites them on reimport.

## Acceptance criteria

1. Only Editor scripts change.
2. The report explains why each validator change keeps the original fidelity intent (Editor/Standalone review uncompressed).

## Human verification in Unity (copy into your report)

- [ ] Compiles. Run `Assets > Reimport All` (slow), or reimport the affected folders.
- [ ] Switch the platform to Android: textures show ASTC in the inspector. Art review on device is approved by the art owner.
- [ ] The existing review validators still pass in the Editor.
- [ ] Commit the updated `.png.meta` files.
