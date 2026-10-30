import pytest

Image = pytest.importorskip("PIL.Image")  # assets 그룹 없이 돌리면 건너뜀

from tools.icons import make_icons  # noqa: E402


def test_makes_square_icons_in_each_size(tmp_path):
    src = tmp_path / "rabbit.webp"
    img = Image.new("RGBA", (300, 512), (0, 0, 0, 0))
    img.paste((255, 255, 255, 255), (50, 50, 250, 462))
    img.save(src)
    paths = make_icons(src, tmp_path / "out")
    sizes = {}
    for p in paths:
        with Image.open(p) as icon:
            sizes[p.name] = icon.size
            assert icon.mode == "RGB"  # 아이폰 홈 화면 아이콘은 투명을 검게 칠하므로 배경을 채운다
    assert sizes == {"icon-192.png": (192, 192), "icon-512.png": (512, 512), "apple-touch-icon.png": (180, 180)}
