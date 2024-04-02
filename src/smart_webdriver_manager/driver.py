import logging
from abc import ABCMeta, abstractmethod
from functools import cache

from smart_webdriver_manager.context import SmartChromeContextManager

logger = logging.getLogger(__name__)


class DriverManager(metaclass=ABCMeta):
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

    __called_driver__ = False
    __called_browser__ = False

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
        driver_release = self._cx.get_driver_release(self._version)
        driver_path = self._cx.get_driver(str(driver_release))
        self.__called_driver__ = True
        if not self.__called_browser__:
            self.get_browser()
        return str(driver_path)

    @cache
    def _get_browser_helper(self):
        if not self.__called_driver__:
            self.get_driver()
        return self._cx.get_browser_release(self._version)

    @cache
    def get_browser(self):
        self.__called_browser__ = True
        browser_release, browser_revision = self._get_browser_helper()
        browser_path = self._cx.get_browser(str(browser_release), str(browser_revision))
        return str(browser_path)

    def get_browser_user_data(self):
        if not self.__called_browser__:
            self.get_browser()
        browser_release, browser_revision = self._get_browser_helper()
        user_data_path = self._cx.get_browser_user_data(str(browser_release), str(browser_revision))
        return str(user_data_path)

    def remove_browser_user_data(self):
        if not self.__called_browser__:
            self.get_browser()
        browser_release, browser_revision = self._get_browser_helper()
        self._cx.remove_browser_user_data(str(browser_release), str(browser_revision))
