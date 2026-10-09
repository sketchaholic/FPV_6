@echo off
rem Launches Lap Callout. Keep this file in the same folder as lap_callout.py.
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw "lap_callout.py" & exit /b)
where pythonw >nul 2>nul && (start "" pythonw "lap_callout.py" & exit /b)
echo Could not find Python. Install it from python.org and tick "Add python.exe to PATH".
pause
