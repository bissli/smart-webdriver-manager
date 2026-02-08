import glob
import logging
from pathlib import Path

import pytest
from asserts import assert_equal, assert_false, assert_in, assert_not_equal
from asserts import assert_true
from unittest.mock import Mock
from smart_webdriver_manager import ChromeDriverManager
from smart_webdriver_manager.context import SmartChromeContextManager
from smart_webdriver_manager.utils import mktempdir
from util import run_chrome_helper

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
def test_can_get_driver_for_platform(platform, version, tempdir):
    logger.info(f'=test_can_get_driver_for_platform {platform}')

    import platform as platform_
    platform_.system = Mock(return_value=platform)
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
def test_can_get_browser_for_platform(platform, version, tempdir):
    logger.info(f'=test_can_get_browser_for_platform {platform} {version}')

    import platform as platform_
    platform_.system = Mock(return_value=platform)
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


if __name__ == '__main__':
    pytest.main(args=['-s', __file__])
