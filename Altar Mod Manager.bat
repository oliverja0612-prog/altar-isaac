@echo off
rem Opens Altar Mod Manager (the built exe if present, else the Python source).
cd /d "%~dp0AltarModManager"
if exist Altar.exe (
    start "" Altar.exe --game "%~dp0."
) else (
    start "" pythonw src\altar_manager.py --game "%~dp0."
)
