# Shell Script и Cron Setup для Автоматических Уведомлений

Этот документ описывает как настроить автоматический запуск уведомлений через shell скрипт и cron на Linux, или systemd timer.

## 📋 Обзор run_daily_notify.sh

Скрипт `scripts/run_daily_notify.sh` предназначен для:

1. **Загрузки переменных окружения** из файла `.env` (если существует)
2. **Предотвращения параллельных запусков** через `flock` (файловую блокировку)
3. **Запуска CLI** с нужными параметрами
4. **Логирования** всех операций в `logs/cron_notify.log`

### Содержимое скрипта

```bash
#!/usr/bin/env bash
set -euo pipefail
# Wrapper to run nightly notifications
# Adjust the following paths to your environment before enabling cron/systemd

# Project root (modify if different)
PROJECT_ROOT="/home/username/git-rep/xcell-proc"
# Python executable inside venv
PYTHON_EXEC="/home/username/.venv/bin/python"
# Lock file to prevent concurrent runs
LOCK_FILE="/var/lock/notify_vacations.lock"
# Log file
LOG_FILE="$PROJECT_ROOT/logs/cron_notify.log"

cd "$PROJECT_ROOT"

# load .env if present
if [ -f .env ]; then
  # export variables from .env safely
  set -a
  . .env
  set +a
fi

# ensure log dir exists
mkdir -p "$(dirname "$LOG_FILE")"

# use flock to prevent overlaps
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "Another instance is running; exiting" >> "$LOG_FILE"
  exit 0
fi

"$PYTHON_EXEC" src/cli_email_sender.py --test-recipient admin@example.com --subject "Авто-уведомления" --send >> "$LOG_FILE" 2>&1
```

## 🔧 Настройка

### Шаг 1: Отредактируйте пути в скрипте

Откройте `scripts/run_daily_notify.sh` и измените:

```bash
PROJECT_ROOT="/home/your-username/git-rep/xcell-proc"
PYTHON_EXEC="/home/your-username/.venv/bin/python"
```

**Где найти правильные пути:**

```bash
# Путь к проекту
pwd  # выведет текущую папку

# Путь к Python в venv
which python  # если venv активирован
# или
ls /path/to/.venv/bin/python
```

### Шаг 2: Установите права доступа

```bash
chmod 700 scripts/run_daily_notify.sh
```

### Шаг 3: Протестируйте скрипт вручную

```bash
bash scripts/run_daily_notify.sh
```

Проверьте логи:
```bash
cat logs/cron_notify.log
```

## 📅 Запуск через Cron (рекомендуется)

### Добавление в crontab

```bash
crontab -e
```

Добавьте строку для запуска в 02:00 каждый день:

```
0 2 * * * /bin/bash -lc '/home/username/git-rep/xcell-proc/scripts/run_daily_notify.sh'
```

### Объяснение cron выражения

```
0 2 * * *
│ │ │ │ │
│ │ │ │ └── День недели (0-6, 0 = воскресенье)
│ │ │ └──── Месяц (1-12)
│ │ └────── День месяца (1-31)
│ └──────── Час (0-23)
└────────── Минута (0-59)
```

**Примеры:**
- `0 2 * * *` — каждый день в 02:00
- `0 9 * * 1-5` — в 09:00 по будням (понедельник-пятница)
- `0 */6 * * *` — каждые 6 часов

### Проверка установленных правил

```bash
# Просмотр всех правил для текущего пользователя
crontab -l

# Просмотр логов cron
journalctl -u cron --follow  # systemd
tail -f /var/log/cron        # традиционный syslog
```

### Отладка cron

Если скрипт не запускается:

1. **Убедитесь, что использованы абсолютные пути:**
```bash
# ❌ Неправильно
0 2 * * * bash scripts/run_daily_notify.sh

# ✅ Правильно
0 2 * * * /bin/bash -lc '/home/username/git-rep/xcell-proc/scripts/run_daily_notify.sh'
```

2. **Используйте опцию `-lc`** для загрузки профиля оболочки:
```bash
0 2 * * * /bin/bash -lc 'cd /home/username/git-rep/xcell-proc && scripts/run_daily_notify.sh'
```

3. **Проверьте права доступа:**
```bash
ls -la scripts/run_daily_notify.sh
# Должно быть: -rwx------
```

4. **Добавьте debug логирование** в скрипт:
```bash
echo "Cron job started at $(date)" >> "$LOG_FILE"
```

## 🔄 Systemd Timer (современная альтернатива)

Для систем с systemd вместо cron можно использовать timer.

### Создание Service файла

Создайте `~/.config/systemd/user/xcell-notify.service`:

```ini
[Unit]
Description=XCell Vacation Notifications Service
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/home/username/git-rep/xcell-proc
ExecStart=/home/username/.venv/bin/python src/cli_email_sender.py --test-recipient admin@example.com --subject "Авто-уведомления" --send
StandardOutput=append:%h/git-rep/xcell-proc/logs/cron_notify.log
StandardError=append:%h/git-rep/xcell-proc/logs/cron_notify.log
```

### Создание Timer файла

Создайте `~/.config/systemd/user/xcell-notify.timer`:

```ini
[Unit]
Description=Run XCell Notifications Daily at 02:00
Requires=xcell-notify.service

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true
Accuracy=1min

[Install]
WantedBy=timers.target
```

### Включение и запуск

```bash
# Перезагрузить systemd конфигурацию
systemctl --user daemon-reload

# Включить таймер при загрузке
systemctl --user enable xcell-notify.timer

# Запустить таймер сейчас
systemctl --user start xcell-notify.timer

# Проверить статус
systemctl --user status xcell-notify.timer
systemctl --user list-timers

# Просмотр логов
journalctl --user-unit xcell-notify.service -f
```

## 📝 Ротация логов (logrotate)

Чтобы логи не заполнили диск, настройте ротацию.

### Создание конфигурации logrotate

Создайте `/etc/logrotate.d/xcell-proc` (требует sudo):

```
/home/username/git-rep/xcell-proc/logs/*.log {
    daily
    rotate 14
    copytruncate
    compress
    missingok
    notifempty
    create 0640 username username
}
```

### Объяснение параметров

- `daily` — ротировать ежедневно
- `rotate 14` — хранить последние 14 файлов
- `copytruncate` — скопировать и обрезать (безопаснее, чем `delaycompress`)
- `compress` — сжимать старые логи (gzip)
- `missingok` — не ошибаться, если файла нет
- `notifempty` — не ротировать пустые файлы
- `create` — создать новый файл с нужными правами

### Проверка конфигурации

```bash
logrotate -d /etc/logrotate.d/xcell-proc  # dry-run
logrotate -f /etc/logrotate.d/xcell-proc  # принудительно
```

## 🔐 Переменные окружения и .env файл

Скрипт автоматически загружает переменные из `.env`:

```bash
# Создайте .env в корне проекта
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

**Не забудьте ограничить доступ:**

```bash
chmod 600 .env
```

Переменные будут доступны для скрипта и Python кода через `EmailSender`.

## ✅ Чек-лист перед включением Cron

- [ ] Отредактировал пути в `scripts/run_daily_notify.sh`
- [ ] Сделал скрипт исполняемым: `chmod 700 scripts/run_daily_notify.sh`
- [ ] Протестировал скрипт вручную: `bash scripts/run_daily_notify.sh`
- [ ] Проверил логи: `cat logs/cron_notify.log`
- [ ] Создал `.env` файл с переменными (если нужны)
- [ ] Ограничил права доступа: `chmod 600 .env`
- [ ] Добавил правило в `crontab -e`
- [ ] Проверил статус: `crontab -l`
- [ ] Дождался запуска и проверил логи
- [ ] Настроил logrotate для ротации логов

## 🐛 Решение проблем

### Скрипт не запускается через cron

**Проблема:** Правило в crontab существует, но скрипт не работает.

**Решение:**
1. Используйте абсолютные пути везде
2. Проверьте права: `chmod 700 scripts/run_daily_notify.sh`
3. Добавьте диагностику в скрипт:
```bash
echo "Script executed at $(date)" >> "$LOG_FILE"
env | grep SMTP >> "$LOG_FILE"  # Проверьте переменные
```
4. Посмотрите логи cron:
```bash
journalctl -u cron -n 50
tail -f /var/log/cron
```

### "Another instance is running; exiting"

Это нормально — означает, что предыдущий запуск еще не закончился. Если это происходит часто:
- Увеличьте время выполнения между запусками (измените расписание в crontab)
- Или улучшите производительность скрипта (кэширование, оптимизация запросов)

### Письма не отправляются

1. Проверьте логи: `tail -f logs/cron_notify.log`
2. Убедитесь, что используется флаг `--send` в скрипте
3. Проверьте переменные SMTP в `.env` или конфиге
4. Протестируйте вручную: `python src/cli_email_sender.py --test-recipient you@example.com --send`

### Переменные окружения не загружаются

Скрипт явно экспортирует переменные из `.env`:
```bash
if [ -f .env ]; then
  set -a
  . .env
  set +a
fi
```

Убедитесь, что:
1. Файл `.env` существует в корне проекта
2. Права доступа позволяют его читать: `chmod 600 .env`
3. Переменные в формате `KEY=VALUE` (без пробелов)
4. В `EmailSender` используется переменная из config или переменных окружения

## 📚 Ссылки

- [Crontab Guru](https://crontab.guru/) — интерактивный генератор cron выражений
- [Systemd timer documentation](https://wiki.archlinux.org/title/Systemd/Timers)
- [Logrotate man page](https://linux.die.net/man/8/logrotate)
- [Python-dotenv документация](https://python-dotenv.readthedocs.io/)
