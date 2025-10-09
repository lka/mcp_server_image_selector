import os
import shutil
from mcp_server_image_selector.server import create_tmp_dir_if_needed


def test_create_tmp_dir_if_needed(tmp_path):
    base = str(tmp_path)
    tmp_dir = create_tmp_dir_if_needed(base)
    assert os.path.isdir(tmp_dir)
    assert tmp_dir.endswith(os.path.join(base, "tmp"))

    # Cleanup
    shutil.rmtree(tmp_dir)
    assert not os.path.exists(tmp_dir)
