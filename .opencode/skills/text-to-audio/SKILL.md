---
name: Text to Audio
description: 텍스트→오디오 변환 크로스플랫폼 앱 개발용. 무료/로컬 TTS 우선, 단문 즉시변환+장문 오디오북(챕터 분할·합치기) 지원, 텍스트 전처리·청킹·MP3 후처리·재생 워크플로우 제공. TTS, 오디오북, 음성합성 관련 작업 시 사용.
---

# Text to Audio Skill

크로스플랫폼(Windows/macOS/Android/iOS/Web) 텍스트→오디오 변환 앱을 만들 때 따르는 표준 워크플로우.
유료 클라우드 API 없이 **무료/로컬 우선**, **단문+장문 겸용**을 기본값으로 한다.

## When to Use

- 새 TTS/오디오북 앱, 기능 추가, 버그 수정 시
- 입력 파싱(txt/pdf/epub/docx), TTS 연동, MP3 합치기, 재생 UI 작업 시
- 키워드: `TTS`, `edge-tts`, `piper`, `오디오북`, `음성합성`, `챕터 분할`

## Workflow

반드시 순서대로 진행하고, 각 단계 결과를 사용자에게 한 줄로 보고한다.

### 1. 요구사항 확정

- 입력 형식 확인: `txt` 필수, `pdf/epub/docx` 중 지원 범위 확정. `references/text-processing.md` 참조.
- 출력 형식 확인: 기본 `mp3` (호환성), 원본 보존용 `wav` 옵션.
- 단문(즉시 재생/저장) vs 장문(큐·백그라운드·챕터) 중 해당 범위 확인. 기본은 둘 다.
- 언어 확인: 기본 `ko` + `en`. 한국어 문장 분할 규칙 적용 여부 결정.

### 2. 스택 선정

`references/tech-stack.md`의 결정표대로 선택. 기본 권장:

- **코어 변환 파이프라인: Python + `edge-tts` (온라인 무료 고품질) + `piper-tts` (완전 오프라인) 이중 지원**
- **오디오 후처리: `ffmpeg` (합치기, 메타데이터, 배속)**
- **크로스플랫폼 UI: Flutter 또는 Tauri(Electron 대체 경량) 중 택1** — 기존 코드 있으면 그것을 유지.
- 네이티브 백그라운드 재생이 필요하면 Flutter `just_audio` / `audio_service`, Tauri면 OS 미디어키 연동.

금지: 유료 API(OpenAI/ElevenLabs/Google Cloud)를 기본값으로 채택하지 말 것. 옵션으로만 제공한다.

### 3. 텍스트 파이프라인 구축

1. 인코딩 정규화: `utf-8-sig` 읽기 → `NFC` 정규화 → `\r\n`→`\n`, 제어문자 제거.
2. 포맷별 추출:
   - pdf → `pypdf` 또는 `pdfplumber` (스캔본이면 OCR 필요함을 명시하고 중단)
   - epub → `ebooklib` + BeautifulSoup, 챕터(`spine`) 단위 분리
   - docx → `python-docx`, 문단 유지
3. 클리닝: 머리글/바닥글·페이지번호·URL·과도한 공백 제거. 원문은 절대 덮어쓰지 않고 `cleaned.txt` 별도 저장.
4. 청킹: **문장 경계 유지, 청크당 300~500자(한국어 기준 400자 권장)**. 마침표 `.!?。` + `…` + 줄바꿈 기준 분리 후 병합. `references/text-processing.md`의 분할 알고리즘 사용.
5. 각 청크에 `id, chapter, index, char_count` 메타 부여, JSON 매니페스트(`manifest.json`) 생성.

### 4. TTS 엔진 연동

`references/tts-engines.md` 우선순위 준수:

1. `edge-tts` — 기본. 한국어 음성 `ko-KR-SunHiNeural` / `ko-KR-InJoonNeural`, `rate/pitch` 옵션 노출.
2. `piper-tts` — 오프라인 폴백. 한국어 모델(`ko_KR` 계열) 다운로드 경로를 설정에 명시.
3. `espeak-ng` — 최후 폴백/테스트용 (품질 낮음 고지).

규칙:

- 청크 단위 순차 합성 → 실패한 청크만 재시도(최대 3회, 지수 백오프).
- 요청 사이 최소 200ms 간격(edge-tts 레이트리밋 회피).
- 합성 즉시 `wav`로 저장 후 검증(0바이트·1초 미만 파일은 실패 처리).
- API 키가 필요한 엔진은 `config.json` + 환경변수로 분리, 코드에 하드코딩 금지.

### 5. 오디오 후처리

`references/audio-post.md` 준수:

- 포맷: 청크 `wav` → 챕터별 concat → 최종 `mp3 (192k)` + 선택 `m4b(챕터 마크 포함)`.
- concat은 `ffmpeg concat demuxer` 사용, 재인코딩 최소화.
- 무음 삽입: 문단 경계 300ms, 챕터 경계 800ms.
- 메타데이터: 제목/저자/챕터/커버를 `mutagen` 또는 `ffmpeg -metadata`로 주입.
- 배속(0.8x~2.0x)은 원본이 아닌 재생 시점 또는 별도导出본에만 적용.

### 6. 크로스플랫폼 UI/재생

- 단문 화면: 텍스트 입력 → 즉시 합성 → 파형/진행률 + 재생/일시정지/저장.
- 장문 화면: 파일 가져오기 → 챕터 목록 → 일괄 변환 큐(진행률·남은시간·실패재시도) → 라이브러리(이어듣기 위치 저장).
- 파일 접근: 모바일 권한(`READ_MEDIA_AUDIO`, 저장소) 분기, 데스크톱은 임의 경로 허용.
- 백그라운드 재생: 모바일은 반드시 백그라운드 서비스 + 잠금화면 컨트롤, 데스크톱은 최소화 시 계속 재생.
- 설정: TTS 엔진 선택(edge/piper), 음성, 속도, 출력 폴더, 오프라인 모드 토글.

### 7. 테스트/QA

`references/qa-checklist.md`를 모두 통과해야 완료:

- 빈 입력, 1글자, 10만자 장문, 특수문자/이모지 혼합 케이스.
- 네트워크 끊김 시 piper 폴백 동작 확인.
- Windows/macOS/Android/iOS 중 타깃 2종 이상에서 재생·저장 확인.
- `ffmpeg` 미설치 시 명확한 에러 메시지 출력.

## Conventions

- 프로젝트 구조:
  ```text
  core/        # 텍스트 파싱·청킹·매니페스트 (순수 Python, UI 의존 금지)
  tts/         # 엔진 어댑터 (base.py + edge.py + piper.py, 동일 인터페이스)
  audio/       # concat·metadata·convert (ffmpeg 래퍼)
  app/         # Flutter/Tauri UI (core/tts/audio를 import만)
  tests/       # 청킹·합성·후처리 단위테스트
  assets/voices/ # piper 모델 (.onnx + .json)
  ```
- `core/tts/audio`는 UI 프레임워크를 import하지 않는다. 역방향 의존 금지.
- 모든 장문 변환은 `manifest.json` + 중간 `wav`를 남겨 재개 가능하게 한다.
- 로깅: 청크 실패는 `chunk_id + engine + error` 필수 기록.

## Pitfalls (자주 틀리는 점)

- CJK 문자 기준 `len(text)` 그대로 청크 자르기 → 문장 중간 절단. 반드시 문장 경계 우선.
- edge-tts를 병렬로 과도 호출 → 429/차단. 순차 + 간격 유지.
- pdf를 무조건 텍스트로 취급 → 스캔본은 OCR 안내 없이 빈 오디오 생성. 사전에 텍스트 추출량 검증.
- `ffmpeg`를 가정하고 배포 → 미설치 환경 크래시. 시작 시 `ffmpeg -version` 체크 + 설치 안내.
- 모바일 백그라운드 재생 미구현 → 화면 꺼지면 중단. 처음부터 `audio_service` 계열로 설계.

## References

- `references/tech-stack.md` — 스택 결정표, Flutter vs Tauri 비교
- `references/text-processing.md` — 포맷별 추출 + 한국어 청킹 알고리즘
- `references/tts-engines.md` — edge-tts / piper 설정, 음성표, 폴백 전략
- `references/audio-post.md` — ffmpeg 합치기·무음·메타데이터 명령
- `references/qa-checklist.md` — 완료 조건 체크리스트
