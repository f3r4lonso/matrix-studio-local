@echo off
chcp 65001 >nul
title Matrix Studio
powershell.exe -NoProfile -File "%~dp0scripts\start-local.ps1"
pause
