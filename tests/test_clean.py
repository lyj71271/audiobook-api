from core.clean import normalize, clean_for_tts


def test_normalize_crlf():
    assert normalize("a\r\nb\r\n") == "a\nb"


def test_clean_removes_url():
    out = clean_for_tts("참고 https://example.com 내용")
    assert "https://" not in out
    assert "링크" in out


def test_clean_empty():
    assert clean_for_tts("   ") == ""
