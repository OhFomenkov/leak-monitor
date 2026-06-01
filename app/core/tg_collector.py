import os
import sys
import re
import asyncio
import subprocess
import signal

# --- ФИКС ПУТЕЙ ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from app.database.db_manager import DBManager

# Инициализация БД
db = DBManager()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8675324591:AAHfXa6_dYZtOm8ODTdj1vZ8nqTw4aJPFis")

if not BOT_TOKEN:
    print("[!] Ошибка: Не задан BOT_TOKEN!", file=sys.stderr)
    sys.exit(1)

LEAK_PATTERN = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}):([^\s]+)'

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Глобальный счетчик для статистики сессии
session_stats = {"total_found": 0}


def get_monitored_chat_ids():
    try:
        with db.conn.cursor() as cur:
            cur.execute("SELECT chat_id FROM telegram_sources;")
            return [int(row[0]) for row in cur.fetchall()]
    except Exception as e:
        print(f"[!] Ошибка БД: {e}", file=sys.stderr)
        return []


@dp.channel_post()
async def handle_channel_post(message: Message):
    current_chat_id = message.chat.id
    monitored_ids = get_monitored_chat_ids()

    if current_chat_id in monitored_ids:
        text = message.text or message.caption
        if not text:
            return

        found_data = re.findall(LEAK_PATTERN, text)
        if found_data:
            total_inserted = 0
            for email, password in found_data:
                is_new = db.add_scraped_data(email, password, f"TG Live: {message.chat.title or current_chat_id}")
                if is_new:
                    total_inserted += 1

            if total_inserted > 0:
                print(f"[LIVE] Канал '{message.chat.title}': Добавлено {total_inserted} утечек")


# Обработчик завершения процесса
def on_stop(signum, frame):
    sys.exit(0)


# Регистрируем обработчик для корректного выхода
signal.signal(signal.SIGTERM, on_stop)


def start_bot_process():
    """Запускает этот же файл как отдельный процесс"""
    cmd = [sys.executable, __file__]
    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return process.pid


async def main():
    print("[*] Telegram коллектор запущен...")
    await dp.start_polling(bot, allowed_updates=["channel_post"])


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        with open("last_session_stats.txt", "w") as f:
            f.write(str(session_stats["total_found"]))
            f.flush()
            os.fsync(f.fileno())
        print("\n[-] Мониторинг остановлен.")