from pathlib import Path

DEFAULT_PATH = Path(__file__).with_name("banned_words.txt")


def load_banned_words(path: Path | None = None) -> list[str]:
    lines = (path or DEFAULT_PATH).read_text(encoding="utf-8").splitlines()
    return [w.strip() for w in lines if w.strip()]


def find_banned(text: str, banned: list[str]) -> list[str]:
    return [w for w in banned if w in text]
