import pytest
from smart_webdriver_manager import ChromeDriverManager
from smart_webdriver_manager.utils import mktempdir
from util import run_chrome_helper


@pytest.mark.parametrize('version', [94, None])
def test_install(version):
    """Verify a version's downloaded driver and browser launch together.

    Mutation: pairing the driver with a browser of another major, or a
    broken pre-115 driver download URL.
    Oracle: chromedriver refuses a session when the browser major differs.
    """
    with mktempdir() as base_path:
        cdm = ChromeDriverManager(version=version, base_path=base_path)
        browser_path = cdm.get_browser()
        driver_path = cdm.get_driver()
        user_data_path = cdm.get_browser_user_data()
        run_chrome_helper(driver_path, browser_path, user_data_path)


if __name__ == '__main__':
    pytest.main(args=['-s', __file__])
