@echo off
rem Preview of the Mulle Meck launcher, run inside WSL (window on Windows via
rem WSLg). Mouse and keyboard only: controllers do not reach WSL. Uses the
rem Windows package folder dist\windows\MulleMeck and the Linux ScummVM build.
wsl.exe -d Ubuntu --cd "%~dp0" -- bash -c "~/.venvs/mulle/bin/python -m launcher --root dist/windows/MulleMeck --window"
if errorlevel 1 pause
