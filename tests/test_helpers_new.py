from mcp_server_image_selector.server import transform_coords, format_export_paths


def test_transform_coords_normal():
    coords = (100, 100, 200, 200)
    scaled = transform_coords(coords, 2.0)
    assert scaled == (50, 50, 100, 100)


def test_transform_coords_zero_scale():
    coords = (10, 10, 20, 20)
    try:
        transform_coords(coords, 0)
        assert False, "Expected ValueError for zero scale"
    except ValueError:
        pass


def test_format_export_paths_foto(tmp_path):
    base = "img"
    ts = "20250101_000000"
    info = format_export_paths(base, ts, 1, "foto", str(tmp_path))
    assert info["type"] == "foto"
    assert info["file"].endswith("_region01_foto.png")


def test_format_export_paths_text(tmp_path):
    base = "img"
    ts = "20250101_000000"
    info = format_export_paths(base, ts, 2, "text", str(tmp_path))
    assert info["type"] == "text"
    assert info["image_file"].endswith("_region02_text.png")
    assert info["text_file"].endswith("_region02_text.txt")
