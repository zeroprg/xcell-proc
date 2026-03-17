# Excel Email Sender

Автоматическая система для извлечения email адресов из Excel файлов и отправки писем с вложениями.

**🚀 Новичок?** Начните с **[QUICKSTART.md](QUICKSTART.md)** — инструкция на 5 минут.

## Описание проекта

Проект предназначен для автоматизации процесса:
1. Чтение Excel файлов из указанной папки
2. Извлечение email адресов из файлов
3. Отправка персонализированных писем с вложениями

## Возможности

- ✅ Обработка файлов Excel (.xlsx, .xls)
- ✅ Автоматическое определение колонок с email
- ✅ Поддержка шаблонов писем
- ✅ Отправка вложений
- ✅ Логирование всех операций
- ✅ Обработка ошибок и повторные попытки отправки
- ✅ Конфигурация через файл настроек

## Требования

- Python 3.8+
- pip (менеджер пакетов Python)

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd xcell-proc
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
```

3. Активируйте виртуальное окружение:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

4. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Настройка

1. Скопируйте файл конфигурации:
```bash
cp config/config.example.json config/config.json
```

2. Отредактируйте `config/config.json` и укажите:
   - SMTP сервер и учетные данные
   - Путь к папке с Excel файлами
   - Путь к папке с вложениями
   - Настройки шаблона письма

3. Подготовьте шаблон письма в `templates/email_template.html`

## Структура проекта

```
xcell-proc/
├── src/
│   ├── __init__.py
│   ├── cli_email_sender.py      # CLI для отправки писем
│   ├── cli_vacations.py         # CLI для чтения расписания отпусков
│   ├── email_sender.py          # Класс EmailSender для отправки
│   ├── excel_reader.py          # Чтение Excel файлов
│   ├── vacation_reader.py       # Парсинг данных об отпусках
│   ├── notify_vacations.py      # Логика уведомлений об отпусках
│   └── utils.py                 # Вспомогательные функции
├── config/
│   ├── config.json              # Конфигурация (не в git)
│   └── config.example.json      # Пример конфигурации
├── templates/
│   └── email_template.html      # Шаблон письма
├── scripts/
│   └── run_daily_notify.sh      # Скрипт для запуска через cron
├── logs/
│   └── email_previews/          # Папка для предпросмотра писем (.eml)
├── data/
│   └── .gitkeep                 # Папка для Excel файлов
├── attachments/
│   └── .gitkeep                 # Папка для вложений
├── tests/
│   └── test_*.py                # Тесты
├── docs/
│   └── SMTP_AND_CRON.md         # Документация по SMTP и cron
├── .gitignore
├── .env                         # Переменные окружения (не в git)
├── requirements.txt
└── README.md
```

## Использование

Проект предоставляет два основных CLI инструмента:

### 1. Отправка писем (cli_email_sender.py)

Основной инструмент для отправки email с шаблонами и вложениями:

```bash
python src/cli_email_sender.py --help
```

**Типичные использования:**

```bash
# Отправить тестовое письмо (без отправки, только предпросмотр)
python src/cli_email_sender.py --test-recipient you@example.com --subject "Тест" --body "Тестовое письмо"

# Отправить письмо с использованием конфигурации
python src/cli_email_sender.py -c config/config.json --test-recipient admin@example.com --subject "Уведомление" --send

# Отправить письмо с вложением
python src/cli_email_sender.py --to user@example.com --subject "Отчет" --template email_template.html --attachments file1.pdf,file2.xlsx --send

# Сохранить предпросмотр письма в .eml файл
python src/cli_email_sender.py --test-recipient admin@example.com --subject "Проверка" --preview-dir logs/email_previews
```

**Параметры:**
- `--config, -c` — Путь к файлу конфигурации (default: `config/config.example.json`)
- `--to, -t` — Email получателей (через запятую)
- `--subject, -s` — Тема письма
- `--template` — Файл шаблона в папке `templates/`
- `--body` — Текст письма (если нет шаблона)
- `--attachments` — Пути к файлам (через запятую)
- `--send` — Действительно отправить письмо (без флага = сухой запуск)
- `--preview-dir` — Сохранять предпросмотры в указанную папку
- `--test-recipient` — Использовать один адрес для тестирования

### 2. Чтение расписания отпусков (cli_vacations.py)

Инструмент для парсинга данных об отпусках из Excel:

```bash
python src/cli_vacations.py config/config.example.json
```

Выводит JSON-расписание отпусков для всех сотрудников.

## Формат Excel файла

### Данные о сотрудниках

Excel файл должен содержать колонки:
- `email` или `Email` или `E-mail` - адрес электронной почты (обязательно)
- `name` или `Name` - имя получателя (опционально)
- `company` - название компании (опционально)

Пример:

| Email | Name | Company |
|-------|------|---------|
| user@example.com | Иван Иванов | ООО "Рога и Копыта" |
| admin@test.com | Петр Петров | ИП Петров |

### Расписание отпусков

Данные об отпусках парсятся из Excel листов, где каждый столбец представляет месяц, а строки — сотрудников. 
Дни отпусков отмечаются `+` или `V`, выходные и праздничные дни определяются по конфигурации.

## Шаблон письма

Шаблон письма `templates/email_template.html` поддерживает переменные Jinja2:
- `{{ name }}` - имя получателя
- `{{ email }}` - email получателя
- `{{ company }}` - название компании
- `{{ date }}` - текущая дата

Пример:
```html
<html>
<body>
<p>Здравствуйте, {{ name }}!</p>
<p>Ваш email: {{ email }}</p>
<p>Компания: {{ company }}</p>
<p>Дата: {{ date }}</p>
</body>
</html>
```

## Логирование

Все операции записываются в лог-файлы:
- `logs/cron_notify.log` — логи автоматических запусков через cron/systemd
- `logs/email_previews/` — предпросмотры отправленных писем в формате .eml
- Стандартный логер Python для отладки

## Автоматическое выполнение (Cron/Systemd)

### Быстрый старт

1. **Скопируйте скрипт** в подходящее место (или используйте существующий):
```bash
cp scripts/run_daily_notify.sh /usr/local/bin/xcell-notify
chmod 755 /usr/local/bin/xcell-notify
```

2. **Отредактируйте пути** в скрипте:
```bash
PROJECT_ROOT="/home/username/git-rep/xcell-proc"
PYTHON_EXEC="/home/username/.venv/bin/python"
```

3. **Добавьте в crontab** (запуск в 02:00 каждый день):
```bash
crontab -e
```
```
0 2 * * * /bin/bash -lc '/usr/local/bin/xcell-notify'
```

### Детальная документация

Полная документация по настройке SMTP, безопасной передаче секретов, cron, systemd timers и ротации логов находится в:

- **[docs/SMTP_AND_CRON.md](docs/SMTP_AND_CRON.md)** — безопасность SMTP и способы передачи учётных данных
- **[docs/SHELL_SCRIPT_SETUP.md](docs/SHELL_SCRIPT_SETUP.md)** — детальное руководство по скрипту `run_daily_notify.sh`, cron, systemd и logrotate

## Безопасность

⚠️ **ВАЖНО:**
- **Никогда** не добавляйте `config/config.json` в git (в .gitignore)
- **Никогда** не коммитьте `.env` файл с секретами
- Используйте переменные окружения или файл `.env` для чувствительных данных
- Храните пароли в безопасном месте или используйте App Passwords для Gmail

**Безопасная передача секретов:**

```bash
# Способ 1: Временные переменные в текущей сессии
export SMTP_USERNAME='your-email@gmail.com'
export SMTP_PASSWORD='app-password'
python src/cli_email_sender.py --test-recipient you@example.com --send

# Способ 2: Файл .env (локально, не в git)
echo "SMTP_USERNAME=your-email@gmail.com" > .env
echo "SMTP_PASSWORD=app-password" >> .env
chmod 600 .env  # Ограничить доступ
python src/cli_email_sender.py --test-recipient you@example.com --send
```

## Разработка

### Запуск тестов
```bash
pytest tests/
pytest tests/ --cov=src  # С отчетом покрытия
```

### Форматирование кода
```bash
black src/ tests/
flake8 src/ tests/
```

### Создание виртуального окружения
```bash
# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

## Решение проблем

### ❌ Ошибка: `Config not found: config/config.example.json`
```bash
# Убедитесь, что файл существует
ls config/config.example.json
```

### ❌ Ошибка подключения к SMTP
```
Failed to send email: [Errno 111] Connection refused
```
**Решение:**
- Проверьте адрес и порт SMTP сервера в конфигурации
- Убедитесь, что сервер доступен: `telnet smtp.gmail.com 587`
- Проверьте настройки брандмауэра
- Используйте `--send` флаг, в противном случае письма не отправляются

### ❌ Ошибка: `No module named 'src.email_sender'`
```
Убедитесь, что запускаете скрипт из корня проекта:
python src/cli_email_sender.py ...
(не из папки src)
```

### ❌ Не находятся email в Excel
- Проверьте название колонки: `email`, `Email` или `E-mail`
- Убедитесь в правильности формата email адресов
- Проверьте, что файл не открыт в другой программе

### ❌ Письма не отправляются (но без ошибок)
- По умолчанию запускается **сухой запуск** (dry-run)
- Добавьте флаг `--send` для реальной отправки
- Проверьте логи: `logs/cron_notify.log` или `logs/email_previews/`

## 📚 Документация

Полная документация проекта доступна в папке `docs/`:

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — архитектура проекта, описание модулей и потоки данных
- **[docs/SHELL_SCRIPT_SETUP.md](docs/SHELL_SCRIPT_SETUP.md)** — настройка автоматизации через shell скрипт, cron и systemd
- **[docs/SMTP_AND_CRON.md](docs/SMTP_AND_CRON.md)** — безопасность SMTP и способы передачи учётных данных

## Лицензия

MIT License

## Автор

Ваше имя / Ваша компания

## Поддержка

Для вопросов и предложений создавайте issues в репозитории.
