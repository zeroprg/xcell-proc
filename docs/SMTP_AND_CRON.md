Безопасные SMTP-учётные данные и планирование
Этот документ описывает безопасные способы передачи SMTP-учётных данных в проект для тестирования и как запускать CLI один раз в сутки через cron (Linux). Также приведены рекомендуемые лучшие практики тестирования и логирования.
1. Основные правила безопасности

Никогда не коммитьте реальные учётные данные в git.
Предпочитайте переменные окружения или системные хранилища секретов текстовым файлам.
Всегда сначала тестируйте в режиме --dry-run, чтобы не отправлять настоящие письма.

2. Временные переменные в сессии PowerShell (безопасно для тестов)
PowerShell$env:SMTP_USERNAME='your-email@gmail.com'
$env:SMTP_PASSWORD='app-password'
# запуск теста
python src/cli_email_sender.py --test-recipient you@example.com --subject "Проверка" --body "Тест" --send
# удаление секретов из сессии после теста
Remove-Item Env:\SMTP_PASSWORD; Remove-Item Env:\SMTP_USERNAME
3. Постоянные переменные окружения (не рекомендуется для секретов)
PowerShellsetx SMTP_USERNAME "your-email@gmail.com"
setx SMTP_PASSWORD "app-password"
Предупреждение: setx сохраняет значения в реестре в открытом виде.
4. Файл .env (кроссплатформенный вариант)
Создайте .env в корне проекта (не добавляйте в git):
textSMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=app-password
Ограничьте права:
Linux/macOS:
Bashchmod 600 .env
Windows (PowerShell):
PowerShellicacls .env /inheritance:r
icacls .env /grant:r "$($env:USERNAME):(R)"
Загружайте через python-dotenv или экспортируйте перед запуском.
5. Рекомендуемый подход в продакшене

Используйте менеджер секретов ОС/облака (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager, Windows Credential Manager).
Создавайте App Password для Gmail с минимальными правами.

6. Варианты тестирования

MailHog / MailCatcher: smtp.server=localhost, порт 1025, без учётных данных.
Бесплатные SMTP-релеи (проверяйте лимиты и TLS).
Gmail: smtp.gmail.com:587, STARTTLS + App Password.

7. Cron — запуск раз в сутки (Linux)
Создайте скрипт scripts/run_daily_notify.sh:
Bash#!/usr/bin/env bash
set -e
cd /home/username/git-rep/xcell-proc

if [ -f .env ]; then
  set -a
  . .env
  set +a
fi

exec 9>/var/lock/notify_vacations.lock
if ! flock -n 9; then
  echo "Другая копия уже запущена" >&2
  exit 0
fi

/home/username/.venv/bin/python src/cli_email_sender.py --test-recipient admin@example.com --subject "Авто-уведомления" --send >> logs/cron_notify.log 2>&1
Bashchmod 700 scripts/run_daily_notify.sh
Запись в crontab (02:00):
text0 2 * * * /bin/bash -lc '/home/username/git-rep/xcell-proc/scripts/run_daily_notify.sh'
8. Защита от параллельного запуска
Используйте flock (как в примере выше) или pid-файл.
9. Ротация логов (logrotate)
Пример /etc/logrotate.d/xcell-proc:
text/home/username/git-rep/xcell-proc/logs/*.log {
  daily
  rotate 14
  copytruncate
  compress
  missingok
}
10. Альтернатива — systemd timer
~/.config/systemd/user/notify.service:
text[Unit]
Description=Ежедневная отправка уведомлений

[Service]
Type=oneshot
WorkingDirectory=/home/username/git-rep/xcell-proc
ExecStart=/home/username/.venv/bin/python src/cli_email_sender.py --test-recipient admin@example.com --send
~/.config/systemd/user/notify.timer:
text[Unit]
Description=Запуск уведомлений каждый день в 02:00

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
Bashsystemctl --user enable --now notify.timer
11. Чек-лист перед запуском

Протестируйте вручную с --dry-run.
Отправьте тестовое письмо на реальный адрес.
Убедитесь, что секреты защищены и не в git.
Настройте ротацию логов и мониторинг ошибок.

12. Быстрое устранение проблем

535 BadCredentials → неверные данные / нужен App Password.
Ошибки TLS → проверьте порт и параметры use_tls/use_ssl.
Нет соединения → firewall / ограничения провайдера.



**Secure SMTP Credentials & Scheduling**

This document shows safe ways to provide SMTP credentials to the project for testing and how to schedule the CLI to run once per night using cron (Linux). It also includes recommended best practices for testing and logging.

**1. Quick safety rules**
- Do not commit real credentials into git.
- Prefer environment variables or OS secret stores over plaintext files.
- Always test in `dry-run` mode first so no real mail is sent.

**2. Temporary PowerShell session variables (safe for interactive tests)**
- For an interactive session (only for the current PowerShell session):
```powershell
$env:SMTP_USERNAME='your-email@gmail.com'
$env:SMTP_PASSWORD='app-password'
# run your test
python src/cli_email_sender.py --test-recipient you@example.com --subject "Проверка" --body "Тест" --send
# clear the secrets from the session when done
Remove-Item Env:\SMTP_PASSWORD; Remove-Item Env:\SMTP_USERNAME
```
- This keeps credentials in memory only for the session and avoids writing them to disk.

**3. Persistent environment variables (not recommended for secrets)**
- To persist for the Windows user (visible to other processes and stored in registry):
```powershell
setx SMTP_USERNAME "your-email@gmail.com"
setx SMTP_PASSWORD "app-password"
```
- Warning: `setx` stores values in user environment variables in plaintext. Prefer credential stores or `.env` with restricted permissions.

**4. Using a `.env` file (cross-platform, file-based)**
- Create a `.env` at project root (do NOT commit it):
```
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=app-password
```
- Restrict file permissions (Linux/macOS):
```bash
chmod 600 .env
```
- On Windows, restrict with ACLs (PowerShell):
```powershell
icacls .env /inheritance:r
icacls .env /grant:r "$($env:USERNAME):(R)"
```
- Load `.env` in your CLI by exporting the variables before running the command, or add `python-dotenv` to your project and call `load_dotenv()` early in `src/cli_email_sender.py`.

**5. Recommended production approach**
- Use the OS secret manager if available (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager, Windows Credential Manager) and fetch credentials at runtime.
- Alternatively, use per-service credentials (App Passwords for Gmail) with minimal scope and revoke them after tests.

**6. Testing options (choose one)**
- MailHog / MailCatcher (local dev testing): configure `smtp.server=localhost`, `port=1025`. No credentials needed. View messages in the MailHog web UI.
- freesmtpservers.com or other free relay: check provider docs for auth/no-auth, rate limits and TLS requirements.
- Gmail: use `smtp.gmail.com`, port `587` with STARTTLS; create an App Password (if 2FA enabled).

**7. Cron: run once per night (Linux)**

Recommended approach: use a wrapper script that:
- activates the virtualenv, 
- loads environment variables from a secure `.env` or system secret,
- runs the CLI, and
- writes stdout/stderr to a log file.

Create `scripts/run_daily_notify.sh` (example):
```bash
#!/usr/bin/env bash
set -e
# project root
cd /home/username/git-rep/xcell-proc
# load .env if present (export variables for the run)
if [ -f .env ]; then
  set -a
  . .env
  set +a
fi
# optional: prevent concurrent runs (requires flock)
exec 9>/var/lock/notify_vacations.lock
if ! flock -n 9; then
  echo "Another instance is running, exiting" >&2
  exit 0
fi
# activate venv and run
/home/username/.venv/bin/python src/cli_email_sender.py --test-recipient admin@example.com --subject "Авто-уведомления" --send >> logs/cron_notify.log 2>&1

```
- Make the script executable:
```bash
chmod 700 scripts/run_daily_notify.sh
```

Crontab entry to run at 02:00 (user crontab):
```
0 2 * * * /bin/bash -lc '/home/username/git-rep/xcell-proc/scripts/run_daily_notify.sh'
```
- Notes:
  - Use full absolute paths inside the wrapper.
  - `-lc` ensures login shell reads profile if needed.
  - Logs are appended to `logs/cron_notify.log` for review.

**8. Prevent overlapping executions**
- Use `flock` (shown above) or a pidfile. Example with `flock` in a one-liner for cron:
```
0 2 * * * /usr/bin/flock -n /var/lock/notify_vacations.lock /home/username/.venv/bin/python /home/username/git-rep/xcell-proc/src/cli_email_sender.py --test-recipient admin@example.com --send >> /home/username/git-rep/xcell-proc/logs/cron_notify.log 2>&1
```

**9. Rotating logs**
- Add a `logrotate` rule, e.g. `/etc/logrotate.d/xcell-proc`:
```
/home/username/git-rep/xcell-proc/logs/*.log {
  daily
  rotate 14
  copytruncate
  compress
  missingok
}
```

**10. Systemd timer alternative (modern Linux)**
- Create `~/.config/systemd/user/notify.service`:
```
[Unit]
Description=Run notify_vacations CLI

[Service]
Type=oneshot
WorkingDirectory=/home/username/git-rep/xcell-proc
ExecStart=/home/username/.venv/bin/python src/cli_email_sender.py --test-recipient admin@example.com --send
```
- And `~/.config/systemd/user/notify.timer`:
```
[Unit]
Description=Run notify service daily at 02:00

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```
- Enable and start the timer:
```bash
systemctl --user enable --now notify.timer
```

**11. Final checklist before enabling cron/systemd**
- Test the command manually with `--dry-run` and inspect `logs/email_previews`.
- Test a real send with a test account (MailHog or App Password) and confirm receipt.
- Restrict access to any stored `.env` or credential files and do not commit them.
- Configure log rotation and monitoring so failures are noticed.

**12. Quick troubleshooting**
- `535 BadCredentials` — fix credentials (App Password or correct login) or use local MailHog for dev.
- TLS/SSL errors — ensure correct `port` + `use_tls`/`use_ssl` combination.
- No outgoing connection — check firewall and provider restrictions.

If you want, I can:
- add `python-dotenv` to `requirements.txt` and load `.env` automatically in `src/cli_email_sender.py`,
- add the `scripts/run_daily_notify.sh` wrapper to the repo,
- provide `systemd` unit files adapted to your paths.


