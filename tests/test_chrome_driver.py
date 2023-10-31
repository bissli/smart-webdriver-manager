import pytest
import glob
from mock import Mock
from asserts import assert_equal, assert_not_equal, assert_in, assert_true

from pathlib import Path

from smart_webdriver_manager import ChromeDriverManager
from smart_webdriver_manager.context import SmartChromeContextManager
from smart_webdriver_manager.utils import mktempdir

from util import run_chrome_helper

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('==>')


@pytest.mark.parametrize("version", [90, 80, 70])
def test_chrome_manager_with_specific_version(version):
    logger.info("=test_chrome_manager_with_specific_version")
    with mktempdir() as tmpdir:
        driver_path = Path(ChromeDriverManager(base_path=tmpdir, version=version).get_driver())
        assert_true(driver_path.exists())
        assert_in(tmpdir, driver_path.parents)

        browser_path = Path(ChromeDriverManager(base_path=tmpdir, version=version).get_browser())
        assert_true(browser_path.exists())
        assert_in(tmpdir, browser_path.parents)


def test_chrome_manager_with_bad_version():
    logger.info("=test_chrome_manager_with_bad_version")
    with pytest.raises(ValueError) as ex:
        with mktempdir() as tmpdir:
            ChromeDriverManager(base_path=tmpdir, version=60).get_driver()
    assert_in("There is no driver for version 60", ex.value.args[0])


def test_chrome_manager_cached_driver_with_selenium():
    logger.info("=test_chrome_manager_cached_driver_with_selenium")
    with mktempdir() as tmpdir:

        cdm = ChromeDriverManager(base_path=tmpdir, version=75)
        driver_path_1 = Path(cdm.get_driver()).resolve(strict=True)
        browser_path_1 = Path(cdm.get_browser()).resolve(strict=True)
        use_data_path_1 = Path(cdm.get_browser_user_data()).resolve(strict=True)

        cdm = ChromeDriverManager(base_path=tmpdir, version=75)
        driver_path_2 = Path(cdm.get_driver()).resolve(strict=True)
        browser_path_2 = Path(cdm.get_browser()).resolve(strict=True)
        assert_equal(driver_path_1, driver_path_2)
        assert_equal(browser_path_1, browser_path_2)

        cdm = ChromeDriverManager(base_path=tmpdir, version=74)
        driver_path_3 = Path(cdm.get_driver()).resolve(strict=True)
        browser_path_3 = Path(cdm.get_browser()).resolve(strict=True)
        assert_not_equal(driver_path_1, driver_path_3)
        assert_not_equal(browser_path_1, browser_path_3)


@pytest.mark.parametrize("platform", ["Windows", "Linux", "Darwin"])
def test_can_get_driver_for_platform(platform):
    logger.info(f"=test_can_get_driver_for_platform {platform}")
    with mktempdir() as tmpdir:

        import platform as platform_

        platform_.system = Mock(return_value=platform)
        cdm = ChromeDriverManager(base_path=tmpdir, version=96)
        driver_path = Path(cdm.get_driver())
        assert_true(driver_path.exists())

        scm = SmartChromeContextManager(base_path=tmpdir)
        driver_platform = scm.driver_platform

        driver_files = {Path(f).name for f in glob.glob(f"{driver_path.parent}/*")}
        assert_equal(
            driver_files,
            {f"chromedriver_{driver_platform}.zip", f'chromedriver{".exe" if platform=="Windows" else ""}'},
        )


@pytest.mark.parametrize("platform", ["Windows", "Linux", "Darwin"])
def test_can_get_browser_for_platform(platform):
    logger.info(f"=test_can_get_browser_for_platform {platform}")
    with mktempdir() as tmpdir:

        import platform as platform_
        platform_.system = Mock(return_value=platform)
        cdm = ChromeDriverManager(base_path=tmpdir, version=96)
        browser_path = Path(cdm.get_browser())
        assert_true(browser_path.exists())

        scm = SmartChromeContextManager(base_path=tmpdir)
        browser_zip = scm.browser_zip(999999)  # see code

        browser_files = {Path(f).name for f in glob.glob(f"{browser_path.parents[1]}/*")}
        assert_equal(browser_files, {f"chrome-{browser_zip}.zip", f"chrome-{browser_zip}"})


def test_order_doesnt_matter():
    logger.info("=test_order_doesnt_matter")
    with mktempdir() as tmpdir:
        logger.info("> Driver->Browser->Data")
        cdm = ChromeDriverManager(base_path=tmpdir)
        Path(cdm.get_driver()).resolve(strict=True)
        Path(cdm.get_browser()).resolve(strict=True)
        Path(cdm.get_browser_user_data()).resolve(strict=True)
    with mktempdir() as tmpdir:
        logger.info("> Data->Browser->Driver")
        cdm = ChromeDriverManager(base_path=tmpdir)
        Path(cdm.get_browser_user_data()).resolve(strict=True)
        Path(cdm.get_browser()).resolve(strict=True)
        Path(cdm.get_driver()).resolve(strict=True)
    with mktempdir() as tmpdir:
        logger.info("> Data->Driver-Browser")
        cdm = ChromeDriverManager(base_path=tmpdir)
        Path(cdm.get_browser_user_data()).resolve(strict=True)
        Path(cdm.get_driver()).resolve(strict=True)
        Path(cdm.get_browser()).resolve(strict=True)


def test_chrome_uses_data_dir():
    logger.info("=test_chrome_uses_data_dir")
    with mktempdir() as tmpdir:
        cdm = ChromeDriverManager(base_path=tmpdir, version=95)
        driver_path = cdm.get_driver()
        browser_path = cdm.get_browser()
        user_data_dir = cdm.get_browser_user_data()
        run_chrome_helper(driver_path, browser_path, user_data_dir)


if __name__ == "__main__":
    pytest.main(args=["-s", __file__])
