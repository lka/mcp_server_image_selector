import os
import sys
import types
from PIL import Image
import shutil

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

from mcp_server_image_selector.export import export_regions


def make_test_image(path, size=(200, 100), color=(255, 0, 0)):
    img = Image.new("RGB", size, color)
    img.save(path, "JPEG")


def test_export_regions(tmp_path):
    base_dir = str(tmp_path)
    img_path = os.path.join(base_dir, "test.jpg")
    make_test_image(img_path)

    regions = [
        {"coords": (10, 10, 100, 80), "mode": "foto"},
        {"coords": (50, 20, 150, 90), "mode": "text"},
    ]

    result = export_regions(img_path, regions, base_dir)

    assert result["success"] is True
    assert result["exported_count"] == 2

    # Check files exist
    for f in result["files"]:
        if f["type"] == "foto":
            assert os.path.exists(f["file"]) is True
        else:
            assert os.path.exists(f["image_file"]) is True
            assert os.path.exists(f["text_file"]) is True

    # Cleanup
    shutil.rmtree(base_dir)
    assert not os.path.exists(base_dir)
