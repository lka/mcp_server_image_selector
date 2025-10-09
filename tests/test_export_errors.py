import os
import shutil
import pytest  # type: ignore
from PIL import Image
import sys
import types

# ensure src/ is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

# lightweight mcp mocks (same approach as other tests)
if "mcp" not in sys.modules:
    _m = types.ModuleType("mcp")
    _m_server = types.ModuleType("mcp.server")
    setattr(_m_server, "Server", object)
    _m_server_stdio = types.ModuleType("mcp.server.stdio")
    _m_types = types.ModuleType("mcp.types")
    setattr(_m_types, "Tool", object)
    setattr(_m_types, "TextContent", object)
    sys.modules["mcp"] = _m
    sys.modules["mcp.server"] = _m_server
    sys.modules["mcp.server.stdio"] = _m_server_stdio
    sys.modules["mcp.types"] = _m_types

from mcp_server_image_selector.server import export_regions


def make_test_image(path, size=(200, 100), color=(255, 0, 0)):
    img = Image.new("RGB", size, color)
    img.save(path, "JPEG")


def test_export_with_empty_regions(tmp_path):
    base_dir = str(tmp_path)
    img_path = os.path.join(base_dir, "test.jpg")
    make_test_image(img_path)

    result = export_regions(img_path, [], base_dir)
    assert result["success"] is True
    assert result["exported_count"] == 0
    shutil.rmtree(base_dir)


def test_export_with_invalid_coords(tmp_path):
    base_dir = str(tmp_path)
    img_path = os.path.join(base_dir, "test.jpg")
    make_test_image(img_path)

    regions = [{"coords": (1000, 1000, 2000, 2000), "mode": "foto"}]
    # out-of-bounds coords should not raise, but result should be success with 0 exported or handled gracefully
    result = export_regions(img_path, regions, base_dir)
    assert result["success"] is True
    # If crop works, exported_count may be 1; we accept 0 or 1
    assert result["exported_count"] in (0, 1)
    shutil.rmtree(base_dir)


def test_export_missing_image_raises(tmp_path):
    base_dir = str(tmp_path)
    img_path = os.path.join(base_dir, "missing.jpg")

    with pytest.raises(Exception):
        export_regions(img_path, [], base_dir)
