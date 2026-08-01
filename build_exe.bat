@echo off
setlocal

cd /d "%~dp0"

set "APP_NAME=DokuZen-Pro"
set "VERSION=1.0.0"
set "BUILD_ROOT=C:\_Local_DEV\codex_build\DokuZen-Pro"
set "DIST_DIR=%CD%\releases\v%VERSION%"
set "EXE_NAME=%APP_NAME%-%VERSION%-win64"
set "ICON=%CD%\DokuZen.ico"

if not exist "%BUILD_ROOT%" mkdir "%BUILD_ROOT%"
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"

python tools\preflight.py --strict-build
if errorlevel 1 (
  echo Preflight failed.
  exit /b 1
)

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name "%EXE_NAME%" ^
  --icon "%ICON%" ^
  --workpath "%BUILD_ROOT%\build" ^
  --specpath "%BUILD_ROOT%" ^
  --distpath "%DIST_DIR%" ^
  --add-data "%CD%\assets;assets" ^
  --add-data "%CD%\config;config" ^
  --exclude-module torch ^
  --exclude-module pandas ^
  --exclude-module scipy ^
  --exclude-module matplotlib ^
  --exclude-module IPython ^
  --exclude-module pytest ^
  --exclude-module black ^
  --exclude-module pygame ^
  --exclude-module PyQt5 ^
  --exclude-module PyQt6 ^
  main.py

if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

echo Built "%DIST_DIR%\%EXE_NAME%.exe"
