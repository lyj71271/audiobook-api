# Troubleshooting (겪었던 장애와 처방)

| 증상 | 원인 | 처방 |
|---|---|---|
| `합성 중...`에서 무한 대기 | 네트워크 단절 + 앱 타임아웃 없음 | 글자수 비례 타임아웃 적용됨. 서버 주소·Wi-Fi 확인 |
| `failed: list index out of range` | 한글 메타데이터 → ffmpeg stderr cp949 디코딩 붕괴 | `audio/concat.py` 바이트 수신+utf-8 디코딩으로 수정됨 |
| `failed` + 한글 제목 | 위와 동일 | 동일 수정으로 해결 |
| 8001번 요청이 엉뚱한 서버에 닿음 | `python -m http.server`가 같은 포트 점유 | 8002로 이전. 8000/8001 프로세스는 타 프로젝트라 손대지 말 것 |
| 앱 실행 먹통 (스플래시 정지) | `MainActivity`가 일반 FlutterActivity라 `AudioService.init` 예외 | `AudioServiceActivity` 상속으로 수정됨 |
| Android 빌드 `JVM 17+` 실패 | 시스템 Java 1.8 | `flutter config --jdk-dir` 내장 JBR로 고정됨 |
| Android 빌드 file_picker v1 임베딩 에러 | file_picker 6 구버전 | 13.1.0 + 신 API(`pickFiles`→`readAsBytes`)로 수정됨 |
| Kotlin 증분캐시 붕괴 (C:/D:) | 크로스 드라이브 소스 | `kotlin.incremental=false` (gradle.properties) |
| Windows 빌드 C4819 (한글 깨짐) | `main.cpp` BOM 없음 | UTF-8 BOM으로 저장됨 |
| `flutter analyze` 서버 충돌 | 한글 포함 프로젝트 경로 | 영문 경로(`audiobook`)로 이전, 세션 이동 |
| 에뮬레이터 System UI ANR | SwiftShader 저속 렌더링 | Wait 후 정상. 실사용은 실기기로 |
| 에뮬레이터 가속 없음 | AEHD 미설치 | sdkmanager로 설치 + 관리자 권한 실행됨 |
| 음성 끊김(찌어짐) | 청크 MP3 패딩 연결부 | 트리밍+PCM 통일 concat으로 수정됨. `stop_periods=-1`은 말소리 삭제하므로 사용 금지 |
| 릴리스에서 LAN 접속 차단 | 클리어텍스트 기본 차단 | `usesCleartextTraffic=true` 적용됨 |
| 서버 재시작 시 작업 소실 | 메모리 저장 | `jobs.json`+`singles.json` 영속화, `/resume` 추가됨 |

## 진단 순서 (새 장애 발생 시)

1. `curl.exe http://127.0.0.1:8002/health` — 백엔드 생존 확인
2. `netstat -ano | Select-String ':8002'` — 포트 점유 확인 (8000/8001은 제외)
3. 폰이면 `adb logcat`에서 `FATAL`·`AudioService` 검색
4. 위 표 대조 → 없으면 새로 기록 (이 파일에 추가)
