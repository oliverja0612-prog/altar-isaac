"""Builds everything for sharing:

    dist/AltarSetup.exe   the installer: the C# / WPF app (app/) with the mod embedded
    Altar.exe             the same exe, dropped next to this folder for local use (manager mode)

Run:  python tools/build.py [--skip-art] [--public]

A venv (art and audio tools) and the .NET 9 SDK are installed under
%LOCALAPPDATA%\\AltarBuild so your normal Python and PATH stay untouched.
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
TOOLS = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "AltarBuild")
VENV = os.path.join(TOOLS, "venv")
DOTNET = os.path.join(TOOLS, "dotnet", "dotnet.exe")
APP = os.path.join(ROOT, "app")
PY = os.path.join(VENV, "Scripts", "python.exe")

sys.path.insert(0, SRC)
from altar_sounds import sounds_xml  # noqa: E402

# generated per-install files that must not ship
SKIP_MOD_FILES = {"altar_modlist.lua", "disable.it"}

# --public leaves out the fan-made "Umbra" voice lines; the cutscene then shows
# subtitles only. Used for the GitHub release.
PUBLIC = "--public" in sys.argv
PRIVATE_PATHS = ("sfx/altar/", "resources/sfx/altar/", "content/sounds.xml")


def run(cmd, **kw):
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True, **kw)


def ensure_venv():
    if not os.path.isfile(PY):
        print("Creating build venv at", VENV)
        venv.create(VENV, with_pip=True)
    run([PY, "-m", "pip", "install", "-q", "--upgrade", "pillow", "imageio-ffmpeg"])


def ensure_dotnet():
    """Private .NET 9 SDK via Microsoft's dotnet-install script (no admin, no PATH change)."""
    if os.path.isfile(DOTNET):
        return
    script = os.path.join(TOOLS, "dotnet-install.ps1")
    run(["powershell", "-NoProfile", "-Command",
         f"Invoke-WebRequest https://dot.net/v1/dotnet-install.ps1 -OutFile '{script}'"])
    run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script,
         "-Channel", "9.0", "-InstallDir", os.path.dirname(DOTNET), "-NoPath"])


def publish(payload):
    """One self-contained exe (no .NET install needed on friends' PCs) with the mod
    embedded: named AltarSetup.exe it installs, installed as Altar.exe it is the manager."""
    out = os.path.join(BUILD, "app")
    run([DOTNET, "publish", os.path.join(APP, "Altar.csproj"), "-c", "Release", "-r", "win-x64",
         "--self-contained", "-p:PublishSingleFile=true", f"-p:AltarPayload={payload}", "-o", out, "-nologo"],
        env={**os.environ, "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"})
    return os.path.join(out, "Altar.exe")


def make_payload():
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
        if PUBLIC:  # SFX only, no voice lines
            z.writestr("mod/content/sounds.xml", sounds_xml(MOD, include_voice=False))
    print(f"payload: {count} mod files -> {path}" + ("  (public: no voice lines)" if PUBLIC else ""))
    return path


def main():
    if "--skip-art" not in sys.argv:
        run([sys.executable, os.path.join(HERE, "gen_items.py")])
        run([sys.executable, os.path.join(HERE, "make_sprites.py")])
        run([sys.executable, os.path.join(HERE, "make_oblivion.py")], cwd=HERE)
        run([sys.executable, os.path.join(HERE, "make_story.py")], cwd=HERE)
    ensure_venv()
    run([PY, os.path.join(HERE, "import_voice.py")])  # Fish Audio lines in voice_in/ -> game sounds
    run([PY, os.path.join(HERE, "import_music.py")], cwd=HERE)
    run([PY, os.path.join(HERE, "import_sfx.py")], cwd=HERE)  # sfx_in/ -> boss sound effects  # music_in/ -> custom soundtrack
    os.makedirs(BUILD, exist_ok=True)
    ensure_dotnet()
    exe = publish(make_payload())
    os.makedirs(DIST, exist_ok=True)
    shutil.copy2(exe, os.path.join(DIST, "AltarSetup.exe"))
    shutil.copy2(exe, os.path.join(ROOT, "Altar.exe"))
    print(f"AltarSetup.exe: {os.path.getsize(os.path.join(DIST, 'AltarSetup.exe')) / 1e6:.1f} MB")
    shutil.rmtree(BUILD, ignore_errors=True)  # dotnet output and payload
    print("\nDone. Share dist/AltarSetup.exe with friends.")


if __name__ == "__main__":
    main()
