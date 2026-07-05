@echo off
setlocal
set "DEST=%USERPROFILE%\.claude\commands"
if not exist "%DEST%" mkdir "%DEST%"
copy /Y "%~dp0commands\hud-catchup.md" "%DEST%" >nul
copy /Y "%~dp0commands\hud-handoff.md" "%DEST%" >nul
copy /Y "%~dp0commands\hud-update.md" "%DEST%" >nul
if exist "%DEST%\catchup.md" del "%DEST%\catchup.md"
if exist "%DEST%\handoff.md" del "%DEST%\handoff.md"
echo.
echo Installed /hud-catchup, /hud-handoff and /hud-update to:
echo   %DEST%
echo.
echo Restart Claude Code and type / to see them.
echo.
pause
