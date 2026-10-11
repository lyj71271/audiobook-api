# Text Processing

## 인코딩/정규화

1. `utf-8-sig`로 읽기, 실패 시 `chardet`/`charset-normalizer`로 감지.
2. `unicodedata.normalize('NFC', text)` — 한국어 자모 분리 방지.
3. `\r\n`→`\n`, `\t`→공백, 제어문자(`\x00-\x08`) 제거.
4. 3개 이상 연속 줄바꿈 → 2개로 축소. 원문 보존, 결과는 `cleaned.txt`.

## 포맷별 추출

- **txt/md**: 그대로 읽기. 마크다운 기호(`#`, `*`, `` ` ``, `[]()`)는 발음 방해 시 제거.
- **pdf** (`pypdf`):
  ```python
  from pypdf import PdfReader
  reader = PdfReader(path)
  text = "\n".join((p.extract_text() or "") for p in reader.pages)
  if len(text.strip()) < 100:
      raise ValueError("스캔본 PDF 의심 — OCR 필요")
  ```
  머리글/바닥글 반복 행, 페이지 번호 단독 행(`^\d+\s*$`) 제거.
- **epub** (`ebooklib`):
  ```python
  from ebooklib import epub
  from bs4 import BeautifulSoup
  book = epub.read_epub(path)
  chapters = []
  for item in book.get_items():
      if item.get_type() == 9:  # ITEM_DOCUMENT
          soup = BeautifulSoup(item.get_content(), "html.parser")
          chapters.append(soup.get_text("\n"))
  ```
  `spine` 순서 유지, 빈 챕터 제외.
- **docx** (`python-docx`): 문단(`paragraphs`) + 표(`tables`) 텍스트 결합, 빈 문단 2개 이상 압축.

## 한국어 청킹 (300~500자, 문장 경계 유지)

```python
import re
SENT_RE = re.compile(r'(?<=[.!?。？！…])\s+|\n{2,}')

def chunk_ko(text: str, target: int = 400, hard_max: int = 600) -> list[str]:
    sents = [s.strip() for s in SENT_RE.split(text) if s.strip()]
    chunks, cur = [], ""
    for s in sents:
        if len(s) > hard_max:  # 초장문 강제 분할 (콤마/공백 기준)
            if cur:
                chunks.append(cur); cur = ""
            for i in range(0, len(s), target):
                chunks.append(s[i:i+target])
            continue
        if len(cur) + len(s) + 1 > target and cur:
            chunks.append(cur); cur = s
        else:
            cur = (cur + " " + s).strip() if cur else s
    if cur:
        chunks.append(cur)
    return chunks
```

- 영어 혼합 시 약어(`Mr.`, `Dr.`, `e.g.`) 오분할 주의 — 필요 시 약어 사전으로 병합.
- URL·이메일·이모지는 발음 전 제거 또는 치환(`https://...`→"링크").
- 결과 매니페스트 예:
  ```json
  {"id": "c001", "chapter": 1, "index": 0, "chars": 387, "file": "ch1_000.wav", "status": "pending"}
  ```
