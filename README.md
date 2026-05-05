Как начать работать с Git

Инициализируйте репозиторий и добавьте файл программы:
git init
git add currency_converter.py
git commit -m "Initial: Currency Converter with API, history and JSON export/import"
Игнорируйте временные файлы:
создайте .gitignore и добавьте: *.pyc, pycache/, venv/
Регулярно сохраняйте изменения:
git add .
git commit -m "Добавлена функция конвертации, экспорт/импорт истории"
Расширения (по желанию)

поддержка OAuth/аутентификации для повышения лимита API
кэш курсов в SQLite или файле
графики расходов по дням (matplotlib/plotly)
синхронизация истории через GitHub Gist или облако
