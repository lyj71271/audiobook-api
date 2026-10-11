---
name: Web Deploy
description: 오디오북 백엔드를 PC가 아닌 웹(클라우드)에 배포하는 작업용. Docker 패키징, 호스트 선정(Render/Railway/Fly/Oracle), HTTPS·CORS, 무료 티어 슬립 대응, Flutter 웹 빌드, 모바일 앱의 클라우드 접속 전환 포함. 클라우드 배포, Docker, HTTPS, CORS 관련 작업 시 사용.
---

# Web Deploy Skill

PC 상시 구동 없이 **클라우드에서 24시간 쓰는** 상태로 만드는 표준 워크플로우.
원칙: 긴 합성(수십 분)이 무료 티어의 슬립/타임아웃에 죽지 않게 설계한다.

## When to Use

- `uvicorn` PC 실행을 클라우드로 옮길 때, Dockerfile 작성, 호스트 선정 시
- 폰이 집 Wi-Fi 밖에서도 쓰게 할 때 (클라우드 URL은 어디서든 접속)
- `CORS`, `Mixed Content`, 슬립으로 잡이 중간에 죽는 문제 해결 시
- 키워드: `배포`, `Docker`, `Render`, `Fly.io`, `HTTPS`, `CORS`, `슬립`

## Workflow

순서대로 진행하고 각 단계 결과를 한 줄로 보고한다.

### 1. 전제 확인

- 로컬에서 `flutter analyze`·`flutter test`·백엔드 핵심 API 통과.
- `config.json`의 포트·비트레이트 등 운영값 확정.
- 사용자에게 1가지만 확인: **장문(수십 분짜리 합성)을 자주 쓰는지**. 자주 쓰면 2단계에서 상시 구동형(Oracle 등)을 고른다.

### 2. 호스트 선정

`references/options.md` 비교표로 선택. 기본 권장:

- **카드 없이 → Hugging Face Spaces.** 이메일 가입만으로 Docker 배포 + https 자동. 48시간 유휴 슬립(접속 시 기동), 장문은 폴링 유지 시 지속.
- **장문 상시 → Oracle Cloud Always Free (Ampere VM).** 카드 필요. 슬립 없음.
- 공통 주의: edge-tts는 외부망만 되면 됨 (키 불필요). piper 모델은 이미지 비대화 → 클라우드용 이미지에선 제외, edge 단일 엔진으로 간다.

### 3. 컨테이너 패키징

`references/docker.md` 준수:

1. 베이스: `python:3.11-slim` + `ffmpeg` apt 설치 (합치기·인코딩 필수).
2. `requirements.txt` 설치, `piper-tts`·모델 제외.
3. 실행: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` ($PORT 환경변수 필수 — 호스트가 주입).
4. 헬스체크: `GET /health`. 시작 프로브 실패 시 로그에서 import 에러 먼저 확인.
5. 결과물(`out/`)은 **휘발**로 간주: 완료 즉시 다운로드가 원칙. 영속 디스크는 유료/별도 설정이므로 기본 포함하지 않는다.

### 4. 백엔드 웹 대응 (코드 변경 3건)

1. **CORS 허용**: `CORSMiddleware` 추가 (Flutter 웹·외부 호출용). `allow_origins`는 배포 후 프론트 도메인으로 조인다. 와일드카드는 개발 단계까지만.
2. **잡 저장소**: `JOBS`·`DONE_FILES`가 메모리라 재시작/스케일 시 소실. 웹 배포에선 `out/manifest.json` 기반 재조회로 보완하거나, 최소한 "재시작 시 소실"을 다운로드 화면에 고지한다.
3. **타임아웃**: 호스트/프록시의 요청 제한(보통 30~120초) 안에 안 끝나는 API는 전부 백그라운드 잡+폴링으로. `/synth` 장문 경로(수 분~수십 분)는 잡 방식으로 전환 검토. 단문(수 초)은 동기 유지.

### 5. 프론트·앱 접속 전환

1. **모바일 앱**: 설정 탭에 `https://<배포도메인>` 입력하면 그대로 동작 (https라 클리어텍스트 문제 없음). 기본값은 그대로 LAN 유지, 클라우드는 사용자 입력.
2. **Flutter 웹** (`flutter build web`) 배포 시 개조 필요:
   - `path_provider` 앱 문서 폴더 → 브라우저 다운로드(AnchorElement) 방식으로 교체.
   - `audio_service` 미지원 → 웹에선 just_audio 직접 재생 + 백그라운드 불가 고지.
   - Mixed Content 금지: 프론트·API 모두 `https`.
3. 정적 호스팅: GitHub Pages/Netlify/Cloudflare Pages 중 택1.

### 6. 함정 (반드시 회피)

- 무료 티어에 장문 잡을 올리고 "왜 중간에 죽나" 반복. 슬립/타임아웃은 스펙이니 호스트 선정(2단계)으로 해결.
- `localhost`·`127.0.0.1`·`10.0.2.2`가 들어간 URL을 그대로 배포. 전부 환경/설정 주입으로.
- API 키·토큰을 이미지·코드에 포함. 전부 호스트의 환경변수(Secrets)로.
- `out/` 영속 가정. 무료 배포의 디스크는 재배포 시 초기화 — 완료 즉시 다운로드가 원칙.
- CORS 와일드카드(`*`)를 운영에 방치. 프론트 도메인 확정 후 조이기.

## Conventions

- 배포 관련 파일은 `deploy/`에 격리: `Dockerfile`, `render.yaml`/`fly.toml`, `.dockerignore`.
- 로컬 개발 포트(8001)와 운영 포트($PORT) 분리. 앱 기본값은 로컬 유지.
- 새 환경변수는 `.env.example`에 예시 추가, 실제 값은 절대 커밋 금지.

## References

- `references/options.md` — 호스트 비교표 (슬립/타임아웃/비용)
- `references/docker.md` — Dockerfile·헬스체크·빌드 명령
- `references/qa-web.md` — 배포 완료 조건 체크리스트
