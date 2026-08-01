@echo off
REM DokuZen - Windows Startskript
REM ======================================

title DokuZen

cd /d "%~dp0"

set "VENV_PY=C:\_Local_DEV\venvs\dokuzen\Scripts\python.exe"

if exist "%VENV_PY%" (
    echo Starte mit virtueller Umgebung...
    "%VENV_PY%" main.py
) else if exist "venv\Scripts\python.exe" (
    echo Starte mit lokaler venv...
    venv\Scripts\python.exe main.py
) else (
    echo Starte mit System-Python...
    python main.py
)

if errorlevel 1 (
    echo.
    echo FEHLER: Anwendung konnte nicht gestartet werden.
    echo Tipp: ueber den Doku-Launcher installieren ^(legt venv an + Abhaengigkeiten^).
    echo   oder manuell: pip install -r requirements.txt
    echo.
    pause
)
