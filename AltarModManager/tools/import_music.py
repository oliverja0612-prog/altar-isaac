"""Turns the OBLIVION soundtrack in AltarModManager/music_in/ into game music.

    python import_music.py

Expects intro, battle, battle2 and ending (.mp3/.wav/.ogg). Each is loudness levelled
a little under the voice lines, saved to resources/music/altar/ and registered in
content/music.xml as "Altar Oblivion Intro" (plays once) and "Altar Oblivion Battle"
(loops). Missing tracks fall back to the game's own boss music.
"""
import os
import shutil
import subprocess

from import_voice import ffmpeg_exe

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MOD = os.path.join(os.path.dirname(ROOT), "mods", "altar_core")
MUSIC_IN = os.path.join(ROOT, "music_in")
OUT_DIR = os.path.join(MOD, "resources", "music", "altar")
# same belt-and-braces copy as the voice lines: <mod>/music as well as resources/music
MIRROR = os.path.join(MOD, "music", "altar")

TRACKS = [
    # file stem, track name, loops, extra filter
    ("intro", "Altar Oblivion Intro", False, ""),
    ("battle", "Altar Oblivion Battle", True, ""),
    ("battle2", "Altar Oblivion Battle 2", True, ""),   # from half HP
    ("ending", "Altar Oblivion Ending", False, ""),     # when she falls
]


def find(stem):
    for ext in ("mp3", "wav", "ogg", "flac", "m4a"):
        p = os.path.join(MUSIC_IN, f"{stem}.{ext}")
        if os.path.isfile(p):
            return p
    return None


def main():
    ff = ffmpeg_exe()
    os.makedirs(OUT_DIR, exist_ok=True)
    xml = ['<music root="music/">']
    for stem, name, loop, extra in TRACKS:
        src = find(stem)
        if not src:
            print(f"{stem}: missing (game music used instead)")
            continue
        out = os.path.join(OUT_DIR, f"oblivion_{stem}.ogg")
        flt = "loudnorm=I=-18:TP=-1.5:LRA=11" + ("," + extra if extra else "")
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", src, "-af", flt, "-ar", "44100",
                        "-c:a", "libvorbis", "-q:a", "5", out], check=True)
        os.makedirs(MIRROR, exist_ok=True)
        shutil.copy2(out, os.path.join(MIRROR, os.path.basename(out)))
        xml.append(f'\t<track name="{name}" path="altar/oblivion_{stem}.ogg" loop="{"true" if loop else "false"}"/>')
        print(f"{stem}: -> {out}")
    xml.append("</music>")
    with open(os.path.join(MOD, "content", "music.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(xml) + "\n")


if __name__ == "__main__":
    main()
