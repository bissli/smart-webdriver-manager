import json
import multiprocessing
import os
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from asserts import assert_equal, assert_true
from smart_webdriver_manager.cache import DriverCache
from smart_webdriver_manager.utils import mktempdir


def _make_fake_zip(dst_dir):
    """Create a single-entry zip whose sole member is a fake chromedriver.

    A one-member archive makes _match_binary return that member directly, so
    the entry name and byte contents are irrelevant to the cache logic.
    """
    zip_path = Path(dst_dir, 'chromedriver.zip')
    with zipfile.ZipFile(zip_path, 'w') as archive:
        archive.writestr('chromedriver', b'#!/bin/sh\necho fake\n')
    return zip_path


def _stress_worker(base_path, worker_id, rounds, barrier):
    """Provision `rounds` distinct releases, synchronizing on every round.

    Each round builds its own zip (put() moves the source), waits on the
    shared barrier so all workers hit the metadata write together, then caches
    a release unique to this worker and round. A put() that raises (a corrupt
    read on the unlocked code) is counted rather than re-raised, so the worker
    keeps participating in the barrier and the failure surfaces cleanly through
    the returned count instead of breaking the barrier.
    """
    failures = 0
    for round_idx in range(rounds):
        with mktempdir() as src_dir:
            zip_path = _make_fake_zip(src_dir)
            barrier.wait(timeout=30)
            try:
                DriverCache('chromedriver', base_path).put(
                    zip_path, release=f'{worker_id}.{round_idx}.0.0')
            except Exception:
                failures += 1
    return worker_id, failures


def test_concurrent_multi_version_put_is_lossless():
    """Concurrent different-version provisioning keeps every metadata entry.

    Spawns W processes that hammer put() for distinct releases under a
    per-round barrier, forcing simultaneous read-modify-writes of the shared
    drivers.json. The unlocked code loses entries (last writer wins) and/or
    raises JSONDecodeError on a truncated read; the locked, atomic code records
    no write failures and preserves all W * rounds keys.
    """
    workers = min(8, os.cpu_count() or 4)
    rounds = 25
    with mktempdir() as base_path:
        with multiprocessing.Manager() as manager:
            barrier = manager.Barrier(workers)
            with ProcessPoolExecutor(max_workers=workers) as executor:
                futures = [
                    executor.submit(
                        _stress_worker,
                        base_path,
                        worker_id,
                        rounds,
                        barrier)
                    for worker_id in range(workers)
                    ]
                results = [future.result() for future in futures]

        assert_equal(sum(failures for _, failures in results), 0)
        assert_equal({worker_id for worker_id, _ in results}, set(range(workers)))

        metadata = json.loads(Path(base_path, 'drivers.json').read_text())
        expected_keys = {
            f'chromedriver_{worker_id}.{round_idx}.0.0'
            for worker_id in range(workers)
            for round_idx in range(rounds)
            }
        assert_equal(set(metadata), expected_keys)
        for entry in metadata.values():
            assert_true(Path(entry['binary_path']).exists())


if __name__ == '__main__':
    import pytest
    pytest.main(args=['-s', __file__])
