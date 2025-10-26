"""
Tests für GUI-spezifische Helper-Funktionen
"""

from mcp_server_image_selector.gui import ImageSelectorGUI


def test_compute_scale_small_image():
    # image smaller than canvas -> scale up to 1.25 (25% vergrößert)
    scale = ImageSelectorGUI.compute_scale(400, 300, 800, 600)
    assert 0 < scale <= 1.25
    assert scale == 1.25


def test_compute_scale_large_image():
    # image larger than canvas -> scale < 1.0
    scale = ImageSelectorGUI.compute_scale(2000, 1500, 800, 600)
    assert 0 < scale < 1.0
