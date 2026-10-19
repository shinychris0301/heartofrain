# Task 06 — Production player settings menu and shipping scene list

Read `AGENTS.md`, FINDINGS PRJ-01/PRJ-02 and DECISIONS D9, D10, D11. Independent of tasks 02–05.
Branch: `codex/06-project-setup`.

## Background

`Unity/ProjectSettings/` contains only `EditorBuildSettings.asset` and `ProjectVersion.txt`. **Do not
hand-write `ProjectSettings.asset` or any other ProjectSettings YAML.** Unity's format is large and
version-specific. Instead, write an editor menu that applies the settings through the `PlayerSettings` API.
A human runs it once in Unity and commits the files Unity generates.

## Part A — editor menu

New file `Unity/Assets/HeartOfTheRain/Build/Editor/ProductionProjectSetup.cs`, with `.meta` files for the
file and for the new `Build` and `Build/Editor` folders. Namespace `HeartOfTheRain.Build.Editor`.

- `[MenuItem("Heart of the Rain/Build/Apply Production Player Settings")] public static void Apply()` sets
  the D10 values:
  - `PlayerSettings.companyName`, `PlayerSettings.productName`
  - `PlayerSettings.bundleVersion="0.1.0"`, `PlayerSettings.Android.bundleVersionCode=1`, `PlayerSettings.iOS.buildNumber="1"`
  - `PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Android,…)` and the same for `BuildTargetGroup.iOS`
  - `PlayerSettings.colorSpace=ColorSpace.Gamma`
  - Orientation (D9): `PlayerSettings.defaultInterfaceOrientation=UIOrientation.Portrait;` with
    `allowedAutorotateToPortrait=true` and `allowedAutorotateToPortraitUpsideDown`,
    `allowedAutorotateToLandscapeLeft` and `allowedAutorotateToLandscapeRight` all `false`.
  - Android: `SetScriptingBackend(BuildTargetGroup.Android,ScriptingImplementation.IL2CPP)`,
    `Android.targetArchitectures=AndroidArchitecture.ARM64`,
    `Android.minSdkVersion=AndroidSdkVersions.AndroidApiLevel26`,
    `Android.targetSdkVersion=AndroidSdkVersions.AndroidApiLevelAuto`
  - iOS: `SetScriptingBackend(BuildTargetGroup.iOS,ScriptingImplementation.IL2CPP)`, `iOS.targetOSVersionString="13.0"`
  - Finish with `AssetDatabase.SaveAssets();` and a `Debug.Log` summarising what was applied.
- Use the same API style as the existing `M48/Editor/M48ReviewMenu.cs` `Configure()`. It shows the
  `BuildTargetGroup` overloads this project already uses. Use only APIs available in Unity 2022.3. If you are
  unsure an API exists in 2022.3, leave it out and list it in the report instead of guessing.
- Do **not** call `EditorBuildSettings.scenes=` in this menu. Part B handles scenes.
- Do **not** modify `M48ReviewMenu.cs`.

## Part B — shipping scene list (D11)

Edit `Unity/ProjectSettings/EditorBuildSettings.asset` as text:
- For every scene entry **except** `path: Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity`,
  change `enabled: 1` to `enabled: 0`.
- Do not reorder, add or remove entries. Do not change any `guid:` and do not touch any other line.
- M65 stays at index 0 with `enabled: 1`.

## Part C — runbook note

Append a section "Production project settings" to `docs/codex/README.md` that tells the human to:
1. open the project in Unity 2022.3.62f3;
2. run the menu;
3. confirm in Player Settings;
4. commit `Unity/ProjectSettings/*` and `Unity/Packages/packages-lock.json`.

## Acceptance criteria

1. `git diff Unity/ProjectSettings/EditorBuildSettings.asset` shows only `enabled: 1` → `enabled: 0` changes (16 of them).
2. The new editor script references `UnityEditor` only from inside an `Editor/` folder, and compiles under C# 9.
3. The harness (if present) is still green. This task does not affect it.

## Human verification in Unity (copy into your report)

- [ ] Compiles. Menu `Heart of the Rain/Build/Apply Production Player Settings` exists.
- [ ] After running it, Player Settings show the D10 values, with Portrait only.
- [ ] Build Settings list only `M65_First_Start` as ticked.
- [ ] Commit the regenerated `ProjectSettings/*.asset` files and `Packages/packages-lock.json`.
- [ ] Make an Android development build and launch it on a device: it boots into First Start / Home.
