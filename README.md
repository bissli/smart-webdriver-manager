Smart Webdriver Manager
=======================
[![PyPI](https://img.shields.io/pypi/v/smart-webdriver-manager.svg)](https://pypi.org/project/smart-webdriver-manager)
[![Supported Python Versions](https://img.shields.io/pypi/pyversions/smart-webdriver-manager.svg)](https://pypi.org/project/smart-webdriver-manager/)

A smart webdriver manager. Inspired by [webdriver_manager](https://github.com/SergeyPirogov/webdriver_manager/) and [chromedriver-binary-auto](https://github.com/danielkaiser/python-chromedriver-binary).

Unlike other managers, this module manages the driver, browser, and data directory independently of the system installed browser.

The manager requires only a specified browser version (i.e. Chromium 117, 118, 120, etc.). It manages the remaining components.

These are then cached for future use in the user-specified or system-default directory. In other words:

```python
for version in [0, 75, 80, 95, 96]: # 0 -> latest
  # auto-fetch and configure all the needed components and run the automation
```


Supported Driver/Platform
--------------------------

|                           | **Chromium** | **Firefox** |
| ------------------------- | ------------ | ----------- |
| **Windows**               | x            | -           |
| **Linux**                 | x            | -           |
| **macOS (Apple Silicon)** | x            | -           |

Installation
------------

```bash
pip install smart-webdriver-manager
```

Examples
--------

### Basic Usage

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

The components themselves are modular. You can use the driver or the browser independently.
However, both the driver and browser are fetched together. If you only need a driver then other modules may be better suited.

What's really nice is the work required to update automation is now minimal. Just decrement back if the automation doesn't work.
No need to install/uninstall browsers when verifying versions.

### Multiple Versions

```python
from smart_webdriver_manager import ChromeDriverManager

for version in [117, 118, 120, 0]:  # 0 -> latest
    cdm = ChromeDriverManager(version=version)
    driver_path = cdm.get_driver()
    browser_path = cdm.get_browser()
    # run automation with this version ...
```

### Custom Cache Directory

```python
from smart_webdriver_manager import ChromeDriverManager

cdm = ChromeDriverManager(version=120, base_path='/tmp/my-cache')
driver_path = cdm.get_driver()
```

### Cache Management

```python
from smart_webdriver_manager import ChromeDriverManager

cdm = ChromeDriverManager(version=120)

# Remove cached driver for this version
cdm.remove_driver()

# Remove cached browser for this version
cdm.remove_browser()

# Remove user data directory for this version
cdm.remove_browser_user_data()

# Remove all cached drivers and browsers
cdm.clear_cache()
```

macOS Notes
-----------

When running Chromium on macOS, the browser may trigger a **"Do you want to allow this app to find devices on your local network?"** popup. To suppress this, add the following Chrome option:

```python
options.add_argument('--disable-features=MediaRouter')
```

This is already included in the basic usage example above.

API Reference
-------------

### `ChromeDriverManager(version=None, base_path=None)`

| Parameter   | Type            | Default | Description                                             |
| ----------- | --------------- | ------- | ------------------------------------------------------- |
| `version`   | `int` or `None` | `None`  | Browser version (e.g. 117, 120). `None` or `0` = latest |
| `base_path` | `str` or `None` | `None`  | Cache directory. `None` = system default                |

### Methods

| Method                       | Returns | Description                                         |
| ---------------------------- | ------- | --------------------------------------------------- |
| `get_driver()`               | `str`   | Download/cache chromedriver and return its path     |
| `get_browser()`              | `str`   | Download/cache Chromium browser and return its path |
| `get_browser_user_data()`    | `str`   | Return path to user data directory for this version |
| `remove_driver()`            | `None`  | Remove cached driver for the current version        |
| `remove_browser()`           | `None`  | Remove cached browser for the current version       |
| `remove_browser_user_data()` | `None`  | Remove user data directory for the current version  |
| `clear_cache()`              | `None`  | Remove all cached drivers and browsers              |

Technical Layout
----------------

Some module definitions:

- `Version`: main browser version, ie Chrome 95
- `Release`: subversion: ie Chrome 95.01.1121
- `Revision`: browser-only, snapshots within a release

To clarify how the module works, below is the cache directory illustrated:

1. For browsers with revisions, we return the latest revision to the browser.
2. For driver with releases, we return the latest releases to the driver corresponding to the browser.
3. A user data directory is aligned with the release.

For example if the user requests chromedriver v96, revision 92512 will be returned for the browser and 96.1.85.111 for the driver.

```
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
        chromium/ [macOS]
            125.0.6422.141/
                1287718/
                    chrome-mac/
                        Chromium.app/
                            Contents/MacOS/Chromium
                    1287718-chrome-mac.zip
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
```

The system default directory for the cache is as follows:

- `Windows`: ~/appdata/roaming/swm
- `Linux`:   ~/.local/share/swm
- `macOS`:   ~/Library/Application Support/swm

Development
-----------

There are two ways to run local tests

```bash
pip install -U pip poetry tox
git clone https://github.com/bissli/smart-webdriver-manager.git && cd smart-webdriver-manager
tox
```

```bash
pip install -U pip poetry
git clone https://github.com/bissli/smart-webdriver-manager.git && cd smart-webdriver-manager
poetry install --with test
poetry shell
pytest
```

Contributing
------------

Active contributions are welcome (collaboration). Please open a PR for features or bug fixes.
