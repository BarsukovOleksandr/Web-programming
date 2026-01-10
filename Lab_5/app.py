import re
from flask import Flask, render_template, request
from datetime import datetime
import os

app = Flask(__name__)

EMAIL_REGEX = r'^[\w\.-]+@[\w\.-]+\.\w+$'

# Папка для збереження файлів
SAVE_DIR = 'submissions'
os.makedirs(SAVE_DIR, exist_ok=True)

@app.route('/form', methods=['GET', 'POST'])
def form():
    data = {
        'name': '',
        'email': '',
        'age': '',
        'message': ''
    }
    errors = {}
    saved_file = None
    valid = False

    if request.method == 'POST':
        for key in data:
            data[key] = request.form.get(key, '').strip()

        # Валідація
        for field, value in data.items():
            if not value:
                errors[field] = 'Поле є обов’язковим'

        if data['email'] and not re.match(EMAIL_REGEX, data['email']):
            errors['email'] = 'Некоректний формат email'

        if data['age'] and not data['age'].isdigit():
            errors['age'] = 'Поле має містити лише цифри'

        # Збереження у файл після успішної валідації
        if not errors:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"submission_{timestamp}.txt"
            filepath = os.path.join(SAVE_DIR, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                for key, value in data.items():
                    f.write(f"{key}: {value}\n")

            saved_file = filename
            valid = True

    return render_template('form.html', data=data, errors=errors, saved_file=saved_file, valid=valid)


@app.route('/result', methods=['GET'])
def result():
    # Отримання GET-параметрів останнього відправлення (якщо потрібно)
    latest_submission = {
        'name': request.args.get('name', ''),
        'email': request.args.get('email', ''),
        'age': request.args.get('age', ''),
        'message': request.args.get('message', ''),
        'file': request.args.get('file', '')
    }

    # Зчитування всіх текстових файлів з папки submissions
    all_files = []
    for filename in sorted(os.listdir(SAVE_DIR), reverse=True):
        if filename.endswith('.txt'):
            filepath = os.path.join(SAVE_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            all_files.append({'filename': filename, 'content': content})

    return render_template('result.html', latest=latest_submission, all_files=all_files)
    

if __name__ == '__main__':
    app.run(debug=True)
