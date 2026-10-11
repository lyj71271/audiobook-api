# 오디오북 — 텍스트→오디오 변환 (Flutter + Python)

스킬: `.opencode/skills/text-to-audio/SKILL.md` 준수.
스택: Python 코어 + edge-tts/piper + ffmpeg + FastAPI + Flutter.

## 현재 환경 체크 결과 (2026-10-09)

- Python 3.8.4 — 동작은 하나 **3.10+ 권장** (piper, ebooklib 일부가 3.8에서 제한)
- ffmpeg 미설치 — `winget install ffmpeg` 필요
- flutter 미설치 — https://docs.flutter.dev/get-started/install/windows 필요

## 구조

```text
core/     # 텍스트 파싱·청킹 (UI 의존 없음)
tts/      # edge/piper 어댑터
audio/    # ffmpeg 래퍼, 메타데이터
backend/  # FastAPI localhost (Flutter 연동용)
app/      # Flutter UI (lib/main.dart 스켈레톤)
tests/    # pytest
assets/voices/ # piper 모델 저장 위치
```

## 빠른 시작 (Windows PowerShell)

```powershell
# 1. Python 3.10+ 설치 권장, 그 후:
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. ffmpeg 설치
winget install ffmpeg
ffmpeg -version

# 3. 테스트 (외부 의존 없이 통과 가능)
pytest -q

# 4. 백엔드 실행 (8000/8001은 타 프로젝트 사용 중 → 8002)
uvicorn backend.main:app --host 0.0.0.0 --port 8002

# 5. Flutter (별도 설치 후)
cd app
flutter pub get
flutter run
```

## 설정

`config.json` 참조. API 키는 코드에 넣지 말고 환경변수 사용.

## 언어 정책

- 현재: 전체 UI 한글 (`app/lib/main.dart`의 한글 문자열, 상태표 `_statusKo`).
- 앱 완성 후 영문판: `_statusKo` + UI 문자열을 `lib/l10n` 리소스로 분리 예정.
