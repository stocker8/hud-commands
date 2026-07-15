@echo off
setlocal
REM Install the hud session skills. The real installer is tools\install.py.
where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3 not found on PATH. Install it and re-run.
  pause
  exit /b 1
)
python "%~dp0tools\install.py"
if errorlevel 1 (
  echo.
  echo Install failed - see the message above.
  pause
  exit /b 1
)
if not exist "%USERPROFILE%\.claude\commands" mkdir "%USERPROFILE%\.claude\commands"
copy /Y "%~dp0commands\hud-update.md" "%USERPROFILE%\.claude\commands" >nul
echo   Installed: %USERPROFILE%\.claude\commands\hud-update.md
echo.
echo Restart Claude Code and type / to see /hud-catchup and /hud-handoff.
echo.
pause
