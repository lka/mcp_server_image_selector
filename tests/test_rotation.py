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

from mcp_server_image_selector.server import ImageSelectorGUI

TEST_IMAGE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Scan20250919130047_1.jpeg"))


def test_rotate_image_90_degrees_right(tmp_path):
    """Test rotating image 90 degrees to the right"""
    gui = ImageSelectorGUI(TEST_IMAGE, str(tmp_path), create_ui=False)
    try:
        original_width, original_height = gui.original_image.size

        # Rotate 90 degrees right
        gui.rotate_image(90)

        # After 90° rotation, width and height should be swapped
        new_width, new_height = gui.original_image.size
        assert new_width == original_height
        assert new_height == original_width
    finally:
        if getattr(gui, "root", None):
            gui.root.destroy()


def test_rotate_image_90_degrees_left(tmp_path):
    """Test rotating image 90 degrees to the left"""
    gui = ImageSelectorGUI(TEST_IMAGE, str(tmp_path), create_ui=False)
    try:
        original_width, original_height = gui.original_image.size

        # Rotate 90 degrees left
        gui.rotate_image(-90)

        # After 90° rotation, width and height should be swapped
        new_width, new_height = gui.original_image.size
        assert new_width == original_height
        assert new_height == original_width
    finally:
        if getattr(gui, "root", None):
            gui.root.destroy()


def test_rotate_image_180_degrees(tmp_path):
    """Test rotating image 180 degrees"""
    gui = ImageSelectorGUI(TEST_IMAGE, str(tmp_path), create_ui=False)
    try:
        original_width, original_height = gui.original_image.size

        # Rotate 180 degrees
        gui.rotate_image(180)

        # After 180° rotation, dimensions should remain the same
        new_width, new_height = gui.original_image.size
        assert new_width == original_width
        assert new_height == original_height
    finally:
        if getattr(gui, "root", None):
            gui.root.destroy()


def test_rotate_image_clears_regions(tmp_path):
    """Test that rotating image clears all saved regions"""
    gui = ImageSelectorGUI(TEST_IMAGE, str(tmp_path), create_ui=False)
    try:
        # Add some mock regions
        gui.regions = [
            {"coords": (10, 10, 100, 100), "mode": "foto", "rect_id": None},
            {"coords": (200, 200, 300, 300), "mode": "text", "rect_id": None}
        ]

        # Set current selection
        gui.current_selection = (50, 50, 150, 150)

        # Rotate image
        gui.rotate_image(90)

        # Verify regions are cleared
        assert len(gui.regions) == 0
        assert gui.current_selection is None
        assert gui.current_rect is None
    finally:
        if getattr(gui, "root", None):
            gui.root.destroy()


def test_rotate_image_full_circle(tmp_path):
    """Test that rotating 4 times by 90 degrees returns to original dimensions"""
    gui = ImageSelectorGUI(TEST_IMAGE, str(tmp_path), create_ui=False)
    try:
        original_width, original_height = gui.original_image.size

        # Rotate 4 times by 90 degrees right (full circle)
        for _ in range(4):
            gui.rotate_image(90)

        # Should be back to original dimensions
        final_width, final_height = gui.original_image.size
        assert final_width == original_width
        assert final_height == original_height
    finally:
        if getattr(gui, "root", None):
            gui.root.destroy()


def test_rotate_image_with_no_image(tmp_path):
    """Test that rotate_image handles None image gracefully"""
    gui = ImageSelectorGUI(TEST_IMAGE, str(tmp_path), create_ui=False)
    try:
        # Set image to None
        gui.original_image = None

        # Should not raise an error
        gui.rotate_image(90)

        # Image should still be None
        assert gui.original_image is None
    finally:
        if getattr(gui, "root", None):
            gui.root.destroy()


def test_export_with_rotated_image(tmp_path):
    """Test that export uses the rotated image, not the original"""
    from mcp_server_image_selector.server import export_regions
    from PIL import Image

    gui = ImageSelectorGUI(TEST_IMAGE, str(tmp_path), create_ui=False)
    try:
        # Get original dimensions
        original_width, original_height = gui.original_image.size

        # Rotate 90 degrees
        gui.rotate_image(90)

        # Verify rotation happened
        rotated_width, rotated_height = gui.original_image.size
        assert rotated_width == original_height
        assert rotated_height == original_width

        # Create a test region that covers a portion of the rotated image
        # Using coordinates relative to rotated image
        test_region = {
            "coords": (10, 10, 100, 100),
            "mode": "foto",
            "rect_id": None
        }

        # Export the region with the rotated image
        result = export_regions(
            TEST_IMAGE,
            [test_region],
            str(tmp_path),
            image_object=gui.original_image
        )

        # Verify export was successful
        assert result["success"] is True
        assert result["exported_count"] == 1

        # Load the exported image and verify it came from the rotated image
        exported_file = result["files"][0]["file"]
        assert os.path.exists(exported_file)

        exported_image = Image.open(exported_file)
        # The exported region should be 90x90 pixels (100-10 = 90)
        assert exported_image.size == (90, 90)

    finally:
        if getattr(gui, "root", None):
            gui.root.destroy()
