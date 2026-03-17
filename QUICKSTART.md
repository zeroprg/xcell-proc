# 🚀 Быстрый старт

Начните работу с XCell Processor за 5 минут.

## 1️⃣ Установка (2 минуты)

### Windows
```powershell
# Клонируйте репозиторий
git clone <repository-url>
cd xcell-proc

# Создайте виртуальное окружение
python -m venv .venv
.venv\Scripts\activate

# Установите зависимости
pip install -r requirements.txt
```

### Linux/Mac
```bash
git clone <repository-url>
cd xcell-proc

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

## 2️⃣ Конфигурация (2 минуты)

```bash
# Скопируйте пример конфигурации
cp config/config.example.json config/config.json

# Отредактируйте config/config.json и укажите:
# - smtp.server и smtp.port (SMTP сервер)
# - smtp.username и smtp.password (или используйте .env)
# - paths.data_folder и paths.attachments_folder
```

**Для тестирования с Gmail:**
```bash
# Создайте App Password в Google Account
# https://myaccount.google.com/apppasswords

# Вариант 1: Временные переменные окружения
export SMTP_USERNAME='your-email@gmail.com'
export SMTP_PASSWORD='your-app-password'

# Вариант 2: Файл .env (удобнее)
echo "SMTP_USERNAME=your-email@gmail.com" > .env
echo "SMTP_PASSWORD=your-app-password" >> .env
chmod 600 .env
```

## 3️⃣ Первый запуск (1 минута)

### Отправить тестовое письмо

```bash
# Сухой запуск (без отправки, только предпросмотр)
python src/cli_email_sender.py \
  --test-recipient your-email@example.com \
  --subject "Тестовое письмо" \
  --body "Это тестовое письмо"

# Проверьте предпросмотр письма
cat logs/email_previews/*.eml
```

### Отправить настоящее письмо

```bash
# Добавьте флаг --send для реальной отправки
python src/cli_email_sender.py \
  --test-recipient your-email@example.com \
  --subject "Тестовое письмо" \
  --body "Это настоящее письмо" \
  --send

# Проверьте успешность в логах
cat logs/cron_notify.log
```

## 📧 Отправка писем с шаблоном

### Шаблон письма

Создайте или отредактируйте `templates/email_template.html`:

```html
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
  <h2>Здравствуйте, {{ name }}!</h2>
  <p>Это письмо отправлено {{ date }}</p>
  <p>Ваш email: {{ email }}</p>
  <p>Компания: {{ company }}</p>
</body>
</html>
```

### Отправка с шаблоном

```bash
python src/cli_email_sender.py \
  --to user@example.com \
  --subject "Привет" \
  --template email_template.html \
  --send
```

## 📎 Отправка вложений

```bash
python src/cli_email_sender.py \
  --to user@example.com \
  --subject "Отчёт" \
  --template email_template.html \
  --attachments attachments/report.pdf,attachments/data.xlsx \
  --send
```

## 📅 Просмотр расписания отпусков

```bash
python src/cli_vacations.py config/config.json
```

Выведет JSON с информацией об отпусках из Excel файла.

## 🎯 Самые полезные команды

```bash
# Справка по CLI
python src/cli_email_sender.py --help

# Сухой запуск (проверить без отправки)
python src/cli_email_sender.py --test-recipient you@example.com --subject "Test" --body "Test"

# Отправка с шаблоном
python src/cli_email_sender.py --to you@example.com --subject "Test" --template email_template.html --send

# Отправка с вложением
python src/cli_email_sender.py --test-recipient you@example.com --attachments file.pdf --send

# Запуск тестов
pytest tests/ -v

# Форматирование кода
black src/ tests/
```

## ⚠️ Важные правила безопасности

1. **Никогда не коммитьте:**
   - `config/config.json` (если содержит пароли)
   - `.env` файл с секретами
   - Реальные SMTP пароли

2. **Используйте App Passwords для Gmail:**
   - Не используйте основной пароль
   - Создайте отдельный пароль: https://myaccount.google.com/apppasswords

3. **Всегда тестируйте сначала:**
   ```bash
   # Без --send флага = сухой запуск
   python src/cli_email_sender.py --test-recipient test@example.com
   
   # Проверьте результат в logs/email_previews/
   # Только потом добавляйте --send
   ```

## 🆘 Частые проблемы

### Ошибка: `Config not found`
```bash
# Убедитесь, что скопировали конфигурацию
ls config/config.json
# Если нет — создайте:
cp config/config.example.json config/config.json
```

### Ошибка: `Connection refused`
```bash
# Проверьте SMTP параметры в config.json:
# - server: правильный адрес?
# - port: правильный порт? (587 для TLS, 465 для SSL, 25 для plain)
# - use_tls: true для порта 587
# - use_ssl: true для порта 465
```

### Письма не отправляются (но без ошибок)
```bash
# Вероятно, забыли флаг --send
# По умолчанию это сухой запуск!

# ❌ Неправильно (только предпросмотр):
python src/cli_email_sender.py --to you@example.com --subject "Test" --body "Test"

# ✅ Правильно (реальная отправка):
python src/cli_email_sender.py --to you@example.com --subject "Test" --body "Test" --send
```

### ModuleNotFoundError
```bash
# Убедитесь, что:
# 1. Активирована виртуальное окружение
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 2. Запускаете из корня проекта
cd /path/to/xcell-proc
python src/cli_email_sender.py ...

# 3. Установлены зависимости
pip install -r requirements.txt
```

## 📚 Дальше читайте

После первого успешного запуска ознакомьтесь с:

1. **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — понимание структуры проекта
2. **[docs/SHELL_SCRIPT_SETUP.md](docs/SHELL_SCRIPT_SETUP.md)** — как настроить автоматический запуск
3. **[README.md](README.md)** — полная документация всех возможностей

## 💡 Рекомендуемый следующий шаг

Установите автоматизацию для ежедневного запуска:

```bash
# На Linux: отредактируйте скрипт
nano scripts/run_daily_notify.sh
# Измените PROJECT_ROOT и PYTHON_EXEC

# Добавьте в crontab
crontab -e
# 0 2 * * * /bin/bash -lc '/path/to/xcell-proc/scripts/run_daily_notify.sh'

# Готово! Письма будут отправляться каждый день в 02:00
```

Подробнее: [docs/SHELL_SCRIPT_SETUP.md](docs/SHELL_SCRIPT_SETUP.md)

---

**Готово!** 🎉 Вы установили XCell Processor и отправили первое письмо.
