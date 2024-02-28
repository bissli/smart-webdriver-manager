import pytest
from smart_webdriver_manager import ChromeDriverManager
from util import run_chrome_helper


@pytest.mark.skip()
def test_install():
    """Set up latest chromium browser/driver on local"""
    cdm = ChromeDriverManager(version=75)
    browser_path = cdm.get_browser()
    driver_path = cdm.get_driver()
    user_data_path = cdm.get_browser_user_data()
    run_chrome_helper(driver_path, browser_path, user_data_path)

    cdm = ChromeDriverManager(version=91)
    browser_path = cdm.get_browser()
    driver_path = cdm.get_driver()
    user_data_path = cdm.get_browser_user_data()
    run_chrome_helper(driver_path, browser_path, user_data_path)

    cdm = ChromeDriverManager(version=94)
    browser_path = cdm.get_browser()
    driver_path = cdm.get_driver()
    user_data_path = cdm.get_browser_user_data()
    run_chrome_helper(driver_path, browser_path, user_data_path)

    cdm = ChromeDriverManager()
    browser_path = cdm.get_browser()
    driver_path = cdm.get_driver()
    user_data_path = cdm.get_browser_user_data()
    run_chrome_helper(driver_path, browser_path, user_data_path)


if __name__ == '__main__':
    pytest.main(args=['-s', __file__])
