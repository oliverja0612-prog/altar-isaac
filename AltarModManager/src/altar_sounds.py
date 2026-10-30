"""Builds Altar Core's content/sounds.xml from the sound files that are actually
present, so voice lines (private) and SFX (public) can come and go independently.

  voice lines  resources/sfx/altar/oblivion_line<N>.wav  -> "Altar Oblivion Line <N>"
  boss SFX     resources/sfx/altar_fx/<key>.wav          -> "Altar FX <key>"

Each file also has a copy under <mod>/sfx/... because Isaac has been seen
resolving mod sound paths from the mod folder rather than from resources/.
Shared by tools/import_voice.py, tools/import_sfx.py, tools/build.py and the installer.
"""
import os
import re

VOICE_DIR = os.path.join("resources", "sfx", "altar")
FX_DIR = os.path.join("resources", "sfx", "altar_fx")


def sounds_xml(mod_dir, include_voice=True):
    lines = ['<sounds root="sfx/">']
    voice_dir = os.path.join(mod_dir, VOICE_DIR)
    if include_voice and os.path.isdir(voice_dir):
        nums = sorted(int(m.group(1)) for f in os.listdir(voice_dir)
                      for m in [re.fullmatch(r"oblivion_line(\d+)\.wav", f)] if m)
        for n in nums:
            lines.append(f'\t<sound name="Altar Oblivion Line {n}"><sample path="altar/oblivion_line{n}.wav"/></sound>')
    fx_dir = os.path.join(mod_dir, FX_DIR)
    if os.path.isdir(fx_dir):
        for f in sorted(os.listdir(fx_dir)):
            if f.endswith(".wav"):
                key = f[:-4]
                lines.append(f'\t<sound name="Altar FX {key}"><sample path="altar_fx/{f}"/></sound>')
    lines.append("</sounds>")
    return "\n".join(lines) + "\n"


def write_sounds_xml(mod_dir, include_voice=True):
    os.makedirs(os.path.join(mod_dir, "content"), exist_ok=True)
    with open(os.path.join(mod_dir, "content", "sounds.xml"), "w", encoding="utf-8") as f:
        f.write(sounds_xml(mod_dir, include_voice))
