# 설치·실행·배포 가이드

> 사건·민원 정보는 개인정보와 비공개 심의자료를 포함합니다. **사내망 서버에 설치하고 인터넷에 직접 노출하지 마세요.**
> 이 저장소(KPAA)는 Public이므로 GitHub Pages로는 정적 화면만 보이며 데이터·API는 동작하지 않습니다.

## A. 시연용 빠른 실행 (PC, 5분)
요구: Python 3.11 이상
```bash
cd ethics-system
./scripts/run_dev.sh          # 의존성 설치 + 가상 예시 데이터 + http://127.0.0.1:8000
```
최초 관리자 비밀번호는 `ethics-system/data/INITIAL_ADMIN_PASSWORD.txt` 에 생성됩니다(로그인 후 변경 강제, 파일 삭제).
Windows: `cd ethics-system\backend` → `pip install -r requirements.txt` → `python -m app.seed --demo` → `python -m uvicorn app.main:app --port 8000`

## B. 운영 설치 — Docker (권장)
```bash
cd ethics-system
cp .env.example .env            # KPAA_ADMIN_PASSWORD 등 입력
docker compose up -d --build
docker compose logs -f app      # 기동 확인
curl http://127.0.0.1:8000/api/health
```
- 데이터는 `ethics-system/data/` (DB·첨부·백업)에 저장됩니다.
- 앞단에 HTTPS 리버스 프록시를 두고 `.env`에 `KPAA_COOKIE_SECURE=1`.

Nginx 예시:
```nginx
server {
  listen 443 ssl; server_name ethics.kpaa.internal;
  ssl_certificate /etc/ssl/kpaa.crt; ssl_certificate_key /etc/ssl/kpaa.key;
  client_max_body_size 210m;          # 사례집 PDF 업로드
  location / { proxy_pass http://127.0.0.1:8000; proxy_set_header Host $host;
               proxy_set_header X-Forwarded-For $remote_addr; proxy_set_header X-Forwarded-Proto https;
               proxy_read_timeout 300s; }  # AI 분석 대기
}
```

## C. 운영 설치 — 리눅스 직접 설치(systemd)
```bash
sudo useradd --system kpaa
sudo mkdir -p /opt/kpaa-ethics && sudo cp -r ethics-system/* /opt/kpaa-ethics/ && sudo cp ethics-system/.env.example /opt/kpaa-ethics/.env
cd /opt/kpaa-ethics && sudo python3 -m venv venv && sudo venv/bin/pip install -r backend/requirements.txt
sudo chown -R kpaa /opt/kpaa-ethics
sudo cp scripts/kpaa-ethics.service /etc/systemd/system/ && sudo systemctl enable --now kpaa-ethics
```

## D. 백업·복구
- 화면: 관리 > 백업 > [지금 백업] / 내려받기
- 자동(매일 02:30): `30 2 * * * /opt/kpaa-ethics/scripts/backup.sh` (Docker: `docker compose exec -T app python -m app.services.backup`)
- 보존: 최근 30개(`KPAA_BACKUP_KEEP`). **NAS 등 별도 장소로 복사**하세요.
- 복구: 서비스 중지 → `data/kpaa_ethics.db` 를 백업 파일로 교체 → `uploads_*.tar.gz` 를 `data/`에 풀기 → 서비스 시작

## E. 사용자 조치가 필요한 항목 (시스템이 대신할 수 없음)
| 항목 | 해야 할 일 |
|---|---|
| 서버 | 사내 서버(또는 VM) 준비, 리버스 프록시·인증서 |
| AI 사용 | Anthropic Console에서 API 키 발급 → `.env`의 `ANTHROPIC_API_KEY`. 개인정보가 외부 API로 전송되므로 **내부 승인 후 사용**, 불필요 시 비워두기 |
| 메일 발송 | 회 메일 서버 SMTP 계정 → `.env` `KPAA_SMTP_*` (미설정 시 수동 발송 기록) |
| 기본 설정 | 관리 > 기본 설정: 담당 전화·메일, 결재선 → 공문 문의처·결재란 자동 기입 |
| 사용자 | 관리 > 사용자: 이대운·황예진 차장 등 계정 생성 |
| 징계사례집 | 대한변협 게시물에서 1~8집 PDF 다운로드 → 징계 선례·사례집 > 사례집 원문 업로드 |
| 규정 개정 | 규정·근거 매칭 > [개정 원문 반영]으로 HWP 업로드 |
