import os
from mcp_server_image_selector.server import create_tmp_dir_if_needed, ImageSelectorGUI, get_working_dir


def test_compute_scale_small_image():
    # image smaller than canvas -> scale 1.0
    scale = ImageSelectorGUI.compute_scale(400, 300, 800, 600)
    assert 0 < scale <= 1.0
    assert scale == 1.0


def test_compute_scale_large_image():
    # image larger than canvas -> scale < 1.0
    scale = ImageSelectorGUI.compute_scale(2000, 1500, 800, 600)
    assert 0 < scale < 1.0


def test_get_working_dir_creates(tmp_path, monkeypatch):
    # set a temporary working dir via env var
    monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
    p = create_tmp_dir_if_needed()
    assert os.path.isdir(p)
    assert p.endswith(os.path.join(get_working_dir(), "tmp"))
    # cleanup
    os.rmdir(p)
