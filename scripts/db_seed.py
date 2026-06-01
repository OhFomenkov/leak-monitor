import sys
import os
import hashlib

# Добавляем корневую папку в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db_connection


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def seed_database():
    conn = get_db_connection()
    cur = conn.cursor()

    print("[*] Запуск процесса наполнения базы данных демо-данными...")

    try:
        # 1. Заполняем сотрудников
        staff = [
            ('Фоменков Артем Алексеевич', 'fomenkov_aa_22@grsu.by', 'Факультет математики и информатики'),
            ('Иванов Иван Иванович', 'ivanov_ii@grsu.by', 'Кафедра системного программирования'),
            ('Петрова Мария Сергеевна', 'petrova_ms@grsu.by', 'Администрация')
        ]
        cur.executemany("""
            INSERT INTO staff_users (fio, email, department) 
            VALUES (%s, %s, %s) ON CONFLICT (email) DO NOTHING;
        """, staff)

        # 2. Заполняем источники
        cur.executemany("""
            INSERT INTO telegram_sources (channel_name, chat_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;
        """, [('Test Leak Channel', '-1003938123593'), ('ShadowForge', '@shadow_forge_dump')])

        cur.executemany("""
            INSERT INTO scraper_sources (source_name, source_url) VALUES (%s, %s) ON CONFLICT DO NOTHING;
        """, [('LBSG.net', 'http://127.0.0.1:5000/'), ('Public Leak List', 'https://example.com/api')])

        # 3. Добавляем "слитые" данные (один из них совпадает с сотрудником fomenkov_aa_22@grsu.by)
        leaks = [
            ('fomenkov_aa_22@grsu.by', hash_password('super_secret_123'), 'TG Channel: Test Leak Channel'),
            ('random_user@gmail.com', hash_password('qwerty'), 'Web: LBSG.net'),
            ('ivanov_ii@grsu.by', hash_password('password123'), 'Web: Public Leak List')
        ]
        cur.executemany("""
            INSERT INTO scraped_logins (email, password, source_detail) 
            VALUES (%s, %s, %s);
        """, leaks)

        conn.commit()
        print("[+] Демо-данные успешно добавлены!")
        print("[!] Теперь запустите систему и нажмите 'Запустить Matching' — система покажет инциденты.")

    except Exception as e:
        print(f"[X] Ошибка при наполнении базы: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    seed_database()