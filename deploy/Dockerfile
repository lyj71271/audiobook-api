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
