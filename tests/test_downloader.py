import os
import zipfile
from pathlib import Path

import pytest
from asserts import assert_equal, assert_false, assert_true
from smart_webdriver_manager.utils import download_file, mktempdir, unpack_zip


def test_can_download_driver_as_zip_file():
    url = 'http://chromedriver.storage.googleapis.com/2.26/chromedriver_win32.zip'
    with download_file(url) as zip_file:
        assert_equal('chromedriver_win32.zip', Path(zip_file).name)
        files = unpack_zip(zip_file)
        assert_equal(files, ['chromedriver.exe'])


def test_unpack_zip_raises_corrupt_archive_error():
    """Verify a corrupt member raises BadZipFile from unpack_zip.

    Mutation: reading e.args[1] on any exception, which raises IndexError
    for a one-argument error.
    Oracle: zipfile's CRC check on a member with one byte flipped.
    """
    with mktempdir() as tmpdir:
        zip_path = Path(tmpdir, 'chromedriver.zip')
        with zipfile.ZipFile(zip_path, 'w') as archive:
            archive.writestr('chromedriver', b'abcdefgh')
        data = zip_path.read_bytes().replace(b'abcdefgh', b'abcdefgX', 1)
        zip_path.write_bytes(data)
        with pytest.raises(zipfile.BadZipFile):
            unpack_zip(zip_path)


def test_unpack_zip_closes_archive_on_error():
    """Verify unpack_zip closes the zip even when extraction raises.

    Mutation: opening the archive without a with block, so the raised
    error's traceback keeps the file open.
    Oracle: the process's open file descriptors, read from /proc.
    """
    with mktempdir() as tmpdir:
        zip_path = Path(tmpdir, 'chromedriver.zip')
        with zipfile.ZipFile(zip_path, 'w') as archive:
            archive.writestr('chromedriver', b'abcdefgh')
        data = zip_path.read_bytes().replace(b'abcdefgh', b'abcdefgX', 1)
        zip_path.write_bytes(data)
        with pytest.raises(zipfile.BadZipFile) as excinfo:
            unpack_zip(zip_path)
        open_paths = {os.path.realpath(fd) for fd in Path('/proc/self/fd').iterdir()}
        assert_false(str(zip_path.resolve()) in open_paths)
        assert_true(excinfo.value)


if __name__ == '__main__':
    pytest.main(args=['-s', __file__])
