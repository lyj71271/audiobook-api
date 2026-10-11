# Network (LAN 백엔드 접속)

## 백엔드 실행

```powershell
# LAN 공개 (폰에서 접속 가능)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## PC LAN IP 확인

```powershell
ipconfig | Select-String 'IPv4'
# 예: 192.168.0.23
```

## 방화벽 허용 (관리자 PowerShell, 1회)

```powershell
netsh advfirewall firewall add rule name="Audiobook 8000" dir=in action=allow protocol=TCP localport=8000
```

삭제 시:

```powershell
netsh advfirewall firewall delete rule name="Audiobook 8000"
```

## 폰에서 확인

폰 브라우저 → `http://<PC-IP>:8000/health` → `{"ok":true}`.

실패 시 순서대로 점검:

1. 같은 Wi-Fi인가 (게스트 Wi-Fi/AP isolation이면 불가)
2. PC 방화벽 규칙 있는가
3. 포트 충돌인가 (`netstat -ano | Select-String 8000`, 8000번은 타 프로그램 점유 이력 있음 → `config.json` 포트 변경)

## Android 클리어텍스트 허용 (릴리스에서 http:// 접속 필수)

권장: 해당 IP만 허용하는 Network Security Config.

`android/app/src/main/res/xml/network_security_config.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <!-- PC LAN IP로 교체 -->
        <domain includeSubdomains="false">192.168.0.23</domain>
        <domain includeSubdomains="false">10.0.2.2</domain>
    </domain-config>
</network-security-config>
```

`AndroidManifest.xml`의 `<application>`에 추가:

```xml
android:networkSecurityConfig="@xml/network_security_config"
```

간편 대체 (개발용): `<application android:usesCleartextTraffic="true" ...>`.
배포 전에는 도메인 지정 방식으로 교체할 것.
