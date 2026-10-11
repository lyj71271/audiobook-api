"""장문 변환 잡 매니저 — 업로드→추출→청킹→합성→합치기, 폴링용 상태 저장.

영속성: out/jobs.json에 레지스트리 저장. 서버 재시작 시 done 잡은
다운로드 가능하게 복원, 미완료 잡은 interrupted로 복원 후 /resume으로 재개.
(manifest.json + wav가 디스크에 남아 있어 이어하기 가능)
"""
import asyncio
import json
import os
import uuid
from collections import defaultdict
from typing import Dict

from core.clean import clean_for_tts
from core.chunk import chunk_text
from core.extract import extract_text, extract_chapters
from core.manifest import build_manifest
from audio.concat import concat_wavs, to_mp3

REGISTRY = "out/jobs.json"

JOBS: Dict[str, dict] = {}
# 재개용 파라미터 (API 응답에는 노출하지 않음)
PARAMS: Dict[str, dict] = {}


def _save_registry() -> None:
    try:
        os.makedirs("out", exist_ok=True)
        rec = {}
        for jid, job in JOBS.items():
            rec[jid] = {"job": job, "params": PARAMS.get(jid, {})}
        tmp = REGISTRY + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
        os.replace(tmp, REGISTRY)
    except Exception:
        pass  # 상태 저장 실패가 변환을 막지 않음


def _public(job: dict) -> dict:
    return {k: job.get(k) for k in
            ("id", "status", "progress", "total", "done", "out", "error", "title")}


def load_registry() -> None:
    """서버 부팅 시 복원. done+파일존재 → done 유지, 그 외 → interrupted."""
    try:
        with open(REGISTRY, "r", encoding="utf-8") as f:
            rec = json.load(f)
    except (OSError, ValueError):
        return
    for jid, entry in rec.items():
        job = entry.get("job", {})
        job["id"] = jid
        out = job.get("out", "")
        if job.get("status") == "done" and out and os.path.isfile(out):
            pass  # 다운로드 가능 유지
        elif job.get("status") not in ("done", "failed"):
            job["status"] = "interrupted"
            job["error"] = "서버 재시작으로 중단 — 재개 가능"
        JOBS[jid] = job
        if entry.get("params"):
            PARAMS[jid] = entry["params"]


def create_job() -> str:
    jid = uuid.uuid4().hex[:8]
    JOBS[jid] = {"id": jid, "status": "created", "progress": 0.0,
                 "total": 0, "done": 0, "out": "", "error": "", "title": ""}
    _save_registry()
    return jid


def get_job(jid: str) -> dict:
    if jid not in JOBS:
        raise KeyError("job 없음: %s" % jid)
    return _public(JOBS[jid])


def _update(jid: str, **kw) -> None:
    JOBS[jid].update(kw)
    _save_registry()


async def run_book_job(jid: str, src_path: str, out_dir: str,
                       title: str, artist: str, engines, cfg: dict,
                       quality: str = "standard"):
    from audio.concat import PRESET_BITRATE
    bitrate = PRESET_BITRATE.get(quality, PRESET_BITRATE["standard"])
    PARAMS[jid] = {"src_path": src_path, "out_dir": out_dir, "title": title,
                   "artist": artist, "quality": quality}
    job = JOBS[jid]
    try:
        _update(jid, status="extracting")
        ext = os.path.splitext(src_path)[1].lower()
        if ext == ".epub":
            raw_chapters = extract_chapters(src_path)
        else:
            raw_chapters = [extract_text(src_path)]
        chunks_by_ch = []
        for ch in raw_chapters:
            cleaned = clean_for_tts(ch)
            if cleaned.strip():
                chunks_by_ch.append(chunk_text(cleaned, cfg["chunk"]["target_chars"],
                                              cfg["chunk"]["hard_max"]))
        manifest = build_manifest(chunks_by_ch, out_dir)
        total = len(manifest)
        _update(jid, total=total, status="synthesizing")
        job = JOBS[jid]

        from tts.fallback import synth_all

        def _is_done(m):
            return (m["status"] == "done"
                    and os.path.exists(os.path.join(out_dir, m["file"])))

        done = sum(1 for m in manifest if _is_done(m))
        _update(jid, done=done, progress=done / max(total, 1))

        def _cb(m):
            job = JOBS[jid]
            job["done"] = job.get("done", 0) + 1
            job["progress"] = job["done"] / max(total, 1)
            with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            _save_registry()

        todo = [m for m in manifest if not _is_done(m)]
        max_c = cfg.get("tts", {}).get("max_concurrency", 4)
        await synth_all(todo, engines,
                        lambda m: os.path.join(out_dir, m["file"]),
                        max_concurrency=max_c, progress_cb=_cb)

        _update(jid, status="merging")
        by_ch = defaultdict(list)
        for m in manifest:
            by_ch[m["chapter"]].append(os.path.join(out_dir, m["file"]))
        for ch_no in sorted(by_ch):
            ch_wav = os.path.join(out_dir, "chapter_%02d.wav" % ch_no)
            concat_wavs(by_ch[ch_no], ch_wav)
            to_mp3(ch_wav, os.path.join(out_dir, "chapter_%02d.mp3" % ch_no),
                   bitrate, title, artist)
        full_wav = os.path.join(out_dir, "full.wav")
        concat_wavs([os.path.join(out_dir, "chapter_%02d.wav" % c) for c in sorted(by_ch)], full_wav)
        full_mp3 = os.path.join(out_dir, "%s.mp3" % title)
        to_mp3(full_wav, full_mp3, bitrate, title, artist)
        _update(jid, status="done", progress=1.0, out=full_mp3)
    except Exception as e:
        import traceback
        traceback.print_exc()
        _update(jid, status="failed", error=str(e))
