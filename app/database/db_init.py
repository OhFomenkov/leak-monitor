from app.database.connection import get_db_connection

def create_final_db_structure():
    commands = [
        '''
        CREATE TABLE IF NOT EXISTS staff_users (
            id SERIAL PRIMARY KEY,
            fio VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            department VARCHAR(100)
        );
        ''',
        '''
        CREATE TABLE IF NOT EXISTS scraped_logins (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            password TEXT NOT NULL,
            source_detail TEXT,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ''',
        '''
        CREATE TABLE IF NOT EXISTS security_incidents (
            id SERIAL PRIMARY KEY,
            staff_id INTEGER REFERENCES staff_users(id),
            scraped_id INTEGER REFERENCES scraped_logins(id),
            incident_status VARCHAR(50) DEFAULT 'New',
            confirmed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        '''
    ]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        print("[*] Подключение установлено. Создание таблиц...")

        for command in commands:
            cursor.execute(command)

        conn.commit()
        cursor.close()
        conn.close()
        print("[+] Cтруктура БД создана успешно!")

    except Exception as e:
        print(f"[X] Ошибка при создании БД: {e}")

if __name__ == "__main__":
    create_final_db_structure()