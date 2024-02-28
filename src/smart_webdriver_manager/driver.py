import logging
from abc import ABCMeta, abstractmethod
from functools import cache

from smart_webdriver_manager.context import SmartChromeContextManager

logger = logging.getLogger(__name__)


class DriverManager(metaclass=ABCMeta):
    def __init__(self, version, base_path):
        self._base_path = base_path
        self._version = version
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

    # @abstractmethod
    # def remove():
    # pass


class ChromeDriverManager(DriverManager):

    __called_driver__ = False
    __called_browser__ = False

    def __init__(self, version: int = 0, base_path=None):
        super().__init__(version, base_path)
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

    @cache
    def get_browser_user_data(self):
        if not self.__called_browser__:
            self.get_browser()
        browser_release, browser_revision = self._get_browser_helper()
        user_data_path = self._cx.get_browser_user_data(str(browser_release), str(browser_revision))
        return str(user_data_path)

    # def _forfun(self):
        # # test and remove me
        # return [
            # f'driver stats:  {self.get_driver.cache_info()}',
            # f'browser stats: {self.get_browser.cache_info()}',
            # f'datadir stats: {self.get_user_data.cache_info()}',
            # ]

    # def remove(self):
        # """Needs to remove all the instances from cache (force kill if running)
        # """
        # self.get_driver.cache_clear()
        # self.get_browser.cache_clear()
        # self.get_user_data.cache_clear()
        # self._get_browser_helper.cache_clear()
        # self.__called_driver__ = False
        # self.__called_browser__ = False
        # # now remove things
