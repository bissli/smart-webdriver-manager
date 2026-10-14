import glob
import json
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from asserts import assert_equal, assert_false, assert_in, assert_not_equal
from asserts import assert_true
from smart_webdriver_manager import ChromeDriverManager
from smart_webdriver_manager.context import SmartChromeContextManager
from smart_webdriver_manager.utils import mktempdir
from util import put_fake_driver, run_chrome_helper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('==>')


@pytest.fixture(scope='session')
def tempdir():
    with mktempdir() as tmpdir:
        logger.info(f'Made temp dir {tmpdir}')
        yield tmpdir


@pytest.mark.parametrize('version', [120, 118, 117])
def test_chrome_manager_with_specific_version(version, tempdir):
    logger.info('=test_chrome_manager_with_specific_version')

    cdm = ChromeDriverManager(base_path=tempdir, version=version)
    driver_path = Path(cdm.get_driver())
    browser_path = Path(cdm.get_browser())

    assert_true(driver_path.exists())
    assert_in(tempdir, driver_path.parents)
    assert_true(browser_path.exists())
    assert_in(tempdir, browser_path.parents)


def test_chrome_manager_latest(tempdir):
    logger.info('=test_chrome_manager_with_latest_version')

    cdm = ChromeDriverManager(base_path=tempdir)
    driver_path = Path(cdm.get_driver())
    browser_path = Path(cdm.get_browser())

    assert_true(driver_path.exists())
    assert_in(tempdir, driver_path.parents)
    assert_true(browser_path.exists())
    assert_in(tempdir, browser_path.parents)


def test_chrome_manager_with_bad_version(tempdir):
    logger.info('=test_chrome_manager_with_bad_version')
    with pytest.raises(ValueError) as ex:
        ChromeDriverManager(base_path=tempdir, version=60).get_driver()
    assert_in('There is no driver for version 60', ex.value.args[0])


def test_chrome_manager_cached_driver_with_selenium(tempdir):
    logger.info('=test_chrome_manager_cached_driver_with_selenium')

    cdm = ChromeDriverManager(base_path=tempdir, version=119)
    driver_path_1 = Path(cdm.get_driver()).resolve(strict=True)
    browser_path_1 = Path(cdm.get_browser()).resolve(strict=True)
    use_data_path_1 = Path(cdm.get_browser_user_data()).resolve(strict=True)

    cdm = ChromeDriverManager(base_path=tempdir, version=119)
    driver_path_2 = Path(cdm.get_driver()).resolve(strict=True)
    browser_path_2 = Path(cdm.get_browser()).resolve(strict=True)
    assert_equal(driver_path_1, driver_path_2)
    assert_equal(browser_path_1, browser_path_2)

    cdm = ChromeDriverManager(base_path=tempdir, version=118)
    driver_path_3 = Path(cdm.get_driver()).resolve(strict=True)
    browser_path_3 = Path(cdm.get_browser()).resolve(strict=True)
    assert_not_equal(driver_path_1, driver_path_3)
    assert_not_equal(browser_path_1, browser_path_3)


@pytest.mark.parametrize(
    ('platform', 'version'),
    [('Windows', 115), ('Linux', 116), ('Windows', 123), ('Linux', 124),
     ('Darwin', 125), ('Darwin', 126)],
)
def test_can_get_driver_for_platform(platform, version, tempdir, monkeypatch):
    logger.info(f'=test_can_get_driver_for_platform {platform}')

    monkeypatch.setattr('platform.system', lambda: platform)
    cdm = ChromeDriverManager(base_path=tempdir, version=version)
    driver_path = Path(cdm.get_driver())
    assert_true(driver_path.exists())

    scm = SmartChromeContextManager(base_path=tempdir)
    driver_platform = scm.driver_platform

    driver_files = {Path(f).name for f in glob.glob(f'{driver_path.parent}/*')}
    assert_in(f'chromedriver{".exe" if platform=="Windows" else ""}', driver_files)


@pytest.mark.parametrize(
    ('platform', 'version'),
    [('Windows', 115), ('Linux', 116), ('Windows', 123), ('Linux', 124),
     ('Darwin', 125), ('Darwin', 126)],
)
def test_can_get_browser_for_platform(platform, version, tempdir, monkeypatch):
    logger.info(f'=test_can_get_browser_for_platform {platform} {version}')

    monkeypatch.setattr('platform.system', lambda: platform)
    cdm = ChromeDriverManager(base_path=tempdir, version=version)
    browser_path = Path(cdm.get_browser())
    assert_true(browser_path.exists())

    scm = SmartChromeContextManager(base_path=tempdir)
    browser_zip = scm.browser_zip(999999)  # see code

    parent_level = 4 if platform == 'Darwin' else 1
    browser_files = {Path(f).name for f in glob.glob(f'{browser_path.parents[parent_level]}/*')}
    assert_equal(browser_files, {f'chrome-{browser_zip}.zip', f'chrome-{browser_zip}'})


def test_order_doesnt_matter():
    logger.info('=test_order_doesnt_matter')

    with mktempdir() as tmpdir:
        logger.info('> Driver->Browser->Data')
        cdm = ChromeDriverManager(base_path=tmpdir)
        Path(cdm.get_driver()).resolve(strict=True)
        Path(cdm.get_browser()).resolve(strict=True)
        Path(cdm.get_browser_user_data()).resolve(strict=True)
    with mktempdir() as tmpdir:
        logger.info('> Data->Browser->Driver')
        cdm = ChromeDriverManager(base_path=tmpdir)
        Path(cdm.get_browser_user_data()).resolve(strict=True)
        Path(cdm.get_browser()).resolve(strict=True)
        Path(cdm.get_driver()).resolve(strict=True)
    with mktempdir() as tmpdir:
        logger.info('> Data->Driver-Browser')
        cdm = ChromeDriverManager(base_path=tmpdir)
        Path(cdm.get_browser_user_data()).resolve(strict=True)
        Path(cdm.get_driver()).resolve(strict=True)
        Path(cdm.get_browser()).resolve(strict=True)


def test_chrome_uses_data_dir(tempdir):
    logger.info('=test_chrome_uses_data_dir')

    cdm = ChromeDriverManager(base_path=tempdir, version=122)
    driver_path = cdm.get_driver()
    browser_path = cdm.get_browser()
    user_data_dir = cdm.get_browser_user_data()
    run_chrome_helper(driver_path, browser_path, user_data_dir)


def test_remove_chrome_user_data_dir(tempdir):
    logger.info('=test_remove_chrome_user_data_dir')
    cdm = ChromeDriverManager(base_path=tempdir, version=122)
    user_data_dir = cdm.get_browser_user_data()
    assert_true(Path(user_data_dir).exists())
    cdm.remove_browser_user_data()
    assert_false(Path(user_data_dir).exists())


def test_remove_driver(tempdir):
    """Verify remove_driver deletes the cached driver for a version."""
    cdm = ChromeDriverManager(base_path=tempdir, version=120)
    driver_path = Path(cdm.get_driver())
    assert_true(driver_path.exists())
    cdm.remove_driver()
    assert_false(driver_path.exists())


def test_remove_browser(tempdir):
    """Verify remove_browser deletes the cached browser for a version."""
    cdm = ChromeDriverManager(base_path=tempdir, version=120)
    browser_path = Path(cdm.get_browser())
    assert_true(browser_path.exists())
    cdm.remove_browser()
    assert_false(browser_path.exists())


def test_clear_cache(tempdir):
    """Verify clear_cache removes all cached drivers and browsers."""
    cdm = ChromeDriverManager(base_path=tempdir, version=117)
    driver_path = Path(cdm.get_driver())
    browser_path = Path(cdm.get_browser())
    assert_true(driver_path.exists())
    assert_true(browser_path.exists())

    cdm.clear_cache()

    assert_false(driver_path.exists())
    assert_false(browser_path.exists())
    drivers_json = Path(tempdir, 'drivers.json')
    browsers_json = Path(tempdir, 'browsers.json')
    assert_false(drivers_json.exists())
    assert_false(browsers_json.exists())


def test_cached_driver_skips_network(tempdir):
    """Verify get_driver uses cache and skips network for known version."""
    cdm = ChromeDriverManager(base_path=tempdir, version=118)
    driver_path_1 = cdm.get_driver()

    cdm2 = ChromeDriverManager(base_path=tempdir, version=118)
    with patch.object(
        cdm2._cx, 'get_driver_release',
        wraps=cdm2._cx.get_driver_release,
    ) as mock_release:
        driver_path_2 = cdm2.get_driver()
        mock_release.assert_not_called()
    assert_equal(driver_path_1, driver_path_2)


@pytest.fixture
def chrome_endpoints(monkeypatch):
    """Stub the release and milestone endpoints: stable is 155, 157 is newest.
    """
    driver_releases = {
        'LATEST_RELEASE_STABLE': '155.0.8059.79',
        'LATEST_RELEASE_155': '155.0.8059.80',
        'LATEST_RELEASE_158': '158.0.8104.0',
        }
    milestones = [
        {'milestone': 157, 'chromium_main_branch_position': 1717349},
        {'milestone': 156, 'chromium_main_branch_position': 1706539},
        {'milestone': 155, 'chromium_main_branch_position': 1697595},
        {'milestone': 154, 'chromium_main_branch_position': 1697000},
        ]

    def fake_get(url):
        name = url.rsplit('/', 1)[-1]
        if name in driver_releases:
            return SimpleNamespace(status_code=200, text=driver_releases[name])
        content = json.dumps(milestones).encode()
        return SimpleNamespace(status_code=200, content=content)

    monkeypatch.setattr('requests.get', fake_get)
    monkeypatch.setattr('requests.head', lambda url: SimpleNamespace(status_code=200))


@pytest.mark.parametrize('version', [0, None])
def test_latest_browser_matches_stable_driver_milestone(
        version, tempdir, chrome_endpoints):
    """Verify latest pairs Chromium with the stable driver's milestone.

    Mutation: taking the newest branched milestone for latest, or comparing
    None with an int in the cache check.
    Oracle: stubbed milestones 157/156/155 and stable driver 155.x.
    """
    cx = SmartChromeContextManager(base_path=tempdir)
    release, revision = cx.get_browser_release(version)
    assert_equal(str(release), '155.0.8059.79')
    assert_equal(str(revision), '1697595')


def test_browser_release_follows_cached_driver(chrome_endpoints):
    """Verify a fresh manager pairs Chromium with the cached driver release.

    Mutation: resolving the browser release from the latest patch when a
    driver of that major is cached.
    Oracle: cached .79 against a stubbed latest patch of .80.
    """
    with mktempdir() as base_path:
        cdm = ChromeDriverManager(base_path=base_path, version=155)
        put_fake_driver(cdm._cx._driver_cache, '155.0.8059.79')
        release, _ = cdm._cx.get_browser_release(155)
        assert_equal(str(release), '155.0.8059.79')


def test_unbranched_milestone_raises_value_error(tempdir, chrome_endpoints):
    """Verify a driver version with no branched Chromium raises ValueError.

    Mutation: indexing the filtered milestones without an empty check.
    Oracle: stubbed driver 158 against milestones that stop at 157.
    """
    cx = SmartChromeContextManager(base_path=tempdir)
    with pytest.raises(ValueError):
        cx.get_browser_release(158)


def test_snapshot_search_stops_at_prior_milestone(
        tempdir, chrome_endpoints, monkeypatch):
    """Verify the snapshot search raises before reaching the prior milestone.

    Mutation: an unbounded search, which returns a milestone 154 build.
    Oracle: snapshots stubbed only at or below 154's branch position.
    """
    def fake_head(url):
        revision = int(url.split('%2F')[1])
        return SimpleNamespace(status_code=200 if revision <= 1697000 else 404)

    monkeypatch.setattr('requests.head', fake_head)
    cx = SmartChromeContextManager(base_path=tempdir)
    with pytest.raises(ValueError):
        cx.get_browser_release(0)


def test_remove_driver_removes_cached_release(chrome_endpoints):
    """Verify remove_driver removes the cached release, not the latest patch.

    Mutation: looking up the latest patch release in place of the cache.
    Oracle: cached .79 against a stubbed latest patch of .80.
    """
    with mktempdir() as base_path:
        cdm = ChromeDriverManager(base_path=base_path, version=155)
        put_fake_driver(cdm._cx._driver_cache, '155.0.8059.79')
        cdm.remove_driver()
        assert_equal(cdm._cx._driver_cache.find_release_for_version(155), None)


if __name__ == '__main__':
    pytest.main(args=['-s', __file__])
