from flask import Flask, render_template_string, request, redirect

app = Flask(__name__)

# Список для хранения сообщений в памяти
posts = [{"user": "System", "content": "Welcome to the Secure Monitoring Test Board."}]

HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Leak Board v1.0</title>
    <style>
        body { background: #0a0a0a; color: #00ff41; font-family: 'Courier New', monospace; padding: 40px; }
        .container { max-width: 800px; margin: auto; border: 1px solid #00ff41; padding: 20px; box-shadow: 0 0 15px #00ff41; }
        .post { background: #111; border-left: 5px solid #ff0000; padding: 15px; margin-bottom: 20px; color: #eee; }
        textarea { width: 100%; background: #000; color: #00ff41; border: 1px solid #00ff41; padding: 10px; margin-bottom: 10px; }
        input[type="submit"] { background: #00ff41; color: #000; border: none; padding: 10px 30px; cursor: pointer; font-weight: bold; }
        input[type="submit"]:hover { background: #008f11; }
    </style>
</head>
<body>
    <div class="container">
        <h1>[!] DATABASE_LEAK_FORUM</h1>
        <div id="feed">
            {% for post in posts %}
            <div class="post">
                <small style="color: #00ff41;">User: {{ post.user }}</small><br>
                <pre>{{ post.content }}</pre>
            </div>
            {% endfor %}
        </div>
        <hr style="border-color: #333;">
        <form method="POST">
            <textarea name="leak_data" rows="6" placeholder="Вставьте дамп здесь (email:password)..."></textarea>
            <input type="submit" value="ОПУБЛИКОВАТЬ ДАННЫЕ">
        </form>
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        data = request.form.get('leak_data')
        if data:
            posts.append({"user": "Artyom_F", "content": data})
        return redirect('/')
    return render_template_string(HTML_LAYOUT, posts=posts)

if __name__ == '__main__':
    app.run(port=5001, debug=False)