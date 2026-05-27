@echo off
chcp 65001 >nul
title Build Tasker

echo [1/3] Building with PyInstaller...
python -m PyInstaller tasker.spec --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller failed.
    echo Install it: pip install pyinstaller
    pause
    exit /b 1
)
echo.

echo [2/3] Adding UTF-8 BOM to installer script...
powershell -NoProfile -Command ^
  "$enc = New-Object System.Text.UTF8Encoding $true; " ^
  "$raw = [IO.File]::ReadAllText('%~dp0installer.iss', [Text.Encoding]::UTF8); " ^
  "[IO.File]::WriteAllText('%~dp0_installer_bom.iss', $raw, $enc)"
echo.

echo [3/3] Compiling installer with Inno Setup...
set "ISCC="
where iscc >nul 2>&1 && set "ISCC=iscc"
if not defined ISCC (
    if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
)
if not defined ISCC (
    if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
)
if not defined ISCC (
    echo Inno Setup not found. Install: winget install JRSoftware.InnoSetup
    pause
    exit /b 1
)
"%ISCC%" _installer_bom.iss
del _installer_bom.iss 2>nul
echo.

echo Done! Installer: installer_output\Tasker_Setup.exe
pause
