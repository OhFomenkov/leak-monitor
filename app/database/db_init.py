import os
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

def init_database():
    db_name = os.getenv("DB_NAME", "monitor_db")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")

    # 1. Создание БД
    conn = psycopg2.connect(dbname="postgres", user=db_user, password=db_password, host=db_host, port=db_port)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (db_name,))
        if not cur.fetchone():
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
            print(f"База данных '{db_name}' создана.")
    conn.close()

    # 2. Создание таблиц
    conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host=db_host, port=db_port)
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scraped_logins (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255),
                password TEXT,
                source_detail TEXT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS scraper_sources (
                id SERIAL PRIMARY KEY,
                source_name VARCHAR(255),
                source_url TEXT
            );

            CREATE TABLE IF NOT EXISTS staff_users (
                id SERIAL PRIMARY KEY,
                fio VARCHAR(255),
                email VARCHAR(255),
                department VARCHAR(100)
            );

            CREATE TABLE IF NOT EXISTS telegram_sources (
                id SERIAL PRIMARY KEY,
                channel_name VARCHAR(255),
                chat_id VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS security_incidents (
                id SERIAL PRIMARY KEY,
                staff_id INTEGER REFERENCES staff_users(id),
                scraped_id INTEGER REFERENCES scraped_logins(id),
                incident_status VARCHAR(50),
                confirmed_at TIMESTAMP
            );
        """)
        conn.commit()
    conn.close()
    print("Инициализация таблиц успешно завершена.")

if __name__ == "__main__":
    init_database()
