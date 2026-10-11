# Playback (다운로드 → 저장 → 재생)

## 백엔드: 파일 서빙

```python
from fastapi.responses import FileResponse
from urllib.parse import quote

@app.get("/download/{jid}")
def download(jid: str):
    job = get_job(jid)  # 상태 done 확인
    if job["status"] != "done":
        raise HTTPException(409, "아직 변환 중")
    path = job["out"]
    filename = "%s.mp3" % job.get("title", jid)
    return FileResponse(path, media_type="audio/mpeg",
                        filename=quote(filename))  # 한글 파일명
```

## 앱: 다운로드 (스트림 저장, 메모리 적재 금지)

```dart
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

Future<String> downloadMp3(String base, String jid, String title) async {
  final dir = await getApplicationDocumentsDirectory();
  final savePath = '${dir.path}/${jid}_$title.mp3';
  final req = http.Request('GET', Uri.parse('$base/download/$jid'));
  final resp = await http.Client().send(req);
  if (resp.statusCode != 200) throw Exception('다운로드 실패: ${resp.statusCode}');
  final file = File(savePath).openWrite();
  await resp.stream.pipe(file);  // 스트리밍 저장
  return savePath;
}
```

## 앱: 재생 (just_audio)

```dart
final player = AudioPlayer();
await player.setFilePath(savePath);
await player.play();
// 배속: player.setSpeed(1.5);
// 10초 점프: player.seek(player.position + const Duration(seconds: 10));
// 위치 저장: shared_preferences 'pos_$jobId' = position.inSeconds (주기적 저장)
// 복원: player.seek(Duration(seconds: saved));
```

## 보관함 연결

- `library` 항목에 로컬 경로 추가 저장: `$name|$jobId|$date|$localPath`.
- 이어듣기: 재생 시작 시 저장 위치로 `seek`, 재생 중 5초마다 위치 저장.
- 백그라운드 재생은 `audio_service`로 2차 단계에 분리 (MVP는 포그라운드 재생).
