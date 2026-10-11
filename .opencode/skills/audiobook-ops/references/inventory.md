# Inventory (환경·버전·주소 총람, 2026-10-11)

## PC

- Windows 10 Pro 64비트, Python 3.8.4 (3.10+ 권장, piper 미사용 중)
- ffmpeg 9.0.2 (winget), edge-tts 7.2.8
- Flutter 3.47.7 (`C:\src\flutter`, 사용자 PATH 등록)
- VS Build Tools 2022 + C++ 워크로드, 개발자 모드 켬
- Android Studio + SDK 36 (`D:\Android\Sdk`), JDK=내장 JBR (`flutter config --jdk-dir`)
- Git 2.55 + gh 2.102 (PATH 반영된 새 셸에서 사용)

## 네트워크·주소

- PC LAN IP: `192.168.0.22` (DHCP — 바뀌면 `ipconfig`로 재확인)
- 백엔드: `0.0.0.0:8002` → PC `http://127.0.0.1:8002`, LAN `http://192.168.0.22:8002`
- 클라우드: `https://audiobook-api-fh3v.onrender.com` (Render Free, 15분 유휴 슬립)
- 방화벽: `Audiobook 8002` 허용. 8000/8001 점유 프로세스는 타 프로젝트 — 종료 금지
- GitHub: `lyj71271/audiobook-api` (master 브랜치)

## 앱

- 패키지명: `com.example.audiobook_app`, 표시명: 오디오북, 버전 0.2.0+2
- 서버 주소 저장 키: `SharedPreferences api_base`
  - 기본: Android `http://10.0.2.2:8002`, 그 외 `http://127.0.0.1:8002`
- 릴리스 APK: `app/build/app/outputs/flutter-apk/audiobookApp-release.apk` (약 51MB)
- 실기기 이력: Galaxy S10 (R3CN30RMP2H), Galaxy A33 (RFCT709T33L)

## 백엔드 API

- `GET /health` · `GET /voices`
- `POST /synth` (2000자 이하 동기, 5만자→50만자 상한)
- `POST /synth/job` (긴 글 비동기) · `POST /convert/file` · `POST /book`
- `GET /jobs/{id}` · `POST /jobs/{id}/resume`
- `GET /download/{id}` · `GET /download/{id}/{ch}` · `GET /download/single/{sid}`
- 상태 저장: `out/jobs.json` + `out/singles.json` (재시작 복원)

## 변환 성능 실측

- 단문 100자: 약 3초 / 2320자: 병렬 13초
- 5만자: 변환 2.5분, 재생 2시간 19분, 96k 기준 100MB
- 96k MP3는 음성에서 192k와 체감 차이 없음 (실측 비교 완료)
