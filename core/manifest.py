"""장문 변환 매니페스트 — 중단 후 재개용."""
import json
import os
from typing import Dict, List


def build_manifest(chunks_by_chapter: List[List[str]], out_dir: str) -> List[Dict]:
    manifest = []
    n = 0
    for ch_idx, chunks in enumerate(chunks_by_chapter, start=1):
        for idx, text in enumerate(chunks):
            n += 1
            manifest.append({
                "id": "c%03d" % n,
                "chapter": ch_idx,
                "index": idx,
                "chars": len(text),
                "text": text,
                "file": "ch%d_%03d.wav" % (ch_idx, idx),
                "status": "pending",
            })
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest


def load_manifest(out_dir: str) -> List[Dict]:
    with open(os.path.join(out_dir, "manifest.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def mark_done(out_dir: str, chunk_id: str, status: str = "done") -> None:
    manifest = load_manifest(out_dir)
    for m in manifest:
        if m["id"] == chunk_id:
            m["status"] = status
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def pending(manifest: List[Dict]) -> List[Dict]:
    return [m for m in manifest if m.get("status") != "done"]
