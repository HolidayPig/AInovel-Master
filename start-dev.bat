@echo off
REM AInovel 一键启动：后端 + 前端（双击或在此目录执行）
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0start-dev.ps1"
pause
