"""Generates content/items.xml, content/itempools.xml and scripts/altar_data.lua
for Altar Core from the single ITEMS table below. Edit here, then run:

    python gen_items.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.join(os.path.dirname(os.path.dirname(HERE)), "mods", "altar_core")

# key, name, pickup text, menu description, active charges (0 = passive), cache flags, pools
ITEMS = [
    ("cosmic_overclock", "Cosmic Overclock", "Your body runs at 400%", "Damage x2 +2, tears x2, +0.3 speed, rainbow tears. Stacks.", 0, "damage firedelay speed", ["treasure"]),
    ("black_hole_core", "Black Hole Core", "Tears bend space itself", "Tears become black holes: homing, spectral, piercing, pull enemies and collapse into a singularity.", 0, "tearflag range shotspeed", ["devil", "secret"]),
    ("midas_engine", "Midas Engine", "Everything you touch turns to gold", "Hits can turn enemies to gold. Kills drop coins. +1 luck.", 0, "luck", ["treasure", "shop"]),
    ("glitched_crown", "Glitched Crown", "Reality forgets to hurt you", "Flight, +3 luck. 1/3 chance to ignore a hit and fire a tear nova.", 0, "flying luck", ["angel", "secret"]),
    ("shatter_drive", "Shatter Drive", "Break the room", "Huge damage to every enemy plus Crack the Sky on each.", 3, "", ["treasure"]),
    ("debug_die", "Debug Die", "Rolls only the best", "Spawns a random quality 4 item.", 4, "", ["shop"]),
    ("supernova_heart", "Supernova Heart", "Your pain becomes a star", "+1 heart. Getting hit detonates a supernova. Heal half a heart on room clear.", 0, "", ["treasure", "boss"]),
    ("quantum_tears", "Quantum Tears", "Every shot, three timelines", "Fire 2 extra tears in a spread.", 0, "", ["treasure"]),
    ("phoenix_feather", "Phoenix Feather", "Rise again, once per floor", "Once per floor, a lethal hit fully heals you and erupts in fire. +0.2 speed.", 0, "speed", ["angel"]),
    ("storm_core", "Storm Core", "Lightning answers", "Tears chain lightning between enemies. +1.5 damage.", 0, "damage tearflag tearcolor", ["treasure"]),
    ("vampire_fang", "Vampire Fang", "Feed on the fallen", "1/6 chance to heal half a heart on kill. +1 damage.", 0, "damage", ["devil"]),
    ("frost_nova", "Frost Nova", "Absolute zero", "Tears freeze and slow. Tears up.", 0, "tearflag tearcolor firedelay", ["treasure"]),
    ("inferno_halo", "Inferno Halo", "A crown of fire", "Burning tears and an aura that scorches nearby enemies.", 0, "tearflag tearcolor", ["devil", "treasure"]),
    ("titan_blood", "Titan Blood", "Grow beyond mortal limits", "+2 full hearts, damage x1.3 +1, bigger body, slight speed down.", 0, "damage size speed", ["boss"]),
    ("mirror_shard", "Mirror Shard", "Shoot from both sides", "Every tear also fires backwards.", 0, "", ["treasure"]),
    ("fourfold_clover", "Fourfold Clover", "Fortune favours you", "+7 luck. 15% of tears are golden crits for triple damage.", 0, "luck", ["angel", "treasure"]),
    ("bullet_hell", "Bullet Hell", "Fill the screen", "Tears x3, damage x0.6, shot speed up.", 0, "firedelay damage shotspeed", ["treasure"]),
    ("colossus_tears", "Colossus Tears", "Huge tears, huge hits", "+3 damage, giant tears with knockback.", 0, "damage tearflag", ["treasure", "boss"]),
    ("toxic_core", "Toxic Core", "Leave nothing but poison", "Poison tears and a trail of toxic creep.", 0, "tearflag tearcolor", ["devil", "treasure"]),
    ("satellite_beam", "Satellite Beam", "Orbital support online", "Fires a laser at the nearest enemy every 2.5 seconds.", 0, "", ["treasure", "shop"]),
    ("chronos_gear", "Chronos Gear", "Time bends around you", "All enemies are permanently slowed. +0.15 speed.", 0, "speed", ["angel", "shop"]),
    ("blast_heart", "Blast Heart", "Explosions love you", "Immune to explosions. +15 bombs.", 0, "", ["treasure", "shop"]),
    ("phantom_step", "Phantom Step", "Untouchable", "Flight, spectral tears, +0.4 speed, long invincibility after hits.", 0, "speed flying tearflag", ["angel", "secret"]),
    ("chaos_prism", "Chaos Prism", "Every tear is a surprise", "Every tear gets a random effect.", 0, "", ["secret", "treasure"]),
    ("overcharger", "Overcharger", "Infinite power", "+1 extra active charge on room clear. Tears up.", 0, "firedelay", ["shop"]),
    ("ascension_sigil", "Ascension Sigil", "All stats up!", "+1 damage, tears, speed, range, shot speed, +2 luck and a soul heart.", 0, "damage firedelay speed range shotspeed luck", ["angel", "boss"]),
    ("nuke_button", "Nuke Button", "Do not press", "Destroys every normal enemy. Bosses lose 40% of max HP.", 6, "", ["devil", "secret"]),
    ("wormhole_key", "Wormhole Key", "Skip to the good part", "Teleports you to the treasure room (or a random room).", 2, "", ["shop", "secret"]),
    ("balance_glove", "Balance Glove", "Perfectly balanced", "Half of all normal enemies vanish. Bosses lose half their HP.", 6, "", ["devil"]),
    ("seraph_bell", "Seraph Bell", "Heaven answers", "A ring of holy light around you and a soul heart.", 3, "", ["angel"]),
    ("treasure_geyser", "Treasure Geyser", "Make it rain", "Erupts with 12 coins, a bomb and a key.", 2, "", ["shop", "treasure"]),
    ("event_horizon", "Event Horizon", "Nothing escapes", "Opens a huge black hole for 6 seconds: swallows enemy shots, drags in and shreds enemies.", 4, "", ["devil", "secret", "treasure"]),
    # Fallen Sky items (scripts/altar_fallen_sky.lua)
    ("fallen_star", "Fallen Star", "The sky remembers you", "Every 4th tear calls a falling star down on the nearest enemy: a heavy impact that hits everything around it.", 0, "", ["treasure", "angel"]),
    ("still_sky", "Still Sky", "The stars hold their breath", "Time stops for 4 seconds: enemies freeze and every enemy shot turns to stardust.", 4, "", ["shop", "treasure"]),
    ("oblivion_eye", "Eye of Oblivion", "Something watches with you", "A void eye orbits you, blocks shots, burns what it touches and fires void lasers.", 0, "", ["devil", "secret"]),
    ("seraph_wings", "Seraph Wings", "Fly on fallen light", "Flight, +0.2 speed. Every 3rd shot adds two holy feathers; getting hit releases a ring of them.", 0, "flying speed", ["angel"]),
    ("nebula_heart", "Nebula Heart", "A heart full of stars", "+1 heart. Kills leave damaging nebula clouds; every 12 kills heals half a heart.", 0, "", ["treasure", "boss"]),
    ("comet_tail", "Comet Tail", "Never stop moving", "+0.3 speed and a trail of stardust. Keep running for a second to become a comet that rams enemies.", 0, "speed", ["treasure"]),
    ("rift_shard", "Rift Shard", "Tear the world open", "Tears can rip open a void rift: a beam that cuts across the room both ways. Higher chance with luck.", 0, "", ["devil", "secret"]),
    ("dying_star", "Dying Star", "Burn bright, then brighter", "Become a star for 5 seconds: invincible, burning everything near you, then go supernova.", 6, "", ["angel", "devil"]),
]


def lua_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    xml = ['<items gfxroot="gfx/items/" version="1">']
    pools = {}
    for key, name, pickup, _desc, charges, cache, pool_names in ITEMS:
        tag = "active" if charges else "passive"
        attrs = f'name="{name}" description="{pickup}" gfx="{key}.png" quality="4"'
        if charges:
            attrs += f' maxcharges="{charges}"'
        if cache:
            attrs += f' cache="{cache}"'
        xml.append(f'\t<{tag} {attrs} tags="offensive"/>')
        for p in pool_names:
            pools.setdefault(p, []).append(name)
    xml.append("</items>")
    with open(os.path.join(MOD, "content", "items.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(xml) + "\n")

    px = ["<ItemPools>"]
    for pool, names in pools.items():
        px.append(f'\t<Pool Name="{pool}">')
        px += [f'\t\t<Item Name="{n}" Weight="0.6" DecreaseBy="1" RemoveOn="0.1"/>' for n in names]
        px.append("\t</Pool>")
    px.append("</ItemPools>")
    with open(os.path.join(MOD, "content", "itempools.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(px) + "\n")

    lua = ["-- Generated by AltarModManager/tools/gen_items.py. Edit that file instead.", "return {"]
    for key, name, _pickup, desc, charges, _cache, _pools in ITEMS:
        lua.append(f"\t{{ key = {lua_str(key)}, name = {lua_str(name)}, desc = {lua_str(desc)}, charges = {charges} }},")
    lua.append("}")
    os.makedirs(os.path.join(MOD, "scripts"), exist_ok=True)
    with open(os.path.join(MOD, "scripts", "altar_data.lua"), "w", encoding="utf-8") as f:
        f.write("\n".join(lua) + "\n")
    print(f"{len(ITEMS)} items written")


if __name__ == "__main__":
    main()
