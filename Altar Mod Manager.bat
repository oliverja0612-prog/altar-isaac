@echo off
rem Opens Altar Mod Manager. Build it first with: python AltarModManager\tools\build.py
cd /d "%~dp0AltarModManager"
if exist Altar.exe (
    start "" Altar.exe --game "%~dp0."
) else (
    echo Altar.exe is not built yet. Run: python tools\build.py
    pause
)
