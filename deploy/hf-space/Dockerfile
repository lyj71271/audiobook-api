FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# piper-tts·모델 제외 (edge 단일 엔진)
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ ./core/
COPY tts/ ./tts/
COPY audio/ ./audio/
COPY backend/ ./backend/
COPY config.json .

EXPOSE 7860
# /data 영속 디스크가 있으면 out을 연결 (없으면 로컬 디스크 사용)
CMD ["sh", "-c", "mkdir -p /data/out && rm -rf /app/out && ln -s /data/out /app/out; uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
