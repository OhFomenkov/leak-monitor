@echo off
chcp 65001 >nul
echo [*] Активация виртуального окружения...
call venv\Scripts\activate.bat

echo [*] Инициализация базы данных...
python -m app.database.db_init

echo [*] Наполнение базы демо-данными...
python scripts/db_seed.py

echo.
echo [!] Подготовка завершена! Теперь можно запускать систему.
pause