@echo off
rem Launch Ravan without a console window (uses pythonw when available).
setlocal
set "HERE=%~dp0"
if exist "%HERE%.venv\Scripts\pythonw.exe" (
    start "" "%HERE%.venv\Scripts\pythonw.exe" -m ravan
) else (
    start "" pythonw -m ravan
)
endlocal
