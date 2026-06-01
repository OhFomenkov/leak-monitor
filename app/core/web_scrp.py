import re
import sys
import time
import logging
import requests
import subprocess
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from app.database.db_manager import DBManager

# Загружаем настройки из .env
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Регулярка для поиска связок email:password
LEAK_PATTERN = re.compile(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+):([^\s<]+)')


class WebScraper:
    def __init__(self):
        self.db = DBManager()  # Инициализируем твой менеджер БД
        self.processed_leaks = set()

    def fetch_sources(self):
        """Получаем актуальный список OSINT-источников напрямую из базы данных"""
        try:
            with self.db.conn.cursor() as cur:
                cur.execute("SELECT source_name, source_url FROM scraper_sources;")
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Ошибка при получении списка источников из БД: {e}")
            return []

    def run(self):
        sources = self.fetch_sources()
        if not sources:
            return logger.warning("Источники отсутствуют. Скрапинг пропущен.")

        for name, url in sources:
            try:
                soup = BeautifulSoup(requests.get(url, timeout=5).text, 'html.parser')
                for email, password in LEAK_PATTERN.findall(soup.get_text()):
                    leak = f"{email}:{password}"
                    if leak not in self.processed_leaks:
                        if self.db.add_scraped_data(email, password, f"Web: {name} ({url})"):
                            logger.info(f"[OK] [{name}] Новая запись: {leak}")
                        self.processed_leaks.add(leak)
            except Exception as e:
                logger.error(f"Ошибка при обработке '{name}': {e}")

    def start_bot_process(self):
        """Запускает бота как отдельный фоновый процесс"""
        # Используем sys.executable, чтобы гарантированно использовать тот же Python, что и у Flask
        cmd = [sys.executable, __file__]
        # Запускаем без ожидания (Popen не блокирует основной поток)
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return process.pid


if __name__ == "__main__":
    logger.info("--- МНОГОПОТОЧНЫЙ СКАРПЕР SENTINEL ЗАПУЩЕН ---")
    scraper = WebScraper()
    while True:
        scraper.run()
        # Интервал между полными кругами обхода всех источников (в секундах)
        time.sleep(15)