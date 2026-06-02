@echo off
setlocal enabledelayedexpansion
title VTT - Voice to Text

set "VTT_DIR=%~dp0"
cd /d "%VTT_DIR%"

echo.
echo  ============================================
echo    VTT - Voice to Text
echo  ============================================
echo.

:: ================================================================
:: STEP 1 — Find Python (resolved to full path)
:: ================================================================
echo  [1/3] Python...

set "PYTHON="

:: 1a) python on PATH - resolve via where
where python >nul 2>&1
if !errorlevel! equ 0 for /f "delims=" %%i in ('where python 2^>nul') do (
    if "!PYTHON!"=="" set "PYTHON=%%i"
)

:: 1b) Common install locations
if "!PYTHON!"=="" for %%d in (
    "%LOCALAPPDATA%\Programs\Python\Python313"
    "%LOCALAPPDATA%\Programs\Python\Python312"
    "%LOCALAPPDATA%\Programs\Python\Python311"
    "%PROGRAMFILES%\Python312"
    "%PROGRAMFILES%\Python311"
) do if exist "%%~d\python.exe" if "!PYTHON!"=="" set "PYTHON=%%~d\python.exe"

if "!PYTHON!"=="" (
    echo  [ERROR] Python 3 not found
    echo  Install from: https://www.python.org/downloads/
    pause & exit /b 1
)

:: Derive full path for pythonw.exe
for %%f in ("!PYTHON!") do set "PYDIR=%%~dpf"
set "PYTHONW=!PYDIR!pythonw.exe"
if not exist "!PYTHONW!" set "PYTHONW=!PYTHON!"

echo  [OK] !PYTHON!

:: ================================================================
:: STEP 2 — Packages (cached: .vtt_deps_ok file)
:: ================================================================
set "DEPS_OK=%VTT_DIR%.vtt_deps_ok"

if exist "%DEPS_OK%" (
    echo  [2/3] Packages [CACHED]
    goto :launch
)

echo  [2/3] Packages (first-run, installing if needed)...

:: Single pip call — already-installed packages are skipped instantly
"!PYTHON!" -m pip install --quiet --disable-pip-version-check customtkinter SpeechRecognition PyAutoGUI sounddevice numpy scipy keyboard faster-whisper

:: Quick verify: try importing all 8 (one Python call)
"!PYTHON!" -c "import customtkinter,speech_recognition,pyautogui,sounddevice,numpy,scipy,keyboard; import faster_whisper; print('ok')" >nul 2>&1
if !errorlevel! neq 0 (
    echo  [WARN] Some imports failed - VTT will auto-retry on launch
) else (
    echo  [OK] All packages ready
)

:: Write cache marker so next launch skips this entire step
echo verified > "%DEPS_OK%"

:: ================================================================
:: STEP 3 — Launch VTT
:: ================================================================
:launch
echo.
echo  [3/3] Launching VTT...

if not exist "%VTT_DIR%VTT.pyw" (
    echo  [ERROR] VTT.pyw not found
    pause & exit /b 1
)

start "" "!PYTHONW!" "%VTT_DIR%VTT.pyw"

echo  [OK] VTT is running  (logs: logs.txt)
timeout /t 2 >nul
exit /b 0
