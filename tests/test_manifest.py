from core.manifest import build_manifest, pending


def test_manifest_build(tmp_path):
    chunks = [["a. " * 50], ["b. " * 50, "c. " * 10]]
    m = build_manifest(chunks, str(tmp_path))
    assert len(m) == 3
    assert m[0]["chapter"] == 1
    assert m[2]["chapter"] == 2
    assert len(pending(m)) == 3
