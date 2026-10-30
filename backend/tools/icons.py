"""앱 아이콘(홈 화면에 설치할 때 보이는 그림)을 만든다. 캐릭터 그림 하나를 따뜻한 배경 위에 얹는다.

    uv run --group assets python -m tools.icons
"""
from pathlib import Path

from PIL import Image

from app.config import REPO_ROOT

SOURCE = REPO_ROOT / "frontend" / "public" / "img" / "rabbit.webp"
OUT_DIR = REPO_ROOT / "frontend" / "public"
BACKGROUND = (255, 226, 204)  # 앱의 --accent-soft
# 안드로이드는 아이콘을 원·둥근 사각형으로 잘라내므로, 그림을 가운데 70% 안에 둔다
SIZES = {"icon-192.png": 192, "icon-512.png": 512, "apple-touch-icon.png": 180}


def make_icons(src: Path, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    with Image.open(src) as art:
        art = art.convert("RGBA")
        for name, size in SIZES.items():
            icon = Image.new("RGB", (size, size), BACKGROUND)  # 투명 없이 채움(아이폰은 투명을 검게 칠함)
            fit = art.copy()
            fit.thumbnail((int(size * 0.7), int(size * 0.7)), Image.LANCZOS)
            icon.paste(fit, ((size - fit.width) // 2, (size - fit.height) // 2), fit)
            path = out_dir / name
            icon.save(path)
            paths.append(path)
    return paths


if __name__ == "__main__":
    for p in make_icons(SOURCE, OUT_DIR):
        print("만듦:", p.name)
