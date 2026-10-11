"""edge-tts 어댑터 (1순위, 온라인 무료)."""
import asyncio
import time

from .base import TTSAdapter


class EdgeTTSAdapter(TTSAdapter):
    name = "edge"

    def __init__(self, voice="ko-KR-SunHiNeural", rate="+0%", pitch="+0Hz",
                 interval_ms=200, retry_max=3):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.interval_ms = interval_ms
        self.retry_max = retry_max

    def is_available(self) -> bool:
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            return False

    async def synth(self, text: str, out_wav: str) -> str:
        import edge_tts
        last_err = None
        for attempt in range(self.retry_max):
            try:
                comm = edge_tts.Communicate(text, voice=self.voice,
                                            rate=self.rate, pitch=self.pitch)
                await comm.save(out_wav)
                _validate_wav(out_wav)
                time.sleep(self.interval_ms / 1000.0)
                return out_wav
            except Exception as e:
                last_err = e
                time.sleep(1 * (2 ** attempt))  # 1s/2s/4s 백오프
        raise RuntimeError("edge-tts 실패(%d회): %s" % (self.retry_max, last_err))


def _validate_wav(path: str) -> None:
    import os
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        raise ValueError("합성 결과물이 비어 있음: %s" % path)
    try:
        import wave
        with wave.open(path, "rb") as w:
            frames = w.getnframes()
            framerate = w.getframerate() or 1
            if frames / float(framerate) < 0.5:
                raise ValueError("합성 오디오가 너무 짧음(<0.5s)")
    except ValueError:
        raise
    except Exception:
        # mp3로 저장된 경우 등은 크기 체크만으로 통과
        pass
