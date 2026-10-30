"""그림 원본(assets/raw/{id}.png)을 앱용 WebP(frontend/public/img/{id}.webp)로 바꾼다.

개발 PC 에서만 쓴다(배포에는 안 들어감):
    uv run --group assets python -m tools.assets
"""
from collections.abc import Callable
from pathlib import Path

from PIL import Image

from app.catalog import Catalog, load_catalog
from app.config import REPO_ROOT

RAW_DIR = REPO_ROOT / "assets" / "raw"
OUT_DIR = REPO_ROOT / "frontend" / "public" / "img"
IMAGE_KINDS = {"character", "object", "background"}

RemoveBg = Callable[[Image.Image], Image.Image]


def convert(src: Path, out_dir: Path, kind: str, remove_bg: RemoveBg) -> Path:
    """배경은 배경 제거 없이 폭 1024, 캐릭터·사물은 배경 제거 후 긴 변 512"""
    out_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as img:
        if kind == "background":
            img = img.convert("RGB")
            img = img.resize((1024, round(img.height * 1024 / img.width)), Image.LANCZOS)
        else:
            img = remove_bg(img).convert("RGBA")
            # 투명 여백을 잘라야 작게 그려진 인물도 칸을 채운다
            bbox = img.getchannel("A").getbbox()
            if bbox:
                img = img.crop(bbox)
            scale = 512 / max(img.size)
            img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
        out = out_dir / f"{src.stem}.webp"
        img.save(out, "WEBP", quality=80)
    return out


def convert_all(raw_dir: Path, out_dir: Path, catalog: Catalog, remove_bg: RemoveBg) -> list[str]:
    """raw_dir 의 PNG 를 모두 변환. 이미 최신이면 건너뛰고, catalog 에 없는 이름은 경고로 돌려준다"""
    warnings = []
    for src in sorted(raw_dir.glob("*.png")):
        try:
            kind = catalog.kind_of(src.stem)
        except KeyError:
            kind = None
        if kind not in IMAGE_KINDS:
            warnings.append(f"catalog 에 그림 id 가 없어 건너뜀: {src.name}")
            continue
        out = out_dir / f"{src.stem}.webp"
        if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
            continue
        convert(src, out_dir, kind, remove_bg)
        print(f"변환: {src.name} → {out.name}")
    return warnings


def main() -> None:
    from rembg import new_session, remove  # 무거워서 실제 실행 때만 불러온다

    session = new_session()
    warnings = convert_all(RAW_DIR, OUT_DIR, load_catalog(), lambda img: remove(img, session=session))
    for w in warnings:
        print("경고:", w)


if __name__ == "__main__":
    main()
