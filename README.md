Smart Webdriver Manager
=======================
[![PyPI](https://img.shields.io/pypi/v/smart-webdriver-manager.svg)](https://pypi.org/project/smart-webdriver-manager)
[![Supported Python Versions](https://img.shields.io/pypi/pyversions/smart-webdriver-manager.svg)](https://pypi.org/project/smart-webdriver-manager/)

A smart webdriver manager. Inspired by [webdriver_manager](https://github.com/SergeyPirogov/webdriver_manager/) and [chromedriver-binary-auto](https://github.com/danielkaiser/python-chromedriver-binary).

Unlike other managers, this module provides a version-synchronized context for the driver, the browser, and the data directory.

These are then cached for future use in the user-specified directory (or default).

Currently Linux and Windows are fully tested. (See TODO)

Examples
--------

```python
pip install smart-webdriver-manager
```

```python
import os
from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.service import Service
from smart_webdriver_manager import ChromeDriverManager

version = os.getenv('MY_ENVIRONMENTAL_VARIABLE')
cdm = ChromeDriverManager(version=version)

driver_path = cdm.get_driver()
browser_path = cdm.get_browser()
user_data_path = cdm.get_browser_user_data()

options = ChromeOptions()
options.binary_location = browser_path
options.add_argument(f'--user-data-dir={user_data_path}')
service = Service(executable_path=driver_path)
driver = webdriver.Chrome(service=service, options=options)
try:
    driver.get("http://google.com")
finally:
    driver.quit()
```

While it is more verbose than other managers, we can run parallel tests across supported versions.

```python
for version in [0, 75, 80, 95, 96]: # 0 -> latest
  # ... same code as above, replacing version
```

The compoenents themselves are modular. You can use the the driver or the browser independently.
However, both the driver and browser are installed together. If you only need a driver then other modules may be better suited.

Whats really nice is the work required to update tests is now minimal. Just decrement back if the tests don't work.
No need to install/uninstall browsers when verifying versions.

Development
-----------

There are two ways to run local tests

```python
pip install -U pip poetry tox
git clone https://github.com/bissli/smart-webdriver-manager.git
cd smart-webdriver-manager
tox
```

```python
pip install -U pip poetry
git clone https://github.com/bissli/smart-webdriver-manager.git
cd smart-webdriver-manager
poetry install
poetry shell
pip install pytest mock selenium asserts
pytest
```

Technical Layout
----------------

Some module definitions:

- `Version`: main browser version, ie Chrome 95
- `Release`: subversion: ie Chrome 95.01.1121
- `Revision`: browser-only, snapshots within a release

To clarify how the module works, below is the cache directory illustrated:

1. For browsers with revisions, we return the latest revision to the browser.
2. For driver with releases, we return the latest releases to the driver corresponding to the browser.
3. A user data directory is aligned with the release (see TODO)

For example if the user requests chromedriver v96, revision 92512 will be returned for the browser and 96.1.85.111 for the driver.

```python
"""Cache structure
swm/
    browsers/
        chromium/ [linux]
            96.1.85.54/
                929511/
                    chrome-linux/
                        chrome
                        ...
                    929511-chrome-linux.zip
                929512/
                    chrome-linux/
                        chrome
                        ...
                    929512-chrome-linux.zip
            user-data/
                ...
        firefox/
          ...
    drivers/
        chromedriver/ [windows]
            96.1.85.54/
                driver.zip
                chromedriver.exe
            96.1.85.111/
                driver.zip
                chromedriver.exe
        geckodriver/ [linux]
            0.29.8/
                driver.zip
                geckodriver
            0.29.9/
                driver.zip
                geckodriver
    browsers.json
    drivers.json
"""
```

The default directory for the cache is as follows:

- `Windows`: ~/appdata/roaming/swm
- `Linux`:   ~/.local/share/swm
- `Mac`:  ~/Library/Application Support/swm

TODO
----
- [ ] Complete support for Mac. Parse .app directory and create workaround for Gatekeeper.
- [ ] Complete the cache clear/remove methods. Write methods to delete the data directory or parts of the cache.
- [ ] Add Firefox as another supported platform. Current support is limited to Chromium/Chromedriver.
- [ ] Ability to recover if part of the cache is missing (ie a browser not there but browsers.json says so) (check path exists)
- [x] Change the user data directory to fall under the major version, not release (see illustration above).
- [x] Decide whether symlinks have value, remove code if not. (REMOVED)
- [x] Migrate off omahaproxy.appspot.com (discontinued). See https://groups.google.com/a/chromium.org/g/chromium-dev/c/uH-nFrOLWtE?pli=1

Contributing
------------

Active contributions are welcome (collaboration). Please open a PR for features or bug fixes.
