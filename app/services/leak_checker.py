import requests
import logging
from typing import List

# Настройка логгера для сервиса
logger = logging.getLogger(__name__)


def check_email_in_leakcheck(email: str) -> List[str]:
    """
    Проверяет email через API leakcheck.io.
    Возвращает список названий баз (источников).
    Если ничего не найдено или произошла ошибка — возвращает пустой список.
    """
    url = f"https://leakcheck.io/api/public?check={email}"
    try:
        response = requests.get(url, timeout=10)

        # Проверяем успешность ответа
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('sources'):
                # Извлекаем названия источников
                return [s.get('name', 'Unknown') for s in data.get('sources')]

        return []

    except Exception as e:
        logger.error(f"Ошибка при запросе к LeakCheck для {email}: {e}")
        return []