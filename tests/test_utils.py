"""
Tests für Utility-Funktionen (utils.py und export.py)
"""

import os
import shutil
from mcp_server_image_selector.utils import create_tmp_dir_if_needed, cleanup_tmp_dir, get_working_dir, transform_coords
from mcp_server_image_selector.export import format_export_paths


# Tests für Verzeichnis-Funktionen

def test_create_tmp_dir_if_needed(tmp_path, monkeypatch):
    # Set up temporary working directory
    monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))

    tmp_dir = create_tmp_dir_if_needed()
    assert os.path.isdir(tmp_dir)
    assert tmp_dir.endswith(os.path.join(get_working_dir(), "tmp"))

    # Cleanup
    shutil.rmtree(tmp_dir)
    assert not os.path.exists(tmp_dir)


def test_cleanup_tmp_dir_with_files(tmp_path, monkeypatch):
    """Test cleanup_tmp_dir removes all files from tmp directory"""
    # Set up temporary working directory
    monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))

    # Create tmp directory and some test files
    tmp_dir = create_tmp_dir_if_needed()

    test_file1 = os.path.join(tmp_dir, "test1.png")
    test_file2 = os.path.join(tmp_dir, "test2.txt")
    test_file3 = os.path.join(tmp_dir, "test3.jpg")

    # Create test files
    with open(test_file1, "w") as f:
        f.write("test content 1")
    with open(test_file2, "w") as f:
        f.write("test content 2")
    with open(test_file3, "w") as f:
        f.write("test content 3")

    # Verify files exist
    assert os.path.exists(test_file1)
    assert os.path.exists(test_file2)
    assert os.path.exists(test_file3)
    assert len(os.listdir(tmp_dir)) == 3

    # Run cleanup
    cleanup_tmp_dir()

    # Verify all files are deleted but directory still exists
    assert os.path.exists(tmp_dir)
    assert len(os.listdir(tmp_dir)) == 0
    assert not os.path.exists(test_file1)
    assert not os.path.exists(test_file2)
    assert not os.path.exists(test_file3)


def test_cleanup_tmp_dir_empty_directory(tmp_path, monkeypatch):
    """Test cleanup_tmp_dir works with empty tmp directory"""
    # Set up temporary working directory
    monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))

    # Create tmp directory
    tmp_dir = create_tmp_dir_if_needed()

    # Verify directory is empty
    assert len(os.listdir(tmp_dir)) == 0

    # Run cleanup (should not raise any errors)
    cleanup_tmp_dir()

    # Verify directory still exists and is empty
    assert os.path.exists(tmp_dir)
    assert len(os.listdir(tmp_dir)) == 0


def test_cleanup_tmp_dir_nonexistent(tmp_path, monkeypatch):
    """Test cleanup_tmp_dir creates tmp directory if it doesn't exist"""
    # Set up temporary working directory
    monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))

    tmp_dir = os.path.join(str(tmp_path), "tmp")

    # Verify tmp directory doesn't exist yet
    assert not os.path.exists(tmp_dir)

    # Run cleanup (should create the directory)
    cleanup_tmp_dir()

    # Verify directory now exists and is empty
    assert os.path.exists(tmp_dir)
    assert len(os.listdir(tmp_dir)) == 0


# Tests für Koordinaten-Transformation

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


# Tests für Export-Pfade

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
