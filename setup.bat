@echo off
chcp 65001 >nul

echo [*] Проверка виртуального окружения...
if not exist venv (
    echo [*] Окружение не найдено. Создаю...
    python -m venv venv
)

echo [*] Активация окружения...
call venv\Scripts\activate.bat

echo [*] Установка библиотек...
pip install --upgrade pip
pip install -r requirements.txt

echo [*] Инициализация структуры базы данных...
python -m app.database.db_init

echo [*] Наполнение демо-данными...
python scripts/db_seed.py

echo.
echo [!] Установка завершена успешно!
echo [!] Теперь вы можете запустить проект через start.bat
pause
