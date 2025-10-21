import os
import sys
import types
from PIL import Image

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

from mcp_server_image_selector.server import extract_image_from_pdf, ImageSelectorGUI, export_regions

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


def create_test_pdf_with_image(pdf_path, image_size=(400, 300), image_color=(0, 0, 255)):
    """Creates a simple PDF with an embedded image using PyMuPDF."""
    if not PYMUPDF_AVAILABLE:
        return False

    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        doc = fitz.open()
        page = doc.new_page(width=image_size[0], height=image_size[1])

        # Create a temporary image
        temp_img = Image.new("RGB", image_size, image_color)
        temp_img_path = pdf_path.replace(".pdf", "_temp.png")
        temp_img.save(temp_img_path, "PNG")

        # Insert the image into the PDF
        page.insert_image(fitz.Rect(0, 0, image_size[0], image_size[1]), filename=temp_img_path)

        # Save the PDF
        doc.save(pdf_path)
        doc.close()

        # Clean up temporary image
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)

        return True
    except Exception as e:
        print(f"Error creating test PDF: {e}")
        return False


def create_test_pdf_text_only(pdf_path):
    """Creates a PDF with only text (no embedded images) using PyMuPDF."""
    if not PYMUPDF_AVAILABLE:
        return False

    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        doc = fitz.open()
        page = doc.new_page(width=595, height=842)  # A4 size

        # Add some text
        text = "This is a test PDF document\nwith multiple lines of text."
        page.insert_text((50, 50), text, fontsize=14)

        doc.save(pdf_path)
        doc.close()
        return True
    except Exception as e:
        print(f"Error creating test PDF: {e}")
        return False


def test_extract_image_from_pdf_with_embedded_image(tmp_path, monkeypatch):
    """Test extraction of embedded image from PDF."""
    if not PYMUPDF_AVAILABLE:
        print("PyMuPDF not available, skipping test")
        return

    base_dir = str(tmp_path)
    # Set up temporary working directory
    monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", base_dir)

    pdf_path = os.path.join(base_dir, "test_with_image.pdf")

    # Create a test PDF with an embedded image
    success = create_test_pdf_with_image(pdf_path, image_size=(400, 300), image_color=(0, 0, 255))
    if not success:
        print("Failed to create test PDF, skipping test")
        return

    # Extract the image
    extracted_path = extract_image_from_pdf(pdf_path, base_dir)

    # Verify the extraction
    assert extracted_path is not None, "Failed to extract image from PDF"
    assert os.path.exists(extracted_path), f"Extracted image does not exist at {extracted_path}"

    # Verify it's a valid image
    img = Image.open(extracted_path)
    assert img is not None, "Extracted file is not a valid image"
    assert img.size[0] > 0 and img.size[1] > 0, "Extracted image has invalid dimensions"
    img.close()  # Close the image handle


def test_extract_image_from_pdf_text_only(tmp_path, monkeypatch):
    """Test rendering of PDF page when no embedded image exists."""
    if not PYMUPDF_AVAILABLE:
        print("PyMuPDF not available, skipping test")
        return

    base_dir = str(tmp_path)
    # Set up temporary working directory
    monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", base_dir)

    pdf_path = os.path.join(base_dir, "test_text_only.pdf")

    # Create a test PDF with only text
    success = create_test_pdf_text_only(pdf_path)
    if not success:
        print("Failed to create test PDF, skipping test")
        return

    # Extract/render the page
    extracted_path = extract_image_from_pdf(pdf_path, base_dir)

    # Verify the rendering
    assert extracted_path is not None, "Failed to render PDF page"
    assert os.path.exists(extracted_path), f"Rendered image does not exist at {extracted_path}"
    assert "_rendered.png" in extracted_path, "Output should be a rendered PNG"

    # Verify it's a valid image
    img = Image.open(extracted_path)
    assert img is not None, "Rendered file is not a valid image"
    assert img.size[0] > 0 and img.size[1] > 0, "Rendered image has invalid dimensions"
    img.close()  # Close the image handle


def test_image_selector_gui_with_pdf(tmp_path, monkeypatch):
    """Test ImageSelectorGUI initialization with a PDF file."""
    if not PYMUPDF_AVAILABLE:
        print("PyMuPDF not available, skipping test")
        return

    base_dir = str(tmp_path)
    # Set up temporary working directory
    monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", base_dir)

    pdf_path = os.path.join(base_dir, "test_gui.pdf")

    # Create a test PDF with an embedded image
    success = create_test_pdf_with_image(pdf_path, image_size=(600, 400), image_color=(255, 0, 0))
    if not success:
        print("Failed to create test PDF, skipping test")
        return

    # Initialize GUI without creating actual UI (create_ui=False)
    gui = ImageSelectorGUI(pdf_path, base_dir, create_ui=False)

    # Verify PDF was detected and processed
    assert gui.is_pdf is True, "PDF file was not detected as PDF"
    assert gui.original_image_path == pdf_path, "Original path not preserved"
    assert gui.extracted_image_path is not None, "Image was not extracted from PDF"
    assert os.path.exists(gui.image_path), "Extracted image does not exist"

    # Verify the extracted image is in the tmp directory
    expected_tmp_dir = os.path.join(base_dir, "tmp")
    assert gui.extracted_image_path.startswith(expected_tmp_dir), f"Extracted image should be in tmp dir, got {gui.extracted_image_path}"

    # Verify the image was loaded
    assert gui.original_image is not None, "Image was not loaded"
    assert gui.image is not None, "Resized image was not created"


def test_export_regions_from_pdf(tmp_path, monkeypatch):
    """Test exporting regions from a PDF-sourced image."""
    if not PYMUPDF_AVAILABLE:
        print("PyMuPDF not available, skipping test")
        return

    base_dir = str(tmp_path)
    # Set up temporary working directory
    monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", base_dir)

    pdf_path = os.path.join(base_dir, "test_export.pdf")

    # Create a test PDF with an embedded image
    success = create_test_pdf_with_image(pdf_path, image_size=(400, 300), image_color=(0, 255, 0))
    if not success:
        print("Failed to create test PDF, skipping test")
        return

    # Initialize GUI without creating actual UI
    gui = ImageSelectorGUI(pdf_path, base_dir, create_ui=False)

    # Define regions to export
    regions = [
        {"coords": (10, 10, 100, 80), "mode": "foto"},
        {"coords": (50, 20, 150, 100), "mode": "text"},
    ]

    # Export regions using the image from PDF
    result = export_regions(pdf_path, regions, base_dir, image_object=gui.original_image)

    # Verify export
    assert result["success"] is True, "Export failed"
    assert result["exported_count"] == 2, f"Expected 2 exports, got {result['exported_count']}"

    # Check files exist
    for f in result["files"]:
        if f["type"] == "foto":
            assert os.path.exists(f["file"]), f"Foto file does not exist: {f['file']}"
        else:
            assert os.path.exists(f["image_file"]), f"Text image file does not exist: {f['image_file']}"
            assert os.path.exists(f["text_file"]), f"Text file does not exist: {f['text_file']}"


def test_pdf_with_invalid_file():
    """Test error handling for invalid PDF file."""
    if not PYMUPDF_AVAILABLE:
        print("PyMuPDF not available, skipping test")
        return

    # Test with non-existent file
    result = extract_image_from_pdf("/path/to/nonexistent.pdf")
    assert result is None, "Should return None for invalid file"


if __name__ == "__main__":
    import tempfile
    import pathlib

    print("Running PDF tests...")

    if not PYMUPDF_AVAILABLE:
        print("WARNING: PyMuPDF is not available. Tests will be skipped.")
        sys.exit(0)

    # Run tests with temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = pathlib.Path(tmpdir)

        print("Test 1: Extract embedded image from PDF")
        test_extract_image_from_pdf_with_embedded_image(tmp_path / "test1")
        print("[PASS]")

        print("Test 2: Render text-only PDF")
        test_extract_image_from_pdf_text_only(tmp_path / "test2")
        print("[PASS]")

        print("Test 3: ImageSelectorGUI with PDF")
        test_image_selector_gui_with_pdf(tmp_path / "test3")
        print("[PASS]")

        print("Test 4: Export regions from PDF")
        test_export_regions_from_pdf(tmp_path / "test4")
        print("[PASS]")

        print("Test 5: Invalid PDF file")
        test_pdf_with_invalid_file()
        print("[PASS]")

    print("\nAll PDF tests passed!")
