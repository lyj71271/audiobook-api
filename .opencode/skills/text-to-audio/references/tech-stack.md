# Tech Stack

## 기본 권장 (무료/로컬 우선 + 크로스플랫폼)

| 계층 | 선택 | 이유 | 대체 |
|---|---|---|---|
| 변환 코어 | Python 3.10+ | 텍스트/TTS/ffmpeg 생태계 최다 | Node 단독 (비권장, TTS lib 적음) |
| 온라인 TTS | `edge-tts` (pip) | 무료, 한국어 품질 우수, 키 불필요 | `gTTS` (차선, 차단 잦음) |
| 오프라인 TTS | `piper-tts` | 완전 로컬, 경량 onnx | `espeak-ng`, `Coqui XTTS` (무거움) |
| 오디오 처리 | `ffmpeg` + `pydub`/`mutagen` | 합치기·메타데이터 표준 | `sox` (보조) |
| 텍스트 추출 | `pypdf`, `ebooklib+bs4`, `python-docx` | 포맷별 표준 | `pdfplumber` (표 많은 PDF) |
| UI | Flutter **또는** Tauri | 크로스플랫폼 | 기존 코드 있으면 유지 |

## Flutter vs Tauri

- **Flutter**: 모바일(Android/iOS) 포함이면 선택. `just_audio` + `audio_service`로 백그라운드 재생. Python 코어는 `MethodChannel` 또는 로컬 REST(`FastAPI` localhost)로 연동.
- **Tauri**: 데스크톱(Win/macOS) + Web 중심이면 선택. 번들 경량, Python 코어를 사이드카(`tauri sidecar`)로 실행.
- Web만 먼저 검증하고 싶으면: Python `FastAPI` + 정적 프론트로 MVP 후 Flutter/Tauri 이식.

## 의존성 최소셋 (MVP)

```text
edge-tts
piper-tts (optional, offline)
pypdf
ebooklib
beautifulsoup4
python-docx
pydub
mutagen
ffmpeg (system binary, 필수)
pytest
```

## 금지/주의

- 유료 API를 기본값으로 하지 말 것. 설정에서 opt-in으로만 제공.
- `core/tts/audio`가 Flutter/Tauri를 import하지 않게 격리.
- ffmpeg는 코드에 동봉하지 말고 설치 체크 + 안내. Windows는 `winget install ffmpeg`, macOS는 `brew install ffmpeg`.
