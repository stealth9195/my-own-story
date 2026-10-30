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
# 흰 부분이 배경째 지워지던 그림. 두 모델 결과를 합치고 윤곽선 안쪽을 메운다.
# 전체에 쓰지 않는 이유: 무지개처럼 원래 비어 있는 안쪽까지 채워진다
CAREFUL_IDS = {"letter", "unicorn", "ship"}

RemoveBg = Callable[[Image.Image], Image.Image]


def merge_masks(masks: list[Image.Image]) -> Image.Image:
    """모델별 알파 마스크마다 윤곽선 안쪽 구멍을 메운 뒤 합친다(더 불투명한 쪽)"""
    import numpy as np
    from scipy.ndimage import binary_fill_holes

    merged = None
    for mask in masks:
        a = np.array(mask.convert("L"))
        a = np.where(binary_fill_holes(a > 128), 255, a)
        merged = a if merged is None else np.maximum(merged, a)
    return Image.fromarray(merged.astype("uint8"))


def convert(src: Path, out_dir: Path, kind: str, remove_bg: RemoveBg) -> Path:
    """배경은 배경 제거 없이 폭 1024, 캐릭터·사물은 배경 제거 후 긴 변 512"""
    out_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as img:
        if kind == "background":
            img = img.convert("RGB")
            img = img.resize((1024, round(img.height * 1024 / img.width)), Image.LANCZOS)
        else:
            img = remove_bg(img).convert("RGBA")
            # 거의 투명한 잡티는 지우고, 투명 여백을 잘라야 작게 그려진 인물도 칸을 채운다
            img.putalpha(img.getchannel("A").point(lambda v: v if v > 16 else 0))
            bbox = img.getchannel("A").getbbox()
            if bbox:
                img = img.crop(bbox)
            scale = 512 / max(img.size)
            img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
        out = out_dir / f"{src.stem}.webp"
        img.save(out, "WEBP", quality=80)
    return out


def convert_all(raw_dir: Path, out_dir: Path, catalog: Catalog, remove_bg: RemoveBg,
                careful_remove_bg: RemoveBg | None = None) -> list[str]:
    """raw_dir 의 PNG 를 모두 변환. 이미 최신이면 건너뛰고, catalog 에 없는 이름은 경고로 돌려준다.
    CAREFUL_IDS 는 careful_remove_bg 로 배경을 지운다"""
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
        careful = careful_remove_bg and src.stem in CAREFUL_IDS
        convert(src, out_dir, kind, careful_remove_bg if careful else remove_bg)
        print(f"변환: {src.name} → {out.name}")
    return warnings


def main() -> None:
    from rembg import new_session, remove  # 무거워서 실제 실행 때만 불러온다

    # 기본은 bria-rmbg(rembg 기본값). CAREFUL_IDS 만 u2net·birefnet 결과를 합친다(시험해 본 조합)
    default = new_session("bria-rmbg")
    careful_sessions = [new_session("u2net"), new_session("birefnet-general-lite")]

    def careful(img: Image.Image) -> Image.Image:
        out = img.convert("RGBA")
        out.putalpha(merge_masks([remove(img, session=s).getchannel("A") for s in careful_sessions]))
        return out

    warnings = convert_all(RAW_DIR, OUT_DIR, load_catalog(),
                           lambda img: remove(img, session=default), careful)
    for w in warnings:
        print("경고:", w)


if __name__ == "__main__":
    main()
