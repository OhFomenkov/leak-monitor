@echo off
chcp 65001 >nul
echo [*] Активация виртуального окружения...
call venv\Scripts\activate.bat

echo [*] Запуск сервера Sentinel Monitor...
python run.py

pause