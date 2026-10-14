import json
import shutil
from pathlib import Path

import pytest
from asserts import assert_equal
from smart_webdriver_manager.cache import DriverCache
from smart_webdriver_manager.utils import mktempdir
from util import put_fake_driver


def test_sync_keeps_live_entries_intact():
    """Verify a missing binary drops its own entry and leaves the rest as put.

    Mutation: rebuilding metadata from the folder layout, which records the
    downloaded zip or a subfolder as the binary.
    Oracle: the binary paths put() returned.
    """
    with mktempdir() as base_path:
        cache = DriverCache('chromedriver', base_path)
        live_path = put_fake_driver(cache, '120.0.6099.109')
        gone_path = put_fake_driver(cache, '121.0.6167.85')
        shutil.rmtree(gone_path.parent.parent)

        assert_equal(cache.get('121.0.6167.85'), None)
        assert_equal(cache.get('120.0.6099.109'), live_path)
        metadata = json.loads(Path(base_path, 'drivers.json').read_text())
        assert_equal(set(metadata), {'chromedriver_120.0.6099.109'})


def test_metadata_file_is_world_readable():
    """Verify drivers.json is readable by other users of a shared cache.

    Mutation: dropping the chmod, so mkstemp leaves the file at 0o600.
    Oracle: mode 0o644.
    """
    with mktempdir() as base_path:
        put_fake_driver(DriverCache('chromedriver', base_path), '120.0.6099.109')
        mode = Path(base_path, 'drivers.json').stat().st_mode & 0o777
        assert_equal(mode, 0o644)


if __name__ == '__main__':
    pytest.main(args=['-s', __file__])
