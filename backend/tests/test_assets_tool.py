import pytest

Image = pytest.importorskip("PIL.Image")  # assets 그룹 없이 돌리면 건너뜀

from app.catalog import load_catalog  # noqa: E402
from tools.assets import convert, convert_all  # noqa: E402


class FakeRemoveBg:
    """rembg 대신: 호출 횟수를 세고, 구석 한 점을 투명하게 만든 RGBA 를 돌려준다
    (완전히 불투명하면 WebP 가 알파를 빼고 저장한다)"""

    def __init__(self):
        self.calls = 0

    def __call__(self, img):
        self.calls += 1
        img = img.convert("RGBA")
        img.putpixel((0, 0), (0, 0, 0, 0))
        return img


def make_png(path, size):
    Image.new("RGB", size, "white").save(path)
    return path


def test_character_becomes_512_webp_with_alpha(tmp_path):
    src = make_png(tmp_path / "bear.png", (1024, 1024))
    remove_bg = FakeRemoveBg()
    out = convert(src, tmp_path / "out", "character", remove_bg)
    assert out == tmp_path / "out" / "bear.webp"
    with Image.open(out) as img:
        assert img.size == (512, 512)
        assert img.mode == "RGBA"
    assert remove_bg.calls == 1


def test_transparent_margin_is_trimmed(tmp_path):
    """원본에서 인물이 작게 그려져도 투명 여백을 잘라 512 칸을 채운다"""
    src = make_png(tmp_path / "boy.png", (1024, 1024))

    def keep_center(img):
        out = Image.new("RGBA", img.size, (0, 0, 0, 0))
        out.paste((255, 0, 0, 255), (412, 312, 612, 712))  # 200×400 인물
        return out

    out = convert(src, tmp_path / "out", "character", keep_center)
    with Image.open(out) as img:
        assert img.size == (256, 512)


def test_background_keeps_ratio_without_removal(tmp_path):
    src = make_png(tmp_path / "forest.png", (1344, 768))
    remove_bg = FakeRemoveBg()
    out = convert(src, tmp_path / "out", "background", remove_bg)
    with Image.open(out) as img:
        assert img.size == (1024, 585)
    assert remove_bg.calls == 0


def test_unknown_id_is_skipped(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    make_png(raw / "nope.png", (64, 64))
    make_png(raw / "bear.png", (64, 64))
    out_dir = tmp_path / "out"
    warnings = convert_all(raw, out_dir, load_catalog(), FakeRemoveBg())
    assert not (out_dir / "nope.webp").exists()
    assert (out_dir / "bear.webp").exists()
    assert any("nope" in w for w in warnings)


def test_up_to_date_file_is_not_converted_again(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    make_png(raw / "bear.png", (64, 64))
    out_dir = tmp_path / "out"
    convert_all(raw, out_dir, load_catalog(), FakeRemoveBg())
    remove_bg = FakeRemoveBg()
    convert_all(raw, out_dir, load_catalog(), remove_bg)
    assert remove_bg.calls == 0
