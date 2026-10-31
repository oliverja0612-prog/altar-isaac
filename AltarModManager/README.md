# Altar

In-game menu, command console, combos and 40 animated custom items for
The Binding of Isaac: Repentance(+), plus a Geode-style mod manager and installer.

## Sharing with friends

Send them **`dist/AltarSetup.exe`**. They run it, pick their Isaac folder (Steam
installs are found automatically) and click Install. It sets up:

- `mods/altar_core` inside their Isaac folder
- `Altar.exe` (Mod Manager) in `%LOCALAPPDATA%\Programs\Altar`
- Desktop and Start menu shortcuts (optional)
- An "Apps & features" entry so it can be uninstalled normally

The exe is not code-signed, so Windows SmartScreen may say "Windows protected your PC".
Click **More info → Run anyway**.

## In game

| Key | Does |
|---|---|
| F2 / gem button | Altar menu: Mods, Items, Give, Combos, Warp, Player, Debug, Console, Settings |
| F3 | Live stat overlay |
| F4 | Command console |
| `~` console | `altar <command>` works there too |

Commands: `help`, `give <item> [n]`, `spawn <item> [n]`, `boss <name>`, `bosshere <name>`,
`bosses`, `tp <room>`, `stage <floor>`, `char <name>`, `combo <name|all|list>`,
`hearts <type> [n]`, `coins|bombs|keys [n]`, `stat <name> <value>`, `heal`, `god`,
`phase`, `clear`, `map`, `reroll`, `charge`, `blackhole`, `nuke`, `curses [off|name]`,
`q4 [n]`, `seed`, `die`.

Several items at once: `give sad onion 2, cosmic overclock, black hole core 3`
(also works for `spawn` and `hearts`). Several commands at once: `heal; god; coins 99`.

Floor warps and debug toggles use the game's own debug commands, which disable
achievements for that run.

## OBLIVION (secret boss)

`oblivion` in the console (or Warp > Bosses, first card) teleports you to the boss
room and plays the intro. Three phases with interludes, HP scales with your DPS
(about two minutes of perfect damage), and a death sequence that drops three
quality 4 items, Event Horizon, a golden chest and coins. ENTER skips the intro.
`oblivion here` fights it in the current room.

## Project layout

```
mods/altar_core/            the mod (what the game loads)
  main.lua                  bootstrap + shared helpers + item catalogue
  scripts/altar_items.lua   item effects, black hole tears, animated pedestals
  scripts/altar_fallen_sky.lua Fallen Sky items + the pickup burst every item gets
  scripts/altar_combos.lua  Event Horizon + combo effects
  scripts/altar_commands.lua commands, bosses, rooms, floors, characters
  scripts/altar_oblivion.lua OBLIVION boss AI and cutscenes
  scripts/altar_ui.lua      the in-game menu
  scripts/altar_data.lua    generated item list
  content/                  items.xml, itempools.xml, entities2.xml (items.xml + pools generated)
AltarModManager/
  app/                      Mod Manager + setup wizard (C# / WPF, one exe):
    MainWindow.xaml(.cs)    the manager            SetupWindow.xaml(.cs)  install / update / uninstall
    Core/                   config, mods, game detection, installer, safe mode, crash reports
  src/altar_sounds.py       sounds.xml writer used by the build tools
  tools/gen_items.py        item table -> items.xml, itempools.xml, altar_data.lua
  tools/make_sprites.py     all pixel art, VFX strips, icons
  tools/make_oblivion.py    OBLIVION sprite sheet, anm2 and portrait
  tools/build.py            builds dist/AltarSetup.exe (and the same exe as Altar.exe)
  assets/                   generated app art
```

## Building

```
python tools/build.py            # regenerate art + data, build both exes
python tools/build.py --skip-art # just rebuild the exes
```

PyInstaller is installed into its own venv at `%LOCALAPPDATA%\AltarBuild\venv`.

To add an item: add a row to `tools/gen_items.py`, draw it in `tools/make_sprites.py`
(a function named after its key), give it an effect in `scripts/altar_items.lua`, then build.
