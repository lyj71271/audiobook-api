# Audio Post (ffmpeg)

## 사전 체크

```bash
ffmpeg -version
```

없으면 중단하고 안내: Win `winget install ffmpeg`, macOS `brew install ffmpeg`, Ubuntu `apt install ffmpeg`.

## 청크 → 챕터 → 최종

1. 청크 wav 검증: 크기>0, 길이≥1s (`ffprobe` 또는 `wave` 모듈).
2. 챕터 파일리스트 작성 (`ch1.txt`):
   ```text
   file 'ch1_000.wav'
   file 'ch1_001.wav'
   ```
3. 챕터 합치기:
   ```bash
   ffmpeg -f concat -safe 0 -i ch1.txt -c copy ch1.wav
   ```
4. 무음 삽입 (문단 0.3s, 챕터 0.8s):
   ```bash
   ffmpeg -i ch1.wav -af "apad=pad_dur=0.8" ch1_padded.wav
   ```
   짧은 무음은 concat 시 `silence_300ms.wav`를 리스트에 끼워 넣는 방식 권장.
5. 최종 인코딩:
   ```bash
   ffmpeg -i ch1.wav -codec:a libmp3lame -b:a 192k -metadata title="제목" -metadata artist="저자" out.mp3
   ```
6. 전체 챕터 → 완본:
   ```bash
   ffmpeg -f concat -safe 0 -i all.txt -codec:a libmp3lame -b:a 192k audiobook.mp3
   ```
7. m4b(챕터 마크, 선택):
   ```bash
   ffmpeg -i audiobook.mp3 -codec:a aac -b:a 128k -f mp4 audiobook.m4b
   ```

## 메타데이터 (mutagen)

```python
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB
audio = MP3("audiobook.mp3", ID3=ID3)
audio.tags.add(TIT2(encoding=3, text="제목"))
audio.tags.add(TPE1(encoding=3, text="저자"))
audio.save()
```

## 배속

- 원본 훼손 금지. 재생 시 `just_audio.setSpeed()` 또는 별도导出본에만 `atempo` 적용:
  ```bash
  ffmpeg -i in.mp3 -filter:a "atempo=1.5" out_1.5x.mp3
  ```
