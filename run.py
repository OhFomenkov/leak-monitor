from app.web.app import app

if __name__ == "__main__":
    # Просто запускаем Flask приложение
    print("--- Запуск Sentinel Monitor ---")
    app.run(debug=True, port=5000)
