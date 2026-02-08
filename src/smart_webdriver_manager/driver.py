import logging
from abc import ABC, abstractmethod
from functools import cache

from packaging.version import parse
from smart_webdriver_manager.context import SmartChromeContextManager

logger = logging.getLogger(__name__)


class DriverManager(ABC):
    def __init__(self, version: int | None = None, base_path: str = None):
        """
        base_path: location on system to store browsers and drivers. Defaults to platformdirs.
        version: driver (browser) version. None or 0 implies latest version.
        """
        self._version = version or 0
        self._base_path = base_path
        logger.info('Running driver manager')

    @abstractmethod
    def get_driver(self) -> str:
        pass

    @abstractmethod
    def get_browser(self) -> str:
        pass

    @abstractmethod
    def get_browser_user_data(self) -> str:
        pass

    @abstractmethod
    def remove_browser_user_data(self):
        pass


class ChromeDriverManager(DriverManager):

    def __init__(self, version: int | None = None, base_path: str = None):
        """
        base_path: location on system to store browsers and drivers. Defaults to platformdirs.
        version: driver (browser) version. None or 0 implies latest version.
        """
        super().__init__(version or 0, base_path)
        self._cx = SmartChromeContextManager(self._base_path)

    @cache
    def get_driver(self):
        """Smart lookup for current driver version
        - chromedriver version will always be <= latest chromium browser
        """
        if self._version >= 1:
            cached_release = self._cx._driver_cache.find_release_for_version(
                self._version)
            if cached_release:
                self._cx._release_map[self._version] = parse(cached_release)
                driver_path = self._cx.get_driver(cached_release)
                return str(driver_path)
        driver_release = self._cx.get_driver_release(self._version)
        driver_path = self._cx.get_driver(str(driver_release))
        return str(driver_path)

    @cache
    def _get_browser_release_info(self):
        return self._cx.get_browser_release(self._version)

    @cache
    def get_browser(self):
        browser_release, browser_revision = self._get_browser_release_info()
        browser_path = self._cx.get_browser(str(browser_release), str(browser_revision))
        return str(browser_path)

    def get_browser_user_data(self):
        self.get_browser()
        browser_release, browser_revision = self._get_browser_release_info()
        user_data_path = self._cx.get_browser_user_data(str(browser_release), str(browser_revision))
        return str(user_data_path)

    def remove_driver(self) -> None:
        """Remove the cached driver for the current version.
        """
        driver_release = self._cx.get_driver_release(self._version)
        self._cx.remove_driver(str(driver_release))

    def remove_browser(self) -> None:
        """Remove the cached browser for the current version.
        """
        browser_release, browser_revision = self._get_browser_release_info()
        self._cx.remove_browser(str(browser_release), str(browser_revision))

    def clear_cache(self) -> None:
        """Remove all cached drivers and browsers.
        """
        self._cx.clear_cache()

    def remove_browser_user_data(self):
        self.get_browser()
        browser_release, browser_revision = self._get_browser_release_info()
        self._cx.remove_browser_user_data(str(browser_release), str(browser_revision))
