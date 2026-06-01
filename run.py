import argparse
# ... импорты ...

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["bot", "web"], required=True)
    args = parser.parse_args()

    if args.mode == "bot":
        # Вызов логики бота
        pass
    elif args.mode == "web":
        # Вызов app.run()
        pass