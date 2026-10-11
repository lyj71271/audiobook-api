---
name: Audiobook Ops
description: 오디오북 프로젝트 전용 운영 스킬. 지금까지 구축된 전체 구조(백엔드·앱·배포·환경)의 위치·포트·주소·실행법을 한곳에 정리. 일상 기동/재시작/재배포, 포트 충돌·먹통 등 장애 대응, 왕초보 가이드 작성 시 사용. 오디오북 운영, 재시작, 어디에 뭐가, 전체 구조 관련 작업 시 사용.
---

# Audiobook Ops Skill

이 프로젝트의 **현재 상태 그대로**를 다루는 운영 스킬.
일반론이 아니라 실제 경로·포트·명령을 그대로 쓴다.

## When to Use

- "백엔드 켜줘", "앱 다시 빌드해줘", "어디에 뭐가 있지" 같은 운영 요청
- 포트 충돌, 먹통, 재시작 후 복구 같은 장애 대응
- `GUIDE.md` (왕초보 가이드) 갱신 시
- 키워드: `운영`, `재시작`, `8002`, `배포 상태`, `전체 구조`

## System Map (2026-10-11 기준)

```text
D:\MyProject\audiobook\
├── backend/        # FastAPI (8002, LAN 공개)
├── core/ tts/ audio/  # 변환 파이프라인
├── app/            # Flutter (단문/장문/보관함/설정)
├── deploy/         # Dockerfile, render.yaml, oracle-setup.sh, hf-space/
├── out/            # 결과물 + jobs.json (git 제외)
├── config.json     # 포트 8002, 96k, 동시 4개
└── GUIDE.md        # 왕초보용 전체 설명서
```

| 항목 | 값 |
|---|---|
| PC 백엔드 | `http://192.168.0.22:8002` (LAN), `http://127.0.0.1:8002` (PC) |
| 클라우드 | `https://audiobook-api-fh3v.onrender.com` |
| GitHub | `lyj71271/audiobook-api` (master) |
| Flutter | `C:\src\flutter` (3.47.7) |
| Android SDK | `D:\Android\Sdk`, 에뮬레이터 `pixel` |
| APK | `app/build/app/outputs/flutter-apk/audiobookApp-release.apk` |
| 방화벽 | `Audiobook 8002` 인바운드 허용됨 |
| 점유 포트 (타 프로젝트) | 8000, 8001 — 건드리지 말 것 |

상세: `references/inventory.md`.

## Workflow

### 1. 기동 (PC 재시작 후)

```powershell
cd D:\MyProject\audiobook
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8002
curl.exe http://127.0.0.1:8002/health   # {"ok":true} 확인
```

상세: `references/runbook.md`.

### 2. 재배포·재빌드

- 백엔드 코드 변경 → 위 기동 명령으로 재시작 (구 프로세스 taskkill 후).
- 앱 변경 → `cd app`, `flutter analyze` → `flutter build apk --release` → 복사본 `audiobookApp-release.apk` → 폰에 `adb install -r`.
- 클라우드 반영 → `git add -A && git commit && git push` (Render 자동 재배포).

### 3. 장애 대응

`references/troubleshooting.md`의 증상별 표를 그대로 따른다.
원칙: 로그·포트·프로세스 3点 확인 후 조치. 절대 추측으로 재시작 반복 금지.

## Conventions

- 포트는 8002 고정. 8000/8001 점유 프로세스는 절대 죽이지 않는다 (타 프로젝트).
- `_concat.txt` 같은 루트 임시파일은 만들지 않는다 (이미 정리됨).
- repro_*.py 일회성 스크립트는 검증 후 즉시 삭제한다.
- 문서와 코드가 어긋나면 코드를 고치고 `GUIDE.md`·스킬도 함께 갱신한다.

## References

- `references/inventory.md` — 환경·버전·주소·파일 위치 총람
- `references/runbook.md` — 기동/재시작/빌드/배포 명령 모음
- `references/troubleshooting.md` — 겪었던 장애 10건과 처방
