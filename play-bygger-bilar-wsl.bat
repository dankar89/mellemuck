@echo off
rem Test launcher: starts the LINUX build of ScummVM inside WSL (window and
rem sound on Windows via WSLg). The standalone Windows version is in
rem dist\windows\MulleMeck. Add ScummVM options if you like, e.g.
rem   play-bygger-bilar-wsl.bat --fullscreen
wsl.exe -d Ubuntu --cd "%~dp0" -- ./tools/play-bilar.sh %*
if errorlevel 1 pause
