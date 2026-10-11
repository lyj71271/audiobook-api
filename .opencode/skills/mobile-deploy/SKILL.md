---
name: Mobile Deploy
description: Flutter 오디오북 앱을 실제 모바일 기기에서 쓸 수 있게 만드는 작업용. 릴리스 APK 빌드·실기기 설치, LAN 백엔드 접속(런타임 서버 주소), 결과 MP3 다운로드·재생, 권한·클리어텍스트 대응 포함. 실기기, APK, 모바일 재생, LAN 접속 관련 작업 시 사용.
---

# Mobile Deploy Skill

디버그/에뮬레이터를 넘어 **실제 폰에서 쓰는** 상태로 만드는 표준 워크플로우.
원칙: 서버 주소는 컴파일 타임이 아닌 **런타임 설정**, 결과물은 기기에서 **다운로드+재생**까지.

## When to Use

- 실기기 설치, 릴리스 APK 빌드, 기기 연결(USB/무선 adb) 작업 시
- `API_BASE` 고정, LAN 접속 불가, MP3 다운로드/재생 미구현 등 모바일 실사용 차단 이슈
- 키워드: `릴리스 APK`, `실기기`, `adb`, `LAN`, `10.0.2.2`, `클리어텍스트`, `다운로드 재생`

## Workflow

순서대로 진행하고 각 단계 결과를 한 줄로 보고한다.

### 1. 전제 확인

- `flutter doctor` 전체 통과, `flutter analyze`·`flutter test` 통과.
- 백엔드가 PC에서 정상 동작 (`GET /health`).
- 폰과 PC가 **같은 Wi-Fi**에 있는지 확인. 다르면 2단계부터 막히므로 먼저 고지.

### 2. 백엔드 LAN 공개

1. 바인드 변경: `127.0.0.1` → `0.0.0.0` (포트 8000).
   - 주의: 이 PC의 8000번은 타 프로그램도 점유 중. 충돌 시 `config.json` 포트를 8001 등으로 변경.
2. PC의 LAN IP 확인: `ipconfig` → `IPv4 주소` (예: `192.168.0.23`).
3. Windows 방화벽 인바운드 허용 (관리자 1회): `netsh advfirewall firewall add rule ...` 또는 설정 UI.
4. 폰 브라우저에서 `http://<PC-IP>:8000/health` 접속 확인. 안 되면 여기서 멈추고 네트워크를 먼저 해결.

### 3. 앱 네트워크 대응

`references/network.md` 준수. 핵심 3건:

1. **런타임 서버 주소**: `String.fromEnvironment` 고정 금지. 설정 화면에서 입력 → `SharedPreferences` 저장 → 앱 재시작 없이 즉시 반영. 기본값은 플랫폼별 (`kIsWeb`/Windows=`127.0.0.1`, Android=`10.0.2.2`).
2. **클리어텍스트 허용**: 릴리스에서 LAN `http://` 접속은 기본 차단. `android:usesCleartextTraffic="true"` 또는 Network Security Config로 해당 IP만 허용 (후자 권장, `references/network.md` 참조).
3. **권한**: `INTERNET` 필수 선언 (릴리스에선 자동 부여 안 됨). 저장소 쓰기는 `path_provider` 앱 전용 디렉토리 사용으로 권한 없이 해결.

### 4. 결과 다운로드·재생 (실사용 핵심)

현재 앱은 "변환 요청"까지만 되므로, 기기에서 듣는 흐름을 완성한다:

1. 백엔드: `GET /download/{job_id}` (완본 mp3) + `GET /download/{job_id}/{chapter}` (챕터별) 추가. `FileResponse` + 한글 파일명 `Content-Disposition` UTF-8 처리.
2. 앱: `http`로 다운로드 → `path_provider` 앱 문서 폴더 저장 → `just_audio`로 재생.
3. 보관함과 연결: 다운로드된 파일 경로를 `SharedPreferences`에 저장, 이어듣기 위치(`pos_<jobId>`)와 함께 복원.
4. 플레이어 화면: 재생/일시정지, 10초 앞뒤 점프, 배속(0.8x~2.0x), 진행률 바. `audio_service` 백그라운드 연동은 2차로 분리.

### 5. 릴리스 빌드·설치

1. 버전 부여: `pubspec.yaml` `version: x.y.z+n` (빌드넘버 증가 필수).
2. 빌드: `flutter build apk --release` (용량 확인, `build/app/outputs/flutter-apk/app-release.apk`).
3. 설치 방법 택1:
   - USB: `adb install -r app-release.apk` (폰에서 USB 디버깅 허용)
   - 무선: `adb pair` + `adb connect` 후 동일
   - 파일 전송: APK를 폰에 복사 후 탭하여 설치 (출처 불명 허용 필요)
4. 설치 후 체크: `references/qa-mobile.md` — 서버주소 설정→단문 합성→장문 변환→다운로드→재생→이어듣기.

### 6. 함정 (반드시 회피)

- `localhost`를 실기기 주소로 사용 (에뮬레이터 전용 `10.0.2.2`도 실기기에서 불가). 실기기는 **PC의 LAN IP**만 된다.
- 컴파일 타임 `--dart-define`로 서버 주소 고정 후 "폰에서 안 돼요" 반복. 런타임 설정이 정답.
- 릴리스에서 `INTERNET` 미선언 → 화이트리스트 없이 무조건 통신 실패. 디버그에선 되는데 릴리스에서 안 되면 1순위 용의자.
- `http://` + Android 9+ → 클리어텍스트 차단. `https`로 우회 불가(LAN엔 인증서 없음)하므로 예외 설정이 정답.
- 대용량 MP3를 메모리에 통째로 (`readAsBytes`) — 다운로드는 스트림 저장, 재생은 파일 경로로.

## Conventions

- 서버 주소 키: `SharedPreferences` `api_base`, 설정 화면에서 변경 시 즉시 전역 반영 (InheritedWidget/Provider 없이 `ValueNotifier` 1개로 충분).
- 다운로드 파일명: `{jobId}_{title}.mp3` (한글 포함 가능, `Uri.encodeComponent`로 요청).
- 새 엔드포인트는 기존 `/synth`, `/convert/file`, `/jobs/{id}`와 같은 FastAPI 라우터에 추가, `core/tts/audio` 의존 방향 유지 (역의존 금지).

## References

- `references/network.md` — LAN 공개, 방화벽, 클리어텍스트 설정 예시
- `references/playback.md` — 다운로드→저장→재생 구현 패턴 (just_audio)
- `references/qa-mobile.md` — 실기기 완료 조건 체크리스트
