# KR12.2 Windows — runtime/resource compatibility hotfix

## Source of the report

A user installing KR12.1 reported an OpenMW fatal error:

```
Trying to retrieve a non-existing setting: [HUD] mouse emulation cursor.
```

After switching to KR12, they separately reported a pink screen/cursor and
`Failed to start new game: Resource 'meshes/base_anim.nif' not found`.

Report: https://m.dcinside.com/board/skyrim/278450

A different user's workaround was to retain KR12 and copy over only the
KR12.1 ESP and Siege at Firemoth CEL. That is useful evidence but does not
prove that either workaround fixes all installations.

## Source-backed defect

- KR12.1's `openmw.exe` was rebuilt from Korean-fork source while the package
  otherwise retained KR12 resources and installer assets.
- The KR12.1 source has `[HUD] mouse emulation cursor = true` in
  `files/settings-default.cfg`; OpenMW 0.51.0's official default file lacks it.
- KR12.1's `openmw_hud.layout` adds `MouseEmulationCursor`.
- KR12.1's `openmw_hud_box.skin.xml` defines `HUD_MouseEmulationCursor`
  and requires `textures/omw_mouse_emulation_cursor.dds`.
- The old `install-korean.ps1` installed only the executable, fonts, and Korean
  data, not these matching engine resources.

KR12.2 candidates preserve the existing KR12.1 executable and ESP, and add
those exact four runtime assets from the KR12.1 Git tag, plus a corrected
installer with backup support.

## Gates before a public release

1. Download the `KR12.2-Windows-RC-not-for-public-release` workflow artifact
   and confirm the package verification JSON reads `package_integrity: PASS`.
2. In a clean Windows installation, install **official OpenMW 0.51.0** and
   configure a **legitimate Morrowind Data Files directory** with its archives.
   Confirm the vanilla game launches before the Korean overlay.
3. Install the KR12.2 candidate with `Install-Korean.bat`. Confirm the
   installer succeeds, backs up old overwritten files, and installs the four
   matching runtime assets under the correct paths.
4. Launch the game and confirm the `[HUD] mouse emulation cursor` fatal error
   no longer occurs. Check HUD, cursor image and main menu visuals.
5. Start a new game, enter the world, and inspect the `openmw.log` for
   missing resources. In particular, verify `Morrowind.bsa` is registered
   and `meshes/base_anim.nif` is accessible from **original game data**.
   Do not attribute this separate missing-base-game-data error to Korean ESP.
6. Upgrade a working KR12.1 install in a separate test environment and ensure
   the original config, other mod paths, mod order and backup files survive.
7. Verify preexisting KR12.1 translation fixes (spell duration text, range
   labels, Dro'Sakhar dialogue links, and Firemoth cell names).
8. Publish the KR12.2 GitHub release **only after** manual Windows gameplay
   verification. Update README and release notes with supported installation
   prerequisites; publish Nexus only after verifying the exact same ZIP SHA.

**Current status:** release candidate only. No in-game confirmation yet.
