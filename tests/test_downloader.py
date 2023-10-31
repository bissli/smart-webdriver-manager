import os
import pytest
from pathlib import Path
from asserts import assert_equal

from smart_webdriver_manager.utils import download_file, unpack_zip


def test_can_download_driver_as_zip_file():
    url = "http://chromedriver.storage.googleapis.com/2.26/chromedriver_win32.zip"
    with download_file(url) as zip_file:
        assert_equal("chromedriver_win32.zip", Path(zip_file).name)
        files = unpack_zip(zip_file)
        assert_equal(files, ["chromedriver.exe"])


if __name__ == "__main__":
    pytest.main(args=["-s", __file__])
