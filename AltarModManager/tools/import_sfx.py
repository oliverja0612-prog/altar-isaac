"""Turns the boss sound effects in AltarModManager/sfx_in/ into game sounds.

    python import_sfx.py

Each <key>.mp3 (made with ElevenLabs Sound Effects) is loudness levelled, saved as
resources/sfx/altar_fx/<key>.wav (plus a mirror copy under <mod>/sfx/altar_fx) and
registered in content/sounds.xml as "Altar FX <key>". The boss falls back to the
game's own sounds for any key that's missing.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MOD = os.path.join(os.path.dirname(ROOT), "mods", "altar_core")
SFX_IN = os.path.join(ROOT, "sfx_in")
OUT_DIR = os.path.join(MOD, "resources", "sfx", "altar_fx")
MIRROR = os.path.join(MOD, "sfx", "altar_fx")

sys.path.insert(0, os.path.join(ROOT, "src"))
from altar_sounds import write_sounds_xml  # noqa: E402
from import_voice import ffmpeg_exe  # noqa: E402


def main():
    ff = ffmpeg_exe()
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(MIRROR, exist_ok=True)
    count = 0
    for f in sorted(os.listdir(SFX_IN)) if os.path.isdir(SFX_IN) else []:
        key, ext = os.path.splitext(f)
        if ext.lower() not in (".mp3", ".wav", ".ogg"):
            continue
        out = os.path.join(OUT_DIR, key + ".wav")
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", os.path.join(SFX_IN, f),
                        "-af", "loudnorm=I=-14:TP=-1.0:LRA=11", "-ac", "1", "-ar", "44100",
                        "-c:a", "pcm_s16le", out], check=True)
        shutil.copy2(out, os.path.join(MIRROR, key + ".wav"))
        count += 1
    write_sounds_xml(MOD)
    print(f"{count} sound effects imported")


if __name__ == "__main__":
    main()
