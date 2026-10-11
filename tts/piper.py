"""piper-tts 어댑터 (2순위, 완전 오프라인)."""
import os

from .base import TTSAdapter


class PiperTTSAdapter(TTSAdapter):
    name = "piper"

    def __init__(self, model_path="assets/voices/ko_KR-xxx-medium.onnx"):
        self.model_path = model_path
        self.config_path = model_path + ".json"

    def is_available(self) -> bool:
        try:
            import piper  # noqa: F401
        except ImportError:
            return False
        return os.path.exists(self.model_path)

    async def synth(self, text: str, out_wav: str) -> str:
        from piper import PiperVoice
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                "piper 모델 없음: %s — config.json의 tts.piper_model 경로 확인" % self.model_path)
        voice = PiperVoice.load(self.model_path, config_path=self.config_path)
        voice.synthesize(text, wav_file=out_wav)
        if not os.path.exists(out_wav) or os.path.getsize(out_wav) == 0:
            raise ValueError("piper 합성 결과물이 비어 있음")
        return out_wav
