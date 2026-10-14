import json
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from asserts import assert_equal
from smart_webdriver_manager.cache import DriverCache
from smart_webdriver_manager.utils import mktempdir, unpack_zip
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


def test_concurrent_put_of_one_release_unpacks_once(monkeypatch):
    """Verify two concurrent puts of one release unpack it once.

    Mutation: dropping the per-key lock, or the metadata re-check under it.
    Oracle: a stub that records each unpack and holds it long enough for the
    second put to arrive.
    """
    unpacked = []

    def slow_unpack(zip_path):
        unpacked.append(zip_path)
        time.sleep(0.5)
        return unpack_zip(zip_path)

    monkeypatch.setattr('smart_webdriver_manager.cache.unpack_zip', slow_unpack)
    with mktempdir() as base_path:
        cache = DriverCache('chromedriver', base_path)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(put_fake_driver, cache, '120.0.6099.109')
                for _ in range(2)
                ]
            paths = [future.result() for future in futures]

        assert_equal(len(unpacked), 1)
        assert_equal(paths[0], paths[1])


def test_remove_waits_for_put_of_same_release(monkeypatch):
    """Verify remove during a put waits for it, then removes the release.

    Mutation: remove taking no per-key lock, so it deletes the folder
    under the unpack.
    Oracle: a stub unpack that holds the put open while remove runs.
    """
    def slow_unpack(zip_path):
        time.sleep(0.5)
        return unpack_zip(zip_path)

    monkeypatch.setattr('smart_webdriver_manager.cache.unpack_zip', slow_unpack)
    with mktempdir() as base_path:
        cache = DriverCache('chromedriver', base_path)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(put_fake_driver, cache, '120.0.6099.109')
            time.sleep(0.2)
            cache.remove('120.0.6099.109')
            future.result()

        assert_equal(cache.get('120.0.6099.109'), None)


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
