"""Typecast 어댑터 (유료 고품질, opt-in).

공식 REST: POST https://api.typecast.ai/v1/text-to-speech
헤더 X-API-KEY, body {text, voice_id, model: ssfm-v30, ...}.
표준 라이브러리만 사용 (추가 의존 없음).

요금 (2026-10 확인):
- Free $0: 월 15k자, 동시 2, 비상업+출처표시. 카드 불필요.
- Lite $15: 월 200k자. 1크레딧=1자.
사용법: TYPECAST_API_KEY 환경변수 + config tts.primary="typecast".
주의: 무료 할당량은 35분 분량이라 대량 테스트는 edge로 할 것.
"""
import json
import os
import time
import urllib.request

from .base import TTSAdapter

API_URL = "https://api.typecast.ai/v1/text-to-speech"


class TypecastAdapter(TTSAdapter):
    name = "typecast"

    def __init__(self, api_key: str = "", voice_id: str = "",
                 model: str = "ssfm-v31", emotion: str = "smart",
                 retry_max: int = 3):
        self.api_key = api_key or os.environ.get("TYPECAST_API_KEY", "")
        self.voice_id = voice_id
        self.model = model
        self.emotion = emotion
        self.retry_max = retry_max

    def is_available(self) -> bool:
        return bool(self.api_key and self.voice_id)

    def _request(self, text: str) -> bytes:
        payload = {
            "text": text,
            "voice_id": self.voice_id,
            "model": self.model,
            "prompt": {"emotion_type": self.emotion},
        }
        req = urllib.request.Request(
            API_URL, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "X-API-KEY": self.api_key})
        with urllib.request.urlopen(req, timeout=120) as r:
            if r.status != 200:
                raise RuntimeError("typecast HTTP %d" % r.status)
            return r.read()

    async def synth(self, text: str, out_wav: str) -> str:
        import asyncio
        loop = asyncio.get_event_loop()
        last_err = None
        for attempt in range(self.retry_max):
            try:
                data = await loop.run_in_executor(None, self._request, text)
                if len(data) < 1000:
                    raise ValueError("응답 오디오가 비어 있음 (%dB)" % len(data))
                with open(out_wav, "wb") as f:
                    f.write(data)
                return out_wav
            except Exception as e:
                last_err = e
                time.sleep(1 * (2 ** attempt))
        raise RuntimeError("typecast 실패(%d회): %s" % (self.retry_max, last_err))
