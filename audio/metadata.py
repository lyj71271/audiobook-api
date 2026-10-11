"""MP3 메타데이터 주입 (mutagen)."""
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB


def tag_mp3(path: str, title: str = "", artist: str = "", album: str = "") -> str:
    audio = MP3(path, ID3=ID3)
    try:
        audio.add_tags()
    except Exception:
        pass
    if title:
        audio.tags.add(TIT2(encoding=3, text=title))
    if artist:
        audio.tags.add(TPE1(encoding=3, text=artist))
    if album:
        audio.tags.add(TALB(encoding=3, text=album))
    audio.save()
    return path
