"""Builds everything for sharing:

    dist/AltarSetup.exe   one-file installer (contains the mod and Altar.exe)
    Altar.exe             the manager app, also dropped next to this folder for local use

Run:  python tools/build.py [--skip-art] [--public]

PyInstaller is installed into its own venv under %LOCALAPPDATA%\\AltarBuild so
your normal Python stays untouched.
"""
import os
import shutil
import subprocess
import sys
import venv
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # AltarModManager/
GAME = os.path.dirname(ROOT)
MOD = os.path.join(GAME, "mods", "altar_core")
SRC = os.path.join(ROOT, "src")
ASSETS = os.path.join(ROOT, "assets")
BUILD = os.path.join(ROOT, "build")
DIST = os.path.join(ROOT, "dist")
VENV = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "AltarBuild", "venv")
PY = os.path.join(VENV, "Scripts", "python.exe")

# generated per-install files that must not ship
SKIP_MOD_FILES = {"altar_modlist.lua", "disable.it"}

# --public leaves out the fan-made "Umbra" voice lines; the cutscene then shows
# subtitles only. Used for the GitHub release.
PUBLIC = "--public" in sys.argv
PRIVATE_PATHS = ("sfx/", "resources/sfx/altar/", "content/sounds.xml")


def run(cmd, **kw):
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True, **kw)


def ensure_venv():
    if not os.path.isfile(PY):
        print("Creating build venv at", VENV)
        venv.create(VENV, with_pip=True)
    run([PY, "-m", "pip", "install", "-q", "--upgrade", "pyinstaller", "pillow", "imageio-ffmpeg"])


def pyinstaller(script, name, extra_data=()):
    data = [f"{ASSETS}{os.pathsep}assets"] + list(extra_data)
    cmd = [PY, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
           "--name", name, "--icon", os.path.join(ASSETS, "altar.ico"),
           "--distpath", os.path.join(BUILD, "dist"), "--workpath", os.path.join(BUILD, "work"),
           "--specpath", BUILD, "--paths", SRC]
    for d in data:
        cmd += ["--add-data", d]
    run(cmd + [os.path.join(SRC, script)])
    return os.path.join(BUILD, "dist", name + ".exe")


def make_payload(app_exe):
    path = os.path.join(BUILD, "payload.zip")
    count = 0
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(MOD):
            for f in files:
                if f in SKIP_MOD_FILES or f.endswith(".ai"):
                    continue
                full = os.path.join(root, f)
                rel = os.path.relpath(full, MOD).replace("\\", "/")
                if PUBLIC and rel.startswith(PRIVATE_PATHS):
                    continue
                z.write(full, "mod/" + rel)
                count += 1
        z.write(app_exe, "app/Altar.exe")
    print(f"payload: {count} mod files + Altar.exe -> {path}" + ("  (public: no voice lines)" if PUBLIC else ""))
    return path


def main():
    if "--skip-art" not in sys.argv:
        run([sys.executable, os.path.join(HERE, "gen_items.py")])
        run([sys.executable, os.path.join(HERE, "make_sprites.py")])
        run([sys.executable, os.path.join(HERE, "make_oblivion.py")], cwd=HERE)
        run([sys.executable, os.path.join(HERE, "make_story.py")], cwd=HERE)
    ensure_venv()
    run([PY, os.path.join(HERE, "import_voice.py")])  # Fish Audio lines in voice_in/ -> game sounds
    run([PY, os.path.join(HERE, "import_music.py")], cwd=HERE)  # music_in/ -> custom soundtrack
    os.makedirs(BUILD, exist_ok=True)
    app = pyinstaller("altar_manager.py", "Altar")
    payload = make_payload(app)
    setup = pyinstaller("altar_installer.py", "AltarSetup", [f"{payload}{os.pathsep}."])
    os.makedirs(DIST, exist_ok=True)
    shutil.copy2(setup, os.path.join(DIST, "AltarSetup.exe"))
    shutil.copy2(app, os.path.join(ROOT, "Altar.exe"))
    print(f"AltarSetup.exe: {os.path.getsize(os.path.join(DIST, 'AltarSetup.exe')) / 1e6:.1f} MB")
    shutil.rmtree(BUILD, ignore_errors=True)  # PyInstaller work files, specs, payload
    print("\nDone. Share dist/AltarSetup.exe with friends.")


if __name__ == "__main__":
    main()
