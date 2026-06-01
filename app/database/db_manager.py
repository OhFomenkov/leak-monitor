import logging
import hashlib
from app.database.connection import get_db_connection

# Настройка логгера для этого модуля
logger = logging.getLogger(__name__)

class DBManager:
    def __init__(self):
        """Инициализация подключения к PostgreSQL через общий конфиг"""
        try:
            self.conn = get_db_connection()
            self.conn.autocommit = True
            logger.info("Соединение с PostgreSQL установлено.")
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            self.conn = None

    def _hash_password(self, password):
        """Хеширование пароля (SHA-256)"""
        return hashlib.sha256(password.encode()).hexdigest()

    def add_scraped_data(self, email, password, source):
        """Сохранение находки в базу с проверкой на дубликаты"""
        if not self.conn:
            return False

        hashed_pw = self._hash_password(password)

        try:
            with self.conn.cursor() as cursor:
                # Проверка на дубликат
                cursor.execute('''
                    SELECT id FROM scraped_logins 
                    WHERE email = %s AND password = %s
                ''', (email, hashed_pw))

                if cursor.fetchone():
                    return None

                # Сохранение
                cursor.execute('''
                    INSERT INTO scraped_logins (email, password, source_detail) 
                    VALUES (%s, %s, %s)
                ''', (email, hashed_pw, source))

                return True
        except Exception as e:
            logger.error(f"Ошибка при записи в БД: {e}")
            return False

    def run_incident_check(self):
        """Проводит анализ (матчинг) между сотрудниками и утечками"""
        if not self.conn:
            return 0
        try:
            with self.conn.cursor() as cursor:
                query = """
                    INSERT INTO security_incidents (staff_id, scraped_id, incident_status)
                    SELECT s.id, sl.id, 'Confirmed'
                    FROM public.staff_users s
                    JOIN public.scraped_logins sl ON LOWER(TRIM(s.email)) = LOWER(TRIM(sl.email))
                    WHERE NOT EXISTS (
                        SELECT 1 FROM public.security_incidents si 
                        WHERE si.scraped_id = sl.id
                    );
                """
                cursor.execute(query)
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Ошибка при проведении анализа: {e}")
            return 0

    def get_latest_incidents(self, limit=10):
        """Возвращает детали последних обнаруженных инцидентов"""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cursor:
                query = """
                    SELECT s.fio, s.email, sl.source_detail, sl.found_at
                    FROM security_incidents si
                    JOIN staff_users s ON si.staff_id = s.id
                    JOIN scraped_logins sl ON si.scraped_id = sl.id
                    ORDER BY sl.found_at DESC
                    LIMIT %s;
                """
                cursor.execute(query, (limit,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка получения деталей инцидентов: {e}")
            return []

    def check_single_incident(self, email):
        """Точечная проверка одного email"""
        if not self.conn:
            return 0
        try:
            with self.conn.cursor() as cursor:
                query = """
                    INSERT INTO security_incidents (staff_id, scraped_id, incident_status)
                    SELECT s.id, sl.id, 'Confirmed'
                    FROM staff_users s
                    JOIN scraped_logins sl ON LOWER(TRIM(s.email)) = LOWER(TRIM(sl.email))
                    WHERE LOWER(TRIM(s.email)) = LOWER(TRIM(%s))
                    AND NOT EXISTS (
                        SELECT 1 FROM security_incidents si WHERE si.scraped_id = sl.id
                    )
                    RETURNING id;
                """
                cursor.execute(query, (email,))
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Ошибка точечной проверки: {e}")
            return 0




    def close(self):
        """Закрытие соединения"""
        if self.conn:
            self.conn.close()
            logger.info("Соединение с БД закрыто.")

    # ====================================================
    # ИСПРАВЛЕННЫЕ МЕТОДЫ УПРАВЛЕНИЯ ПЕРСОНАЛОМ
    # ====================================================



    def get_all_staff(self):
        """Получает список всех сотрудников из таблицы staff_users"""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cursor:
                query = "SELECT id, fio, email, department FROM staff_users ORDER BY id ASC;"
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка получения списка персонала: {e}")
            return []

    def add_staff(self, fio, email, role):
        """Добавляет нового сотрудника в таблицу staff_users"""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                query = "INSERT INTO staff_users (fio, email, department) VALUES (%s, %s, %s);"
                cursor.execute(query, (fio, email, role))
                return True
        except Exception as e:
            logger.error(f"Ошибка добавления сотрудника: {e}")
            return False

    def update_staff(self, worker_id, fio, email, role):
        """Обновляет данные сотрудника в таблице staff_users по ID"""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                query = "UPDATE staff_users SET fio = %s, email = %s, department = %s WHERE id = %s;"
                cursor.execute(query, (fio, email, role, worker_id))
                return True
        except Exception as e:
            logger.error(f"Ошибка обновления данных сотрудника: {e}")
            return False

    def delete_staff(self, worker_id):
        """Удаляет сотрудника из таблицы staff_users по ID"""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                query = "DELETE FROM staff_users WHERE id = %s;"
                cursor.execute(query, (worker_id,))
                return True
        except Exception as e:
            logger.error(f"Ошибка удаления сотрудника: {e}")
            return False

    def get_all_incidents(self):
        """Возвращает абсолютно все инциденты для детального журнала"""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cursor:
                query = """
                    SELECT s.fio, s.email, sl.source_detail, sl.found_at
                    FROM security_incidents si
                    JOIN staff_users s ON si.staff_id = s.id
                    JOIN scraped_logins sl ON si.scraped_id = sl.id
                    ORDER BY sl.found_at DESC;
                """
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка получения всех инцидентов: {e}")
            return []

    def get_local_sources_by_email(self, email):
        """Ищет источники утечек для конкретного email в локальной таблице scraped_logins"""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cursor:
                query = """
                    SELECT DISTINCT source_detail 
                    FROM scraped_logins 
                    WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s));
                """
                cursor.execute(query, (email,))
                return [row[0] for row in cursor.fetchall() if row[0]]
        except Exception as e:
            logger.error(f"Ошибка поиска локальных источников утечек: {e}")
            return []

    def add_external_leak_if_not_exists(self, email, source):
        """Добавляет утечку из внешнего API в локальную базу scraped_logins"""
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cursor:
                # Проверка дубликатов остается прежней
                cursor.execute("""
                    SELECT id FROM scraped_logins 
                    WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s)) 
                    AND LOWER(TRIM(source_detail)) = LOWER(TRIM(%s));
                """, (email, source))
                row = cursor.fetchone()
                if row:
                    return row[0]

                # ИСПРАВЛЕННЫЙ ЗАПРОС: Явно передаем пустую строку '' вместо NULL в колонку password
                cursor.execute("""
                    INSERT INTO scraped_logins (email, password, source_detail, found_at)
                    VALUES (%s, %s, %s, NOW())
                    RETURNING id;
                """, (email, '', source))  # Передаем пустую строку для обхода NOT NULL

                new_id = cursor.fetchone()[0]
                self.conn.commit()
                return new_id
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            logger.error(f"🔴 Ошибка сохранения внешней утечки: {e}")
            return None

    def get_staff_id_by_email(self, email):
        """Пункт 2: Быстро проверяет, принадлежит ли email сотруднику"""
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM staff_users 
                    WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s));
                """, (email,))
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Ошибка поиска сотрудника по email: {e}")
            return None

    def create_incident_direct(self, staff_id, scraped_id):
        """Записывает строго ОДИН инцидент на сотрудника для предотвращения флуда в БД"""
        if not self.conn:
            return
        try:
            with self.conn.cursor() as cursor:
                # ИЗМЕНЕНО: Ищем любую запись по staff_id (убираем привязку к конкретному scraped_id)
                cursor.execute("""
                    SELECT id FROM security_incidents 
                    WHERE staff_id = %s;
                """, (staff_id,))

                if cursor.fetchone():
                    # Если у сотрудника уже заведен тикет — выходим, дубли не нужны
                    return

                    # Если инцидентов вообще нет — создаем первый и единственный
                cursor.execute("""
                    INSERT INTO security_incidents (staff_id, scraped_id, created_at, status)
                    VALUES (%s, %s, NOW(), 'New');
                """, (staff_id, scraped_id))
                self.conn.commit()
                print(f"[БАЗА] Создан единственный инцидент для staff_id={staff_id}")
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            logger.error(f"🔴 Ошибка записи единичного инцидента: {e}")

    def get_total_leaks_count(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM scraped_logins;")
            return cur.fetchone()[0]