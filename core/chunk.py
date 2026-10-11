"""한국어 문장 경계 유지 청킹. 300~500자 권장, 기본 400자."""
import re
from typing import List

SENT_RE = re.compile(r"(?<=[.!?。？！…])\s+|\n{2,}")


def split_sentences(text: str) -> List[str]:
    return [s.strip() for s in SENT_RE.split(text) if s.strip()]


def chunk_text(text: str, target: int = 400, hard_max: int = 600) -> List[str]:
    sents = split_sentences(text)
    chunks = []
    cur = ""
    for s in sents:
        if len(s) > hard_max:
            # 초장문 강제 분할 (콤마/공백 우선, 없으면 고정 길이)
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.extend(_hard_split(s, target))
            continue
        if cur and len(cur) + len(s) + 1 > target:
            chunks.append(cur)
            cur = s
        else:
            cur = (cur + " " + s).strip() if cur else s
    if cur:
        chunks.append(cur)
    return chunks


def _hard_split(s: str, target: int) -> List[str]:
    # 콤마/공백 경계 우선 분할
    parts: List[str] = []
    start = 0
    while start < len(s):
        end = min(start + target, len(s))
        if end >= len(s):
            parts.append(s[start:].strip())
            break
        # 뒤에서 경계 탐색
        cut = max(s.rfind(",", start, end), s.rfind(" ", start, end))
        if cut <= start:
            cut = end
        else:
            cut += 1
        parts.append(s[start:cut].strip())
        start = cut
    return [p for p in parts if p]
