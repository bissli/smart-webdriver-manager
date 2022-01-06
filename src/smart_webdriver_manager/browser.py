from abc import ABCMeta, abstractmethod
from smart_webdriver_manager.context import SmartChromeContextManager

from . import logger


class BrowserManager(metaclass=ABCMeta):

    @abstractmethod
    def install(self, version:int=0, **kwargs):
        """One of the `smart` elements. Uses `version` to determine
        which driver to install
        """
        pass


class ChromeBrowserManager(BrowserManager):

    def __init__(self, base_path=None):
        self._cx = SmartChromeContextManager(base_path)
        logger.info("Running chrome browser manager")

    def install(self, version:int=0):
        """Smart lookup for current browser version
        """
        logger.debug(f"Fetching chromium browser")
        revision = self._cx.find_supported_chromium_revision(version)
        return self._cx.fetch_browser(revision)
