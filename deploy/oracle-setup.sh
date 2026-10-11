#!/bin/bash
# Oracle Always Free Ubuntu VM용 오디오북 백엔드 설치 스크립트.
# 사용법: 이 파일을 VM에 복사 후 `bash deploy/oracle-setup.sh`
set -e

APP_DIR="$HOME/audiobook"
PORT="${PORT:-8000}"

echo "== 1/4 Docker 설치 =="
if ! command -v docker >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y docker.io git curl
  sudo systemctl enable --now docker
fi
docker --version

echo "== 2/4 방화벽 (Ubuntu UFW) =="
sudo ufw allow ${PORT}/tcp || true
sudo ufw allow 22/tcp || true

echo "== 3/4 이미지 빌드 =="
cd "$APP_DIR"
sudo docker build -t audiobook-api -f deploy/Dockerfile .

echo "== 4/4 컨테이너 실행 (재부팅 후 자동 시작) =="
sudo docker rm -f audiobook 2>/dev/null || true
sudo docker run -d --restart unless-stopped --name audiobook \
  -p ${PORT}:8000 \
  -e PORT=8000 \
  -e ALLOWED_ORIGINS="*" \
  audiobook-api

sleep 8
curl -s http://127.0.0.1:${PORT}/health && echo "" && echo "OK: 배포 완료"
echo "폰에서는 http://<VM공인IP>:${PORT} 로 접속"
