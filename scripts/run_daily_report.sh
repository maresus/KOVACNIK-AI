#!/bin/bash
# Daily smoke report wrapper — bere .env in požene daily_smoke_report.py
set -e

PROJECT="/Volumes/SSD KLJUC/KOVACNIK AI"
PYTHON="$PROJECT/.venv/bin/python3"
SCRIPT="$PROJECT/scripts/daily_smoke_report.py"
LOG="/tmp/kovacnik_smoke_report.log"

# Naloži .env (varno — podpira presledke in šumnike v vrednostih)
if [ -f "$PROJECT/.env" ]; then
  while IFS='=' read -r key value; do
    [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
    export "$key=$value"
  done < "$PROJECT/.env"
fi

# Smoke nastavitve
export SMOKE_BASE_URL="https://kovacnik-ai-production.up.railway.app/v3"
export SMOKE_EMAIL_TO="${DAILY_REPORT_EMAIL:-marko@creative-media.si}"
export SMOKE_EMAIL_MODE="always"
export SMOKE_QUESTIONS_PATH="$PROJECT/data/smoke_questions.txt"

cd "$PROJECT"
export PYTHONPATH="$PROJECT"
echo "--- $(date) ---" >> "$LOG"
"$PYTHON" "$SCRIPT" >> "$LOG" 2>&1
echo "Done: $?" >> "$LOG"
