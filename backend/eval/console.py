import sys


def setup_console() -> None:
    """Windows에서 출력이 파이프·파일로 갈 때 cp949 인코딩 오류로 중단되지 않게 UTF-8로 맞춘다."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
