# XCell Processor — Архитектура и Дизайн

Этот документ описывает архитектуру проекта, структуру модулей и как они взаимодействуют друг с другом.

## 📐 Архитектура проекта

XCell Processor — это многомодульная система для:
1. **Чтения данных** из Excel (сотрудники, расписание отпусков)
2. **Отправки писем** через SMTP
3. **Автоматизации уведомлений** об отпусках
4. **Планирования** регулярного запуска через cron/systemd

### Слой-ориентированный дизайн

```
┌─────────────────────────────────────────────┐
│ CLI Layer (Интерфейс пользователя)          │
│ ├── cli_email_sender.py (отправка писем)   │
│ └── cli_vacations.py (чтение отпусков)    │
├─────────────────────────────────────────────┤
│ Business Logic Layer (Бизнес-логика)        │
│ ├── email_sender.py (EmailSender class)    │
│ ├── notify_vacations.py (логика уведомл.)  │
│ └── vacation_reader.py (парсинг отпусков)  │
├─────────────────────────────────────────────┤
│ Data Access Layer (Работа с данными)        │
│ ├── excel_reader.py (чтение Excel)         │
│ └── utils.py (вспомогательные функции)     │
├─────────────────────────────────────────────┤
│ Configuration & Infrastructure              │
│ ├── config/config.json (настройки)         │
│ ├── templates/ (шаблоны писем)             │
│ └── .env (переменные окружения)            │
└─────────────────────────────────────────────┘
```

## 📦 Модули и их функции

### 1. **cli_email_sender.py** — CLI для отправки писем

**Назначение:** Интерфейс командной строки для тестирования и отправки писем.

**Функции:**
- Парсинг аргументов командной строки
- Загрузка конфигурации из JSON
- Инициализация `EmailSender`
- Отправка тестовых писем с шаблонами
- Создание предпросмотров писем в формате `.eml`

**Пример использования:**
```bash
python src/cli_email_sender.py \
  --test-recipient admin@example.com \
  --subject "Тестовое письмо" \
  --template email_template.html \
  --send
```

### 2. **email_sender.py** — Класс EmailSender

**Назначение:** Основная логика отправки писем через SMTP.

**Класс: `EmailSender`**
- `__init__(smtp_config, templates_path)` — инициализация
- `render_template(template_name, context)` — рендеринг Jinja2 шаблонов
- `compose_message(subject, to, cc, body, attachments)` — формирование письма
- `send(subject, to, cc, body, attachments, dry_run, preview_dir)` — отправка

**Функции:**
- Подключение к SMTP серверу (с поддержкой TLS/SSL)
- Аутентификация по username/password
- Рендеринг шаблонов с переменными
- Добавление вложений
- Сохранение предпросмотров в `.eml` файлы
- Логирование операций

**Пример кода:**
```python
from src.email_sender import EmailSender

config = {
    'server': 'smtp.gmail.com',
    'port': 587,
    'use_tls': True,
    'username': 'your-email@gmail.com',
    'password': 'app-password',
    'from_name': 'System',
    'from_email': 'sender@example.com'
}

sender = EmailSender(config)
sender.send(
    subject='Hello',
    to=['user@example.com'],
    cc=[],
    body='Test message',
    dry_run=False,
    preview_dir='logs/email_previews'
)
```

### 3. **excel_reader.py** — Чтение Excel файлов

**Назначение:** Низкоуровневое чтение и парсинг Excel файлов.

**Функции:**
- Поддержка форматов `.xlsx` (openpyxl) и `.xls` (xlrd)
- Автоматическое определение листов
- Парсинг ячеек и таблиц
- Обработка ошибок при чтении

**Использование в других модулях:**
```python
from src.excel_reader import read_excel_file

data = read_excel_file('data/employees.xlsx')
# Возвращает список словарей с данными
```

### 4. **vacation_reader.py** — Парсинг расписания отпусков

**Назначение:** Специализированный модуль для чтения расписания отпусков из Excel.

**Функции:**
- Парсинг календарного формата Excel (месяцы/дни)
- Определение периодов отпусков по конфигурации
- Расчёт дат отпусков (начало/конец)
- Сопоставление с данными сотрудников

**Пример конфигурации:**
```json
{
  "vacation_settings": {
    "vacation_file": "data/vacations.xlsx",
    "vacation_sheet": "2024",
    "employee_column": "Employee",
    "start_month": 1,
    "end_month": 12
  }
}
```

**Использование:**
```python
from src.vacation_reader import read_vacation_schedule

config = json.load(open('config/config.json'))
schedule = read_vacation_schedule(config)
# Возвращает список с информацией об отпусках каждого сотрудника
```

### 5. **notify_vacations.py** — Логика уведомлений об отпусках

**Назначение:** Бизнес-логика отправки уведомлений о предстоящих отпусках.

**Функции:**
- `notify_due()` — отправка уведомлений о предстоящих отпусках
- Расчёт сроков (за N дней до отпуска, дедлайны согласования)
- Отправка писем менеджерам и финансовому отделу
- Отслеживание отправленных уведомлений

**Конфигурация:**
```json
{
  "notifications": {
    "preapproval_offset_days": 21,
    "deadline_offset_days": 8,
    "approval_deadline_days": 7,
    "manager_email_column": "manager_email",
    "fm_email_column": "fm_email"
  }
}
```

### 6. **cli_vacations.py** — CLI для чтения отпусков

**Назначение:** Инструмент для просмотра расписания отпусков в JSON формате.

**Использование:**
```bash
python src/cli_vacations.py config/config.example.json
```

**Вывод:** JSON с полной информацией об отпусках.

### 7. **utils.py** — Вспомогательные функции

**Назначение:** Общие утилиты, используемые другими модулями.

**Возможные функции:**
- Логирование с цветным выводом (colorlog)
- Обработка дат и времени
- Валидация email адресов
- Конвертация форматов

## 🔄 Потоки данных

### Сценарий 1: Отправка одиночного письма (тестирование)

```
cli_email_sender.py (парсинг аргументов)
    ↓
config.json (загрузка конфигурации)
    ↓
EmailSender.__init__ (инициализация)
    ↓
EmailSender.send() (отправка)
    ├── compose_message() (формирование письма)
    ├── SMTP.connect() (подключение)
    ├── SMTP.send_message() (отправка)
    ├── SMTP.quit() (отключение)
    └── logs/email_previews/*.eml (сохранение предпросмотра)
```

### Сценарий 2: Автоматическое уведомление об отпусках

```
run_daily_notify.sh (shell скрипт, запущенный cron)
    ↓
.env (загрузка переменных окружения)
    ↓
cli_email_sender.py (запуск CLI)
    ↓
notify_vacations.notify_due() (расчёт уведомлений)
    ├── vacation_reader.read_vacation_schedule()
    │   └── excel_reader.read_excel_file() (чтение Excel)
    ├── EmailSender.send() (отправка каждого письма)
    └── logs/cron_notify.log (логирование)
```

### Сценарий 3: Просмотр расписания отпусков

```
cli_vacations.py (CLI)
    ↓
config.json (загрузка конфигурации)
    ↓
vacation_reader.read_vacation_schedule()
    ├── excel_reader.read_excel_file() (чтение Excel)
    └── Парсинг расписания
    ↓
JSON output в консоль
```

## ⚙️ Конфигурация

### config/config.example.json

```json
{
  "paths": {
    "data_folder": "data",
    "attachments_folder": "attachments",
    "templates_folder": "templates"
  },
  "smtp": {
    "server": "smtp.gmail.com",
    "port": 587,
    "use_tls": true,
    "use_ssl": false,
    "timeout": 60,
    "username": "{{ env.SMTP_USERNAME }}",
    "password": "{{ env.SMTP_PASSWORD }}",
    "from_name": "Система",
    "from_email": "noreply@example.com"
  },
  "vacation_settings": {
    "vacation_file": "data/vacations.xlsx",
    "vacation_sheet": "2024",
    "employee_column": "ФИО",
    "weekends": [5, 6],
    "holidays": ["2024-01-01", "2024-12-31"]
  },
  "notifications": {
    "preapproval_offset_days": 21,
    "deadline_offset_days": 8,
    "manager_email_column": "manager_email",
    "fm_email_column": "fm_email"
  }
}
```

## 🧪 Тестирование

### Структура тестов

```
tests/
├── test_main.py          # (устарело, может быть удалено)
├── test_vacation_reader.py
└── __pycache__/
```

### Запуск тестов

```bash
pytest tests/              # Все тесты
pytest tests/ -v           # Подробный вывод
pytest tests/ --cov=src    # С отчетом покрытия
```

## 🔐 Безопасность

### Иерархия загрузки переменных

Проект загружает SMTP учётные данные в следующем порядке (первый найденный используется):

1. **Переменные окружения** (установлены перед запуском)
   ```bash
   export SMTP_USERNAME='...'
   export SMTP_PASSWORD='...'
   ```

2. **Файл .env** (загружается python-dotenv)
   ```
   SMTP_USERNAME=...
   SMTP_PASSWORD=...
   ```

3. **config.json** (может содержать плейсхолдеры `{{ env.VAR }}`)
   ```json
   {
     "smtp": {
       "username": "{{ env.SMTP_USERNAME }}"
     }
   }
   ```

4. **Жесткий код в config.json** (⚠️ не рекомендуется!)

### Рекомендации

- ✅ Используйте переменные окружения для чувствительных данных
- ✅ Используйте файл `.env` локально (dev-окружение)
- ✅ Используйте систему управления секретами в продакшене
- ❌ Не коммитьте учётные данные в git
- ❌ Не используйте простые пароли, используйте App Passwords

## 📚 Расширение проекта

### Добавление нового CLI инструмента

1. Создайте новый файл `src/cli_my_feature.py`
2. Определите функцию `main()`
3. Используйте `argparse` для аргументов
4. Добавьте документацию в README

Пример:
```python
# src/cli_my_feature.py
import argparse

def main():
    p = argparse.ArgumentParser(description='My feature CLI')
    p.add_argument('--option', help='Some option')
    args = p.parse_args()
    # ваша логика

if __name__ == '__main__':
    main()
```

### Добавление новой функциональности

1. **Business logic** → `src/new_module.py`
2. **CLI interface** → `src/cli_new_feature.py`
3. **Tests** → `tests/test_new_module.py`
4. **Documentation** → обновите README и docs/

## 🔗 Зависимости

```
openpyxl (3.1.2)      — Работа с .xlsx файлами
xlrd (2.0.1)          — Работа с .xls файлами
pandas (2.1.4)        — Обработка таблиц
python-dotenv (1.0.0) — Загрузка .env файлов
jinja2 (3.1.2)        — Шаблонизация писем
colorlog (6.8.0)      — Цветной логирования
python-dateutil       — Работа с датами
pytest (7.4.3)        — Тестирование
```

## 📝 Лучшие практики

1. **Логирование** — используйте `logging` модуль:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.info('Operation successful')
   logger.error('Operation failed', exc_info=True)
   ```

2. **Обработка ошибок** — всегда оборачивайте SMTP операции:
   ```python
   try:
       sender.send(...)
   except Exception as e:
       logger.error(f'Send failed: {e}')
   ```

3. **Конфигурация** — всегда используйте параметры из config/env:
   ```python
   port = int(config['smtp'].get('port', 25))
   ```

4. **Тестирование** — тестируйте с `--dry-run` перед `--send`

## 🎯 Дальнейшее развитие

Потенциальные улучшения:
- [ ] Поддержка шаблонов других типов (markdown, plain text)
- [ ] Отправка писем в фоновом процессе (celery/rq)
- [ ] Web интерфейс для управления уведомлениями
- [ ] Интеграция с календарными системами (Google Calendar, Outlook)
- [ ] Аналитика и отчёты об отправленных письмах
- [ ] Webhook'и для интеграции с внешними системами
