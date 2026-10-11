"""TTS 어댑터 공통 인터페이스."""


class TTSAdapter:
    name = "base"

    def is_available(self) -> bool:
        return False

    async def synth(self, text: str, out_wav: str) -> str:
        raise NotImplementedError
