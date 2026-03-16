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
