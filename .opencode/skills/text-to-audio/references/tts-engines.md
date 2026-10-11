# TTS Engines (무료/로컬 우선)

## 1순위: edge-tts (온라인 무료)

```bash
pip install edge-tts
edge-tts --list-voices | findstr ko-KR
```

```python
import edge_tts
async def synth_edge(text: str, out: str, voice="ko-KR-SunHiNeural", rate="+0%", pitch="+0Hz"):
    tts = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
    await tts.save(out)
```

- 한국어 권장: `ko-KR-SunHiNeural` (여성), `ko-KR-InJoonNeural` (남성).
- 장문은 청크 병렬 합성 (`tts/fallback.py:synth_all`, 동시 `config.json`의 `tts.max_concurrency`=4).
  429가 반복되면 2까지 낮출 것. 요청 사이 200ms 간격은 유지.
- 실패 시 청크 단위 재시도 (엔진 내부 최대 3회, 지수 백오프 1s/2s/4s).

## 2순위: piper-tts (완전 오프라인)

```bash
pip install piper-tts
python -m piper.download_voices ko_KR --download-dir assets/voices
```

```python
from piper import PiperVoice
voice = PiperVoice.load("assets/voices/ko_KR-xxx-medium.onnx", config_path="assets/voices/ko_KR-xxx-medium.onnx.json")
voice.synthesize(text, wav_file="out.wav")
```

- 모델 경로를 `config.json`에 명시. 앱 첫 실행 시 모델 존재 체크 + 다운로드 안내.
- 품질은 edge보다 낮음 — 오프라인 모드/네트워크 실패 폴백용임을 UI에 고지.

## 3순위: espeak-ng (폴백/테스트)

- 품질 낮음. 합성 파이프라인 자체 테스트용으로만 사용.
- Windows: `espeak-ng` 바이너리 필요.

## 공통 인터페이스

```python
# tts/base.py
class TTSAdapter:
    name: str
    async def synth(self, text: str, out_wav: str) -> str: ...
    def is_available(self) -> bool: ...
```

- `edge.py`, `piper.py`가 동일 인터페이스 구현.
- 호출부:
  ```python
  for chunk in manifest:
      for engine in [edge, piper]:  # 순서 = 우선순위
          if engine.is_available():
              try: engine.synth(...); break
              except Exception as e: log(chunk.id, engine.name, e); continue
  ```
- 0바이트 또는 1초 미만 wav는 실패로 간주하고 다음 엔진으로 폴백.

## 유료 API (옵션, opt-in)

### Typecast (구현됨, `tts/typecast.py`)

- REST (`POST https://api.typecast.ai/v1/text-to-speech`, `X-API-KEY`), 600+ 보이스, 감정 자동.
- 요금 (2026-10 확인): Free 월 15k자(1크레딧=1자, 동시 2, 비상업+출처표시) / Lite $15 월 200k자.
- 유효화:
  ```powershell
  $env:TYPECAST_API_KEY="<키>"
  # config.json: tts.primary="typecast", tts.typecast.voice_id="<voice_id>"
  ```
- 주의: 무료 15k자는 약 35분 분량. 대량 테스트는 edge로, 본 변환만 typecast로.
- 키는 절대 커밋 금지: 환경변수 `TYPECAST_API_KEY`만 사용 (`.env.example` 참조).

### 기타 (OpenAI/ElevenLabs/Google)

- `tts/cloud_example.py` 스텁으로만 제공하고 기본 비활성화.
- 키는 절대 커밋 금지: `os.environ["TTS_API_KEY"]` + `.env.example`만 제공.
