import os
import sys
import types

# Ensure the package in src/ is importable during tests
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

# Provide lightweight mocks for the external 'mcp' package so tests can run
# without the real dependency installed.
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

from mcp_server_image_selector.gui import ImageSelectorGUI

TEST_IMAGE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Scan20250919130047_1.jpeg"))


def test_load_image_sets_original_image(tmp_path):
    gui = ImageSelectorGUI(TEST_IMAGE, str(tmp_path), create_ui=False)
    try:
        assert gui.original_image is not None
        assert gui.original_image.size[0] > 0
        assert gui.original_image.size[1] > 0
    finally:
        if getattr(gui, "root", None):
            gui.root.destroy()


def test_scale_factor_within_bounds(tmp_path):
    gui = ImageSelectorGUI(TEST_IMAGE, str(tmp_path), create_ui=False)
    try:
        assert 0 < gui.scale_factor <= 1.0
    finally:
        if getattr(gui, "root", None):
            gui.root.destroy()
