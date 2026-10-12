#!/usr/bin/env bash
# 개발·시연용 실행: 가상 예시 데이터를 넣고 http://localhost:8000 에서 실행
set -euo pipefail
cd "$(dirname "$0")/../backend"
python3 -m pip install -q -r requirements.txt
python3 -m app.seed --demo
exec python3 -m uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8000}" --reload
