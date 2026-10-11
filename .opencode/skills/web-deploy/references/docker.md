# Docker Packaging

## deploy/Dockerfile

```dockerfile
FROM python:3.11-slim

# ffmpeg (합치기·인코딩 필수)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# piper-tts·모델은 클라우드 이미지에서 제외 (edge 단일 엔진)
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ ./core/
COPY tts/ ./tts/
COPY audio/ ./audio/
COPY backend/ ./backend/
COPY config.json .

# 결과물은 휘발 (완료 즉시 다운로드 원칙)
VOLUME ["/app/out"]

EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

## deploy/.dockerignore

```text
out/
app/
.opencode/
__pycache__/
*.pyc
.env
```

## 빌드·실행 (로컬 검증)

```powershell
docker build -t audiobook-api -f deploy/Dockerfile .
docker run --rm -p 8001:8000 -e PORT=8000 audiobook-api
curl.exe http://127.0.0.1:8001/health
```

## 헬스체크 실패 시

1. `docker logs`에서 ModuleNotFound 먼저 확인 (COPY 누락이 1순위).
2. ffmpeg 확인: `docker run --rm audiobook-api ffmpeg -version`.
3. `$PORT` 미주입 호스트는 `PORT` 기본값(8000)으로 리슨 — 호스트 포트 매핑과 일치시킬 것.
