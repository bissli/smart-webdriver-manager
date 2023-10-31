import time
import backoff

from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


@backoff.on_exception(backoff.expo, Exception, max_time=30)
def run_chrome_helper(driver_path, browser_path, user_data_dir):
    """Real driver check"""
    options = ChromeOptions()
    options.binary_location = browser_path
    options.headless = True
    options.add_argument(f"--user-data-dir={user_data_dir}")
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.get('https://chromiumdash.appspot.com/')
        driver.find_element(By.CLASS_NAME, "title-wrapper")
    finally:
        driver.quit()
    time.sleep(3)
