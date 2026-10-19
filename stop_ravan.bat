@echo off
rem Safely stop running Ravaan instance without killing unrelated python processes
echo Stopping Ravaan...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*ravan*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('Stopped Ravaan (PID: ' + $_.ProcessId + ')') }"
if %ERRORLEVEL% EQU 0 (
    echo Ravaan stopped.
) else (
    echo Ravaan was not running.
)
timeout /t 2 >nul
