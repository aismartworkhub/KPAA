#!/usr/bin/env bash
# 일일 백업 (cron 예: 30 2 * * * /opt/kpaa-ethics/scripts/backup.sh >> /var/log/kpaa-backup.log 2>&1)
# Docker 사용 시:  docker compose exec -T app python -m app.services.backup
set -euo pipefail
cd "$(dirname "$0")/../backend"
python3 -m app.services.backup
# 외부 보관(예시): rsync -a "${KPAA_BACKUP_DIR:-../data/backups}/" nas:/backup/kpaa-ethics/
