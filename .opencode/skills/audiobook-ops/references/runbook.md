# Runbook (일상 운영 명령)

## 백엔드 켜기 (PC 재시작 후 매번)

```powershell
cd D:\MyProject\audiobook
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8002
curl.exe http://127.0.0.1:8002/health
# {"ok":true} 면 정상
```

## 백엔드 재시작 (코드 변경 후)

```powershell
$p = netstat -ano | Select-String ':8002' | Select-String 'LISTENING' | ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -Unique
$p | ForEach-Object { taskkill /PID $_ /F }
Start-Sleep -Seconds 2
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8002
```

주의: `:8002`로만 찾는다. `:8000`/`:8001`은 타 프로젝트라 절대 포함 금지.

## 앱 분석·테스트

```powershell
cd D:\MyProject\audiobook\app
flutter analyze
flutter test
```

## 릴리스 빌드 + 폰 설치

```powershell
cd D:\MyProject\audiobook\app
flutter build apk --release
Copy-Item 'build\app\outputs\flutter-apk\app-release.apk' 'build\app\outputs\flutter-apk\audiobookApp-release.apk' -Force
D:\Android\Sdk\platform-tools\adb.exe devices   # 폰 확인
D:\Android\Sdk\platform-tools\adb.exe -s <기기ID> install -r D:\MyProject\audiobook\app\build\app\outputs\flutter-apk\audiobookApp-release.apk
```

## 클라우드 반영 (Render 자동 재배포)

```powershell
cd D:\MyProject\audiobook
git add -A
git commit -m "내용"
git push
# Render 대시보드에서 빌드 → https://audiobook-api-fh3v.onrender.com/health 확인
```

## 로그 보기

- 백엔드: 실행한 터미널 그대로 (uvicorn 로그)
- 폰 앱: `adb -s <기기ID> logcat -d --pid=$(adb -s <기기ID> shell pidof com.example.audiobook_app)`
- 에뮬레이터 화면 캡처: `adb -s emulator-5554 shell screencap /sdcard/s.png` 후 `pull`
