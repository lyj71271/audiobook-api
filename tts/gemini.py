"""Gemini TTS 어댑터 (무료 티어, opt-in).

REST: POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
헤더 x-goog-api-key. 한국어 자동 감지, 스타일 지정 가능.
응답 inlineData(base64 PCM) → wav로 저장. 표준 라이브러리만 사용.

무료: AI Studio 키만 있으면 사용 (횟수 제한, 카드 불필요).
사용법: GEMINI_API_KEY 환경변수 + config tts.primary="gemini".
"""
import base64
import json
import os
import time
import urllib.request
import wave

from .base import TTSAdapter


class GeminiAdapter(TTSAdapter):
    name = "gemini"

    def __init__(self, api_key: str = "",
                 model: str = "gemini-2.5-flash-preview-tts",
                 voice: str = "Kore", style: str = "",
                 retry_max: int = 3):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model = model
        self.voice = voice
        self.style = style
        self.retry_max = retry_max

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _request(self, text: str) -> bytes:
        prompt = ("Say in a %s tone: %s" % (self.style, text)) if self.style else text
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": self.voice}
                    }
                },
            },
        }
        url = ("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"
               % self.model)
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "x-goog-api-key": self.api_key})
        with urllib.request.urlopen(req, timeout=180) as r:
            if r.status != 200:
                raise RuntimeError("gemini HTTP %d" % r.status)
            return r.read()

    @staticmethod
    def _save_wav(pcm: bytes, rate: int, out_wav: str) -> None:
        with wave.open(out_wav, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(pcm)

    @staticmethod
    def _parse_audio(resp: bytes):
        """(pcm_bytes, rate) 추출. 구조가 바뀌면 명확한 에러."""
        try:
            body = json.loads(resp.decode("utf-8"))
        except ValueError:
            raise RuntimeError("JSON이 아님: %s" % resp[:200])
        if "error" in body:
            raise RuntimeError("API 에러: %s" % body["error"])
        try:
            parts = body["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError):
            raise RuntimeError("parts 없음: %s" % str(body)[:300])
        for p in parts:
            inline = p.get("inlineData") or {}
            mime = inline.get("mimeType", "")
            if inline.get("data") and mime.startswith("audio/"):
                rate = 24000
                if "rate=" in mime:
                    try:
                        rate = int(mime.split("rate=")[1].split(";")[0])
                    except ValueError:
                        pass
                return base64.b64decode(inline["data"]), rate
        raise RuntimeError("오디오 데이터 없음: %s" % str(body)[:300])

    async def synth(self, text: str, out_wav: str) -> str:
        import asyncio
        loop = asyncio.get_event_loop()
        last_err = None
        for attempt in range(self.retry_max):
            try:
                resp = await loop.run_in_executor(None, self._request, text)
                pcm, rate = self._parse_audio(resp)
                if len(pcm) < 2000:
                    raise ValueError("오디오가 비어 있음 (%dB)" % len(pcm))
                await loop.run_in_executor(
                    None, self._save_wav, pcm, rate, out_wav)
                return out_wav
            except Exception as e:
                last_err = e
                time.sleep(1 * (2 ** attempt))
        raise RuntimeError("gemini 실패(%d회): %s" % (self.retry_max, last_err))
