"""ffmpeg 존재 확인 + 합치기/인코딩 래퍼."""
import os
import shutil
import subprocess


def check_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise FileNotFoundError(
            "ffmpeg을 찾지 못했습니다. Win: winget install ffmpeg / macOS: brew install ffmpeg")
    return path


def _run(cmd):
    # text=True 사용 금지: 한글 Windows(cp949)에서 ffmpeg stderr(UTF-8 한글 포함)
    # 디코딩이 깨지면 reader 스레드가 죽고 communicate()가 IndexError를 낸다.
    # 바이트로 받아 utf-8/replace로 디코딩한다.
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        err = r.stderr.decode("utf-8", errors="replace")
        raise RuntimeError("ffmpeg 실패: %s" % (err[-2000:]))
    return r


def _probe_duration(path: str) -> float:
    """ffprobe로 재생 길이(초). 실패 시 0.0."""
    import subprocess
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1", path],
            capture_output=True)
        return float(r.stdout.decode("utf-8", errors="replace").strip().split("=")[-1])
    except Exception:
        return 0.0


def _trim_to_pcm(src: str, dst: str, sample_rate: int = 24000) -> str:
    """청크 앞 무음 제거 + 뒤 MP3 패딩 절삭 + PCM 모노 통일.

    - 앞: silenceremove 시작 무음만 (정상 동작 확인됨).
    - 뒤: silenceremove의 stop 트리밍이 말소리까지 잘라먹어 고정 0.3s 절삭.
      (MP3 인코더 지연/패딩 ≈ 0.1s + 여유. 끝 무음 0.9s 중 일부가 남아
      자연스러운 호흡이 된다.)
    - PCM 통일로 concat copy가 샘플 단위 정확도로 붙어 뚝 소리 제거.
    """
    check_ffmpeg()
    dur = _probe_duration(src)
    tail = max(0.0, dur - 0.30) if dur > 0.4 else 0.0
    af = ("silenceremove=start_periods=1:start_duration=0.05:"
          "start_threshold=-45dB")
    if tail > 0:
        af += ",atrim=end=%.3f,asetpts=PTS-STARTPTS" % tail
    _run(["ffmpeg", "-y", "-i", src, "-af", af,
          "-ar", str(sample_rate), "-ac", "1", dst])
    return dst


def concat_wavs(wav_files, out_wav: str, list_path: str = "_concat.txt",
                trim: bool = True) -> str:
    """concat demuxer로 합치기. trim=True면 청크 트리밍+PCM 통일 후 copy."""
    check_ffmpeg()
    if trim and wav_files:
        work = os.path.splitext(out_wav)[0] + ".trim"
        os.makedirs(work, exist_ok=True)
        trimmed = []
        for i, w in enumerate(wav_files):
            trimmed.append(_trim_to_pcm(
                w, os.path.join(work, "%04d.wav" % i)))
        wav_files = trimmed
    with open(list_path, "w", encoding="utf-8") as f:
        for w in wav_files:
            # single-quote 이스케이프
            f.write("file '%s'\n" % w.replace("'", "'\\''"))
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", out_wav])
    return out_wav


# 음성(모노 TTS)용 프리셋. 음악용 192k는 과한 스펙이라 기본 96k.
# 음성에서는 96k와 192k의 체감 차이가 거의 없다.
PRESET_BITRATE = {"standard": "96k", "high": "192k"}


def to_mp3(in_wav: str, out_mp3: str, bitrate: str = "96k",
           title: str = "", artist: str = "") -> str:
    """확장자가 .opus/.ogg면 Opus(음성 최적, 동급 음질에 1/4 용량)로 인코딩."""
    check_ffmpeg()
    lower = out_mp3.lower()
    if lower.endswith((".opus", ".ogg")):
        if bitrate in ("96k", "192k", ""):
            bitrate = "48k"
        cmd = ["ffmpeg", "-y", "-i", in_wav, "-codec:a", "libopus",
               "-b:a", bitrate, "-vbr", "on"]
    else:
        cmd = ["ffmpeg", "-y", "-i", in_wav, "-codec:a", "libmp3lame",
               "-b:a", bitrate]
    if title:
        cmd += ["-metadata", "title=%s" % title]
    if artist:
        cmd += ["-metadata", "artist=%s" % artist]
    cmd.append(out_mp3)
    _run(cmd)
    return out_mp3


def make_silence(out_wav: str, ms: int = 300, sample_rate: int = 22050) -> str:
    """무음 wav 생성 (챕터/문단 경계용)."""
    check_ffmpeg()
    secs = ms / 1000.0
    _run(["ffmpeg", "-y", "-f", "lavfi", "-i",
          "anullsrc=r=%d:cl=mono" % sample_rate, "-t", str(secs), out_wav])
    return out_wav


def wav_duration(path: str) -> float:
    try:
        import wave
        with wave.open(path, "rb") as w:
            return w.getnframes() / float(w.getframerate() or 1)
    except Exception:
        return 0.0


def validate_wav(path: str, min_secs: float = 1.0) -> None:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        raise ValueError("오디오 파일이 비어 있음: %s" % path)
    d = wav_duration(path)
    if d and d < min_secs:
        raise ValueError("오디오가 너무 짧음(%.2fs): %s" % (d, path))
