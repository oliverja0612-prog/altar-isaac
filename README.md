# Altar

**The ultimate mod for The Binding of Isaac: Repentance / Repentance+.**
An in-game menu, 40 animated items, broken combos, a full command console, a
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
- **40 animated custom items** and **14 combos** with extra beams, black holes and lasers, including 8 Fallen Sky items (falling stars, stopped time, a void eye, rifts and a supernova)
- **Mod Manager app** (native C# / WPF): enable/disable mods, drag-and-drop .zip install, profiles, conflict checker, one-click Play, auto-update
- **Safe mode**: runs played with mods don't count - your save files are snapshotted when Isaac starts and put back when it closes
- **Installer** with auto-detect, shortcuts and an Apps & features uninstall entry

## OBLIVION, the voice from above

Your mother heard a voice from above. It wasn't God.

Type `oblivion` (or `hardest` to go straight to Floor 14). A flipbook story intro,
three forms (Oblivion → The Hollow Seraph → The Last Star), and when she falls,
she drags you into deep space for Form IV, where she reforms out of the stars.
Custom arenas, health bar and soundtrack, attack title cards, a time-stop killing
blow, and attacks built to break you: judgement pillars, starfall, a spinning
galaxy of shots, feather storms, homing void orbs, sweeping lasers, black holes,
and a Supernova you must escape. Her HP scales with your build and no single hit
takes more than 0.8%.

## Commands

```
give sad onion 2, cosmic overclock     spawn <item> [n]      hearts soul 6, red 2
boss <name> / bosshere <name>          oblivion              tp <room>   stage <floor>
char <name>   combo <name|all>         stat damage 10        heal; god; coins 99
hardest (or tp hardest): straight to OBLIVION on Floor 14     spikes: toggle Spike Shield
clear  map  reroll  charge  blackhole  nuke  q4 [n]  curses off  seed  help
```

Floor warps and debug toggles use the game's debug console, which disables achievements for that run.

## Repo layout

```
mods/altar_core/       the mod the game loads (Lua in scripts/, art in resources/)
AltarModManager/       Mod Manager (app/, C# WPF), installer (src/) and build tools (tools/)
```

Build everything with `python AltarModManager/tools/build.py --public`
(see [AltarModManager/README.md](AltarModManager/README.md)).

---

Altar is a free fan-made mod. Not affiliated with or endorsed by Edmund McMillen,
Nicalis or the makers of The Binding of Isaac. No game files are included.
