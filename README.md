# Altar

**The ultimate mod for The Binding of Isaac: Repentance / Repentance+.**
An in-game menu, 32 animated items, broken combos, a full command console, a
Geode-style mod manager and a secret final boss.

### [⬇ Download AltarSetup.exe (latest release)](../../releases/latest)

Run it, pick your Isaac folder (found automatically), install, start a run and press **F2**.
Windows SmartScreen may warn because the installer isn't code-signed: *More info → Run anyway*.

---

## Features

- **In-game menu (F2 / gem button)**: Windows 11-style window with Mods, Items, Give, Combos, Warp, Player, Debug, Console and Settings tabs
- **Item browser**: search every item (vanilla + mods), give or spawn any amount
- **Give**: every heart type, pickups, cards, pills, trinkets, stat boosts
- **Warp**: any room, any floor, or fight any boss (with portraits)
- **Player**: become any of 34 characters, add/remove curses
- **Command console (F4)**: cmd-style terminal, autocomplete, history, `;` chaining, Ctrl+V paste
- **32 animated custom items** and **9 combos** with extra beams, black holes and lasers
- **Mod Manager app**: enable/disable mods, profiles, conflict checker, one-click Play
- **Installer** with auto-detect, shortcuts and an Apps & features uninstall entry

## OBLIVION, Devourer of Stars

Type `oblivion` in the console. A hand-drawn flipbook story intro, three forms
(Oblivion → The Hollow Seraph → The Last Star), a custom arena, health bar and
soundtrack, and attacks built to break you: judgement pillars, feather storms,
homing void orbs, sweeping lasers, black holes, and a Supernova you must escape.
Her HP scales with your build and no single hit takes more than 0.8%.

## Commands

```
give sad onion 2, cosmic overclock     spawn <item> [n]      hearts soul 6, red 2
boss <name> / bosshere <name>          oblivion              tp <room>   stage <floor>
char <name>   combo <name|all>         stat damage 10        heal; god; coins 99
clear  map  reroll  charge  blackhole  nuke  q4 [n]  curses off  seed  help
```

Floor warps and debug toggles use the game's debug console, which disables achievements for that run.

## Repo layout

```
mods/altar_core/       the mod the game loads (Lua in scripts/, art in resources/)
AltarModManager/       Mod Manager + installer source (src/) and build tools (tools/)
```

Build everything with `python AltarModManager/tools/build.py --public`
(see [AltarModManager/README.md](AltarModManager/README.md)).

---

Altar is a free fan-made mod. Not affiliated with or endorsed by Edmund McMillen,
Nicalis or the makers of The Binding of Isaac. No game files are included.
