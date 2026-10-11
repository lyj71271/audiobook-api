"""텍스트 정규화/클리닝. 원문은 절대 수정하지 않고 별도 문자열 반환."""
import re
import unicodedata

CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MULTI_BLANK_RE = re.compile(r"\n{3,}")
PAGE_NUM_RE = re.compile(r"^\s*\d+\s*$", re.MULTILINE)
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    text = CONTROL_RE.sub("", text)
    text = MULTI_BLANK_RE.sub("\n\n", text)
    return text.strip()


def clean_for_tts(text: str, remove_urls: bool = True) -> str:
    """TTS 발음용 클리닝."""
    text = normalize(text)
    if remove_urls:
        text = URL_RE.sub(" 링크 ", text)
    # 마크다운 기호 제거 (발음 방해)
    text = re.sub(r"(^|\n)#{1,6}\s*", r"\1", text)
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"[`*_>\[\]()]", "", text)
    # 과도한 공백 정리 (줄바꿈은 유지)
    lines = [" ".join(line.split()) for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_headers_footers(text: str) -> str:
    """페이지 번호 단독 행 제거 등 기본 정리."""
    text = PAGE_NUM_RE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
