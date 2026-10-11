"""Flutter 연동용 로컬 API. core/tts/audio만 import (역의존 금지)."""
import asyncio
import json
import os

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from urllib.parse import quote
import uuid

from backend.jobs import JOBS, PARAMS, create_job, get_job, load_registry, run_book_job
from backend.jobs import _update as _update_job

from core.clean import clean_for_tts
from core.chunk import chunk_text
from core.manifest import build_manifest, load_manifest, pending
from tts.edge import EdgeTTSAdapter
from tts.piper import PiperTTSAdapter
from tts.fallback import synth_with_fallback
from audio.concat import PRESET_BITRATE, concat_wavs, to_mp3

app = FastAPI(title="Audiobook Local API")


SINGLES_REG = "out/singles.json"


def _save_singles() -> None:
    try:
        os.makedirs("out", exist_ok=True)
        tmp = SINGLES_REG + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(DONE_FILES, f, ensure_ascii=False, indent=2)
        os.replace(tmp, SINGLES_REG)
    except Exception:
        pass


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_registry()  # 중단된 잡 복원 (done→다운로드 가능, 미완료→interrupted)
    try:
        with open(SINGLES_REG, "r", encoding="utf-8") as f:
            for sid, path in json.load(f).items():
                if os.path.isfile(path):
                    DONE_FILES[sid] = path
    except (OSError, ValueError):
        pass
    yield


app.router.lifespan_context = lifespan

# 웹 배포용 CORS. ALLOWED_ORIGINS 환경변수로 조이기 (미설정 시 개발용 전체 허용).
# 예: ALLOWED_ORIGINS=https://app.example.com,https://foo.pages.dev
_allowed = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed,
    allow_methods=["*"],
    allow_headers=["*"],
)

with open("config.json", encoding="utf-8") as f:
    CFG = json.load(f)


class SynthReq(BaseModel):
    text: str
    voice: str = ""
    out: str = "out/single.mp3"
    quality: str = "standard"  # standard(96k) | high(192k)


class BookReq(BaseModel):
    chapters: list
    out_dir: str = "out/book"
    title: str = "audiobook"
    artist: str = ""
    quality: str = "standard"


def _bitrate(quality: str) -> str:
    return PRESET_BITRATE.get(quality, PRESET_BITRATE["standard"])


# /synth 단건 결과 레지스트리 (경로 탐색 방지: id로만 조회)
DONE_FILES: dict = {}


def _safe_out(path: str) -> str:
    base = os.path.abspath("out")
    full = os.path.abspath(path)
    if not (full == base or full.startswith(base + os.sep)):
        raise HTTPException(403, "허용되지 않은 경로")
    if not os.path.isfile(full):
        raise HTTPException(404, "파일 없음")
    return full


def _dl(path: str, filename: str) -> FileResponse:
    full = _safe_out(path)
    return FileResponse(full, media_type="audio/mpeg", headers={
        "Content-Disposition": "attachment; filename*=UTF-8''%s" % quote(filename)})


def _engines(voice: str = ""):
    t = CFG["tts"]
    return [
        EdgeTTSAdapter(voice=voice or t["edge_voice"], rate=t["edge_rate"],
                       pitch=t["edge_pitch"],
                       interval_ms=t["request_interval_ms"],
                       retry_max=t["retry_max"]),
        PiperTTSAdapter(model_path=t["piper_model"]),
    ]


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/voices")
def voices():
    return {"edge_default": CFG["tts"]["edge_voice"],
            "edge": ["ko-KR-SunHiNeural", "ko-KR-InJoonNeural"],
            "note": "piper 모델은 assets/voices/에 .onnx 배치 후 사용"}


SYNTH_MAX = 500000  # 단문 상한 (50만자). 그 이상은 장문 탭(백그라운드 잡) 권장
SYNTH_SINGLE_MAX = 2000  # 이하면 1회 호출, 초과면 청크 합성


@app.post("/synth")
async def synth(req: SynthReq):
    text = clean_for_tts(req.text)
    if not text:
        raise HTTPException(400, "빈 텍스트")
    if len(text) > SYNTH_MAX:
        raise HTTPException(400, "50만자를 초과했습니다 (%d자)" % len(text))
    os.makedirs(os.path.dirname(req.out) or ".", exist_ok=True)
    tmp = req.out + ".tmp.wav"
    engines = _engines()
    if req.voice and hasattr(engines[0], "voice"):
        engines[0].voice = req.voice
    if len(text) <= SYNTH_SINGLE_MAX:
        await synth_with_fallback(text, tmp, engines)
        to_mp3(tmp, req.out, bitrate=_bitrate(req.quality))
    else:
        # 장문: 청크 분할 → 병렬 합성 → 합치기
        import shutil
        from tts.fallback import synth_all
        tmpdir = req.out + ".chunks"
        os.makedirs(tmpdir, exist_ok=True)
        chunks = chunk_text(text, CFG["chunk"]["target_chars"],
                            CFG["chunk"]["hard_max"])
        items = [{"text": ch, "status": "pending",
                    "file": os.path.join(tmpdir, "%03d.wav" % i)}
                   for i, ch in enumerate(chunks)]
        max_c = CFG.get("tts", {}).get("max_concurrency", 4)
        await synth_all(items, engines, lambda m: m["file"],
                        max_concurrency=max_c)
        wavs = [m["file"] for m in items]
        concat_wavs(wavs, tmp)
        to_mp3(tmp, req.out, bitrate=_bitrate(req.quality))
        shutil.rmtree(tmpdir, ignore_errors=True)
        try:
            os.remove(tmp)
        except OSError:
            pass
    sid = uuid.uuid4().hex[:8]
    DONE_FILES[sid] = os.path.abspath(req.out)
    _save_singles()
    return {"out": req.out, "chars": len(text), "file_id": sid}


@app.post("/book")
async def book(req: BookReq):
    """챕터 리스트 → 청킹 → 합성 → 챕터 mp3 + 완본 mp3."""
    os.makedirs(req.out_dir, exist_ok=True)
    chunks_by_ch = []
    for ch in req.chapters:
        cleaned = clean_for_tts(ch)
        chunks_by_ch.append(chunk_text(cleaned, CFG["chunk"]["target_chars"],
                                       CFG["chunk"]["hard_max"]))
    manifest = build_manifest(chunks_by_ch, req.out_dir)
    engines = _engines()
    for m in pending(manifest):
        wav = os.path.join(req.out_dir, m["file"])
        await synth_with_fallback(m["text"], wav, engines)
        m["status"] = "done"
        with open(os.path.join(req.out_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    # 챕터별 합치기 + 최종 합치기
    from collections import defaultdict
    by_ch = defaultdict(list)
    for m in manifest:
        by_ch[m["chapter"]].append(os.path.join(req.out_dir, m["file"]))
    finals = []
    for ch_no in sorted(by_ch):
        ch_wav = os.path.join(req.out_dir, "chapter_%02d.wav" % ch_no)
        concat_wavs(by_ch[ch_no], ch_wav)
        ch_mp3 = os.path.join(req.out_dir, "chapter_%02d.mp3" % ch_no)
        to_mp3(ch_wav, ch_mp3, _bitrate(req.quality), req.title, req.artist)
        finals.append(ch_mp3.replace(".mp3", ".wav") if False else ch_wav)
    full_mp3 = os.path.join(req.out_dir, "%s.mp3" % req.title)
    concat_wavs([os.path.join(req.out_dir, "chapter_%02d.wav" % c) for c in sorted(by_ch)], 
                os.path.join(req.out_dir, "full.wav"))
    to_mp3(os.path.join(req.out_dir, "full.wav"), full_mp3, _bitrate(req.quality),
           req.title, req.artist)
    return {"out": full_mp3, "chunks": len(manifest)}


class SynthJobReq(BaseModel):
    text: str
    title: str = "단문합성"
    voice: str = ""
    quality: str = "standard"


def _start_text_job(text: str, title: str, artist: str, quality: str,
                    voice: str, bg: BackgroundTasks) -> str:
    """텍스트 직접 잡 시작 (/synth/job·내부 공용). 파일로 저장 후 파일 잡과 동일 처리."""
    jid = create_job()
    src_dir = os.path.join("out", "upload_%s" % jid)
    os.makedirs(src_dir, exist_ok=True)
    src_path = os.path.join(src_dir, "text.txt")
    with open(src_path, "w", encoding="utf-8") as f:
        f.write(text)
    out_dir = os.path.join("out", "book_%s" % jid)
    os.makedirs(out_dir, exist_ok=True)
    _update_job(jid, status="queued", title=title)
    bg.add_task(run_book_job, jid, src_path, out_dir, title,
                artist, _engines(voice), CFG, quality)
    return jid


@app.post("/synth/job")
async def synth_job(req: SynthJobReq, bg: BackgroundTasks):
    """긴 단문용 비동기 합성. 즉시 {"job_id"} 반환 → /jobs 폴링 → /download. (웹 필수)"""
    text = clean_for_tts(req.text)
    if not text:
        raise HTTPException(400, "빈 텍스트")
    if len(text) > SYNTH_MAX:
        raise HTTPException(400, "50만자를 초과했습니다 (%d자)" % len(text))
    return {"job_id": _start_text_job(text, req.title, "", req.quality, req.voice, bg)}


@app.post("/convert/file")
async def convert_file(bg: BackgroundTasks, file: UploadFile = File(...),
                       title: str = "audiobook", artist: str = "",
                       quality: str = "standard"):
    """txt/pdf/epub/docx 업로드 → 백그라운드 잡 시작. {"job_id": ...} 반환 후 /jobs/{id} 폴링."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".txt", ".md", ".pdf", ".epub", ".docx"):
        raise HTTPException(400, "지원 형식: txt/md/pdf/epub/docx")
    jid = create_job()
    src_dir = os.path.join("out", "upload_%s" % jid)
    os.makedirs(src_dir, exist_ok=True)
    src_path = os.path.join(src_dir, file.filename or ("upload%s" % ext))
    with open(src_path, "wb") as f:
        f.write(await file.read())
    out_dir = os.path.join("out", "book_%s" % jid)
    os.makedirs(out_dir, exist_ok=True)
    _update_job(jid, status="queued", title=title)
    bg.add_task(run_book_job, jid, src_path, out_dir,
                title or os.path.splitext(os.path.basename(src_path))[0],
                artist, _engines(), CFG, quality)
    return {"job_id": jid}


@app.get("/jobs/{jid}")
def job_status(jid: str):
    try:
        return get_job(jid)
    except KeyError:
        raise HTTPException(404, "job 없음")


@app.post("/jobs/{jid}/resume")
def resume_job(jid: str, bg: BackgroundTasks):
    """interrupted/failed 잡 재개 (manifest 기준으로 남은 청크만 합성)."""
    try:
        job = get_job(jid)
    except KeyError:
        raise HTTPException(404, "job 없음")
    if job.get("status") not in ("interrupted", "failed"):
        raise HTTPException(409, "재개 대상 아님: %s" % job.get("status"))
    if jid not in PARAMS:
        raise HTTPException(410, "재개 정보 없음 (원본 삭제됨)")
    p = PARAMS[jid]
    _update_job(jid, status="queued", error="", progress=job.get("progress", 0.0))
    bg.add_task(run_book_job, jid, p["src_path"], p["out_dir"],
                p["title"], p["artist"], _engines(), CFG, p.get("quality", "standard"))
    return {"job_id": jid, "resumed": True}


@app.get("/download/single/{sid}")
def download_single(sid: str):
    """/synth 단건 결과 다운로드. (/{jid}/{ch} 보다 먼저 등록해야 함)"""
    if sid not in DONE_FILES:
        raise HTTPException(404, "파일 없음 (서버 재시작 시 소실)")
    return _dl(DONE_FILES[sid], os.path.basename(DONE_FILES[sid]))


@app.get("/download/{jid}")
def download_full(jid: str):
    """완본 mp3 다운로드."""
    try:
        job = get_job(jid)
    except KeyError:
        raise HTTPException(404, "job 없음")
    if job.get("status") != "done":
        raise HTTPException(409, "아직 변환 중")
    title = job.get("title", jid) or jid
    return _dl(job["out"], "%s.mp3" % title)


@app.get("/download/{jid}/{ch}")
def download_chapter(jid: str, ch: int):
    """챕터별 mp3 다운로드."""
    try:
        job = get_job(jid)
    except KeyError:
        raise HTTPException(404, "job 없음")
    if job.get("status") != "done":
        raise HTTPException(409, "아직 변환 중")
    title = job.get("title", jid) or jid
    out_dir = os.path.dirname(job["out"])
    return _dl(os.path.join(out_dir, "chapter_%02d.mp3" % ch),
               "%s_%02d.mp3" % (title, ch))
