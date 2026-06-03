import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from dotenv import load_dotenv

# Импортируем наши модули из пакета app
from app.database.db_manager import DBManager
from app.services.leak_checker import check_email_in_leakcheck

# Загружаем переменные окружения
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret_key_123')

# Инициализируем БД
db = DBManager()

@app.route('/')
def index():
    # Получаем последние 20 инцидентов
    incidents = db.get_latest_incidents(limit=20)
    return render_template('index.html', incidents=incidents)


@app.route('/check', methods=['POST'])
def check_email():
    email = request.form.get('email', '').strip()

    if not email:
        flash("Пожалуйста, введите email для проверки.")
        return redirect(url_for('index'))

    # 1. Проверяем email по внешнему API (Твой пункт 1)
    api_sources = check_email_in_leakcheck(email)

    # Проверяем, принадлежит ли этот email кому-то из сотрудников компании
    staff_id = db.get_staff_id_by_email(email)

    # 2. Если что-то найдено...
    if api_sources and not isinstance(api_sources, int):
        # Флаг: нужно ли еще создавать инцидент в этой сессии проверки?
        incident_needed = True

        for source in api_sources:
            # Логи сохраняем все, чтобы на экране отобразился полный список тегов
            scraped_id = db.add_external_leak_if_not_exists(email, source)

            # В таблицу инцидентов стучимся ТОЛЬКО ОДИН РАЗ для первого источника
            if staff_id and scraped_id and incident_needed:
                db.create_incident_direct(staff_id, scraped_id)
                incident_needed = False  # Выключаем триггер, для остальных сайтов инцидент не создастся
    else:
        api_sources = []

    # Если email не сотрудника — код выше просто пропустит создание инцидента,
    # но ниже мы всё равно соберем инфу и выведем её красивыми тегами на фронтенд!
    local_sources = db.get_local_sources_by_email(email)
    local_sources_styled = [f"💾 Локально: {src}" for src in local_sources]
    combined_sources = local_sources_styled + api_sources

    # Загружаем актуальный список инцидентов для таблицы на главной странице
    all_incidents = db.get_latest_incidents(limit=100)

    return render_template('index.html',
                           incidents=all_incidents,
                           email_checked=email,
                           sources=combined_sources)


@app.route('/analyze')
def run_full_analysis():
    # Запускаем только локальный быстрый матчинг (без внешних API в цикле)
    # Это отработает за доли секунды, сколько бы сотрудников ни было
    count = db.run_incident_check()

    if count > 0:
        flash(f'Глобальный анализ завершен. Выявлено новых инцидентов: {count}')
    else:
        flash('Глобальный анализ завершен. Новых совпадений с локальной базой не найдено.')

    return redirect(url_for('index'))


# ====================================================
# УПРАВЛЕНИЕ ПЕРСОНАЛОМ (STAFF MANAGEMENT)
# ====================================================

@app.route('/staff')
def staff_list():
    # Получаем список всех сотрудников из БД
    workers = db.get_all_staff()
    return render_template('staff.html', workers=workers)


@app.route('/staff/add', methods=['POST'])
def add_worker():
    fio = request.form.get('fio', '').strip()
    email = request.form.get('email', '').strip()
    role = request.form.get('role', '').strip()

    if fio and email:
        db.add_staff(fio, email, role)
        flash(f'Сотрудник {fio} успешно добавлен в систему.')
    else:
        flash('ФИО и Email обязательны для заполнения!', 'danger')

    return redirect(url_for('staff_list'))


@app.route('/staff/edit/<int:worker_id>', methods=['POST'])
def edit_worker(worker_id):
    fio = request.form.get('fio', '').strip()
    email = request.form.get('email', '').strip()
    role = request.form.get('role', '').strip()

    if fio and email:
        db.update_staff(worker_id, fio, email, role)
        flash('Данные сотрудника успешно обновлены.')
    else:
        flash('ФИО и Email не могут быть пустыми!', 'danger')

    return redirect(url_for('staff_list'))


@app.route('/staff/delete/<int:worker_id>')
def delete_worker(worker_id):
    db.delete_staff(worker_id)
    flash('Сотрудник удален из системы базы данных.')
    return redirect(url_for('staff_list'))


@app.route('/incidents')
def incidents_list():
    all_incidents = db.get_all_incidents()
    return render_template('incidents.html', incidents=all_incidents)


import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify


# Импортируй сюда свою функцию подключения к БД (get_db_connection или db.session)

@app.route('/settings')
def settings_page():
    db = DBManager()

    # 1. Получаем источники веб-скрапера
    with db.conn.cursor() as cur:
        cur.execute("SELECT id, source_name, source_url FROM scraper_sources;")
        web_sources = cur.fetchall()

    # 2. Получаем источники Telegram-коллектора из новой таблицы
    with db.conn.cursor() as cur:
        cur.execute("SELECT id, channel_name, chat_id FROM telegram_sources ORDER BY id DESC;")
        tg_sources = cur.fetchall()

    # Рендерим страницу и передаем оба списка
    return render_template('settings.html', sources=web_sources, tg_sources=tg_sources)

@app.route('/settings/delete-source/<int:source_id>', methods=['POST'])
def delete_source(source_id):
    try:
        with db.conn.cursor() as cur:
            cur.execute("DELETE FROM scraper_sources WHERE id = %s;", (source_id,))
            db.conn.commit()
        return jsonify({"status": "success", "message": "Источник успешно удален из базы данных"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Ошибка БД: {str(e)}"}), 500


# В самый верх файла к остальным импортам
from app.core.web_scrp import WebScraper


@app.route('/settings/run-scraper', methods=['POST'])
def run_scraper_manual():
    try:
        # Создаем экземпляр скрапера и запускаем ОДИН круг обхода всех источников из БД
        scraper = WebScraper()
        scraper.run()

        return jsonify({
            "status": "success",
            "message": "Все OSINT-источники успешно просканированы. База обновлена!"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Ошибка при работе скрапера: {str(e)}"
        })


from flask import request, jsonify


@app.route('/settings/delete-tg-source/<int:source_id>', methods=['POST'])
def delete_tg_source(source_id):
    try:
        db = DBManager()
        with db.conn.cursor() as cur:
            cur.execute("DELETE FROM telegram_sources WHERE id = %s;", (source_id,))
            db.conn.commit()
        return jsonify({"status": "success", "message": "Ресурс успешно удален из мониторинга"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Ошибка БД: {str(e)}"}), 500


@app.route('/settings/edit-tg-source/<int:source_id>', methods=['POST'])
def edit_tg_source(source_id):
    try:
        data = request.get_json()
        channel_name = data.get('channel_name')
        chat_id = data.get('chat_id')

        if not channel_name or not chat_id:
            return jsonify({"status": "error", "message": "Все поля должны быть заполнены"}), 400

        db = DBManager()
        with db.conn.cursor() as cur:
            cur.execute(
                "UPDATE telegram_sources SET channel_name = %s, chat_id = %s WHERE id = %s;",
                (channel_name, chat_id, source_id)
            )
            db.conn.commit()
        return jsonify({"status": "success", "message": "Настройки источника успешно изменены"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Ошибка БД: {str(e)}"}), 500

import os
from flask import jsonify
import subprocess
import sys
import os


def start_bot_process():
    # 1. Получаем путь к папке, где лежит app.py (корень проекта)
    # Если app.py лежит в корне, используем os.getcwd() или __file__
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. Формируем путь к файлу tg_collector.py
    # Он лежит в app/core/tg_collector.py
    script_path = os.path.join(base_dir, '..', 'core', 'tg_collector.py')

    # 3. Проверка существования файла
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Файл бота не найден по пути: {script_path}")

    # 4. Запуск
    process = subprocess.Popen([sys.executable, script_path])
    return process.pid

start_counts = {}

@app.route('/settings/run-tg-scraper', methods=['POST'])
def run_tg_scraper():
    start_counts['count_before'] = db.get_total_leaks_count()
    # 1. Проверяем, не запущен ли уже бот
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Ищем наш скрипт в списке запущенных процессов
            if 'tg_collector.py' in str(proc.info['cmdline']):
                return {"status": "error", "message": "Бот уже запущен"}, 400
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # 2. Если не запущен — запускаем
    try:
        pid = start_bot_process()
        return {"status": "success", "message": f"Бот запущен (PID: {pid})"}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/settings/status-tg-scraper', methods=['GET'])
def status_tg_scraper():
    for proc in psutil.process_iter(['pid', 'cmdline']):
        # Проверяем, запущен ли наш скрипт
        if proc.info['cmdline'] and 'tg_collector.py' in str(proc.info['cmdline']):
            return jsonify({"running": True})
    return jsonify({"running": False})

import psutil
@app.route('/settings/stop-tg-scraper', methods=['POST'])
def stop_tg_scraper():
    for proc in psutil.process_iter(['pid', 'cmdline']):
        if proc.info['cmdline'] and 'tg_collector.py' in str(proc.info['cmdline']):
            proc.terminate()
            proc.wait(timeout=3)

            # 3. Считаем, сколько записей стало ПОСЛЕ
            count_after = db.get_total_leaks_count()
            count_before = start_counts.get('count_before', count_after)

            diff = count_after - count_before

            return {"status": "stopped", "message": f"Сканер остановлен. Найдено утечек за сессию: {diff}"}
    return {"status": "error", "message": "Сканер не запущен"}, 400


@app.route('/settings/save-source', methods=['POST'])
def save_source():
    # Получаем данные из формы
    source_id = request.form.get('source_id')  # Это поле скрыто в вашей форме
    name = request.form.get('source_name')
    url = request.form.get('source_url')

    try:
        with db.conn.cursor() as cur:
            if source_id and source_id.strip():
                # Если передан ID, обновляем существующую запись
                cur.execute(
                    "UPDATE scraper_sources SET source_name = %s, source_url = %s WHERE id = %s;",
                    (name, url, source_id)
                )
                flash(f"Источник '{name}' успешно обновлен.")
            else:
                # Если ID пустой, создаем новую запись
                cur.execute(
                    "INSERT INTO scraper_sources (source_name, source_url) VALUES (%s, %s);",
                    (name, url)
                )
                flash(f"Источник '{name}' успешно добавлен.")

            db.conn.commit()
    except Exception as e:
        flash(f"Ошибка при работе с базой данных: {str(e)}", "danger")

    return redirect(url_for('settings_page'))


@app.route('/settings/add-tg-source', methods=['POST'])
def add_tg_source():
    name = request.form.get('channel_name')
    chat_id = request.form.get('chat_id')
    with db.conn.cursor() as cur:
        cur.execute("INSERT INTO telegram_sources (channel_name, chat_id) VALUES (%s, %s)", (name, chat_id))
        db.conn.commit()
    flash("Канал добавлен")
    return redirect(url_for('settings_page'))


if __name__ == '__main__':
    # debug=True только для разработки!
    app.run(debug=True, port=5000)
