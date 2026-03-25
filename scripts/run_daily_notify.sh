#!/usr/bin/env bash
set -euo pipefail
# Ежедневный запуск уведомлений об отпусках через cron/systemd.
#
# Пайплайн: загрузка .env → парсинг Excel с отпусками → определение получателей →
#           отправка уведомлений сотрудникам (с копией руководителю и ФМ).
#
# Настройте пути ниже перед включением в cron:
#   crontab -e
#   0 8 * * * /bin/bash -lc '/path/to/run_daily_notify.sh'

# ── Настраиваемые пути ──────────────────────────────────────────────
PROJECT_ROOT="/home/username/git-rep/xcell-proc"
PYTHON_EXEC="$PROJECT_ROOT/.venv/bin/python"
CONFIG_FILE="$PROJECT_ROOT/config/config.json"
LOCK_FILE="/var/lock/notify_vacations.lock"
LOG_FILE="$PROJECT_ROOT/logs/cron_notify.log"
# ─────────────────────────────────────────────────────────────────────

cd "$PROJECT_ROOT"

# Загрузить переменные окружения из .env
if [ -f .env ]; then
  set -a
  . .env
  set +a
fi

mkdir -p "$(dirname "$LOG_FILE")"

# Защита от параллельных запусков через flock
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') Another instance is running; exiting" | tee -a "$LOG_FILE"
  exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') === Starting daily vacation notifications ===" | tee -a "$LOG_FILE"

"$PYTHON_EXEC" src/cli_notify.py \
  --config "$CONFIG_FILE" \
  --send \
  --preview-dir logs/email_previews \
  2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}
echo "$(date '+%Y-%m-%d %H:%M:%S') === Finished with exit code $EXIT_CODE ===" | tee -a "$LOG_FILE"
exit $EXIT_CODE
