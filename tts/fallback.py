"""우선순위 폴백: edge → piper 순으로 시도."""
import asyncio
import logging

logger = logging.getLogger(__name__)


async def synth_with_fallback(text: str, out_wav: str, engines) -> str:
    last_err = None
    for eng in engines:
        if not eng.is_available():
            logger.warning("[%s] 사용 불가 — 스킵", eng.name)
            continue
        try:
            return await eng.synth(text, out_wav)
        except Exception as e:
            logger.error("청크 실패 engine=%s err=%s", eng.name, e)
            last_err = e
            continue
    raise RuntimeError("모든 TTS 엔진 실패: %s" % last_err)


async def synth_all(items, engines, out_path_fn, max_concurrency: int = 4,
                    progress_cb=None):
    """여러 청크를 동시 합성 (세마포로 동시 수 제한).

    items: {"text": ...} dict 리스트. 성공한 item의 status를 "done"으로 바꾼다.
    순서는 바뀌어 끝날 수 있으나 manifest 저장은 콜백에서 즉시 처리하므로 안전.
    429 등 일시 실패는 eng.synth 내부 재시도가 흡수. 지속 실패 시
    max_concurrency를 2까지 낮출 것.
    """
    max_concurrency = max(1, int(max_concurrency or 1))
    sem = asyncio.Semaphore(max_concurrency)

    async def one(m):
        async with sem:
            await synth_with_fallback(m["text"], out_path_fn(m), engines)
            m["status"] = "done"
            if progress_cb is not None:
                progress_cb(m)
            return m

    return await asyncio.gather(*[one(m) for m in items])
