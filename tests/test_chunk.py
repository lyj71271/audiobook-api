from core.chunk import chunk_text


def test_chunk_keeps_sentences():
    text = "안녕하세요. 반갑습니다! 오늘은 좋은 날입니다. " * 30
    chunks = chunk_text(text, target=400, hard_max=600)
    assert len(chunks) >= 2
    assert all(len(c) <= 600 for c in chunks)


def test_chunk_long_sentence_split():
    text = "가" * 1000
    chunks = chunk_text(text, target=400, hard_max=600)
    assert len(chunks) >= 2


def test_chunk_empty():
    assert chunk_text("") == []
