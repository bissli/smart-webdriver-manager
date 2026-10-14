import time
import zipfile
from pathlib import Path

import backoff
from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from smart_webdriver_manager.utils import mktempdir


@backoff.on_exception(backoff.expo, Exception, max_time=30)
def run_chrome_helper(driver_path, browser_path, user_data_dir):
    """Real driver check"""
    options = ChromeOptions()
    options.binary_location = browser_path
    options.add_argument('--headless=new')
    options.add_argument('--disable-features=MediaRouter')
    options.add_argument(f'--user-data-dir={user_data_dir}')
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.get('https://chromiumdash.appspot.com/')
        driver.find_element(By.CLASS_NAME, 'title-wrapper')
    finally:
        driver.quit()
    time.sleep(3)


def put_fake_driver(cache, release):
    """Cache a zip that unpacks to a subfolder, as Chrome for Testing zips do.
    """
    with mktempdir() as src_dir:
        zip_path = Path(src_dir, 'chromedriver-linux64.zip')
        with zipfile.ZipFile(zip_path, 'w') as archive:
            archive.writestr('chromedriver-linux64/chromedriver', b'')
            archive.writestr('chromedriver-linux64/LICENSE.chromedriver', b'')
        return cache.put(zip_path, release)
