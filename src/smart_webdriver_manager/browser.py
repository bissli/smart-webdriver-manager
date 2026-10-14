import logging
from abc import ABC, abstractmethod

from smart_webdriver_manager.context import SmartChromeContextManager

logger = logging.getLogger(__name__)


class BrowserManager(ABC):
    @abstractmethod
    def install(self, version: int = 0, **kwargs):
        """One of the `smart` elements. Uses `version` to determine
        which driver to install
        """


class ChromeBrowserManager(BrowserManager):
    def __init__(self, base_path=None):
        self._cx = SmartChromeContextManager(base_path)
        logger.info('Running chrome browser manager')

    def install(self, version: int = 0):
        """Path to the cached Chromium for version, downloading it if absent.

        Parameters
        ----------
        version : int, default 0
            Chrome major version. 0 means latest stable, resolved once per
            instance, so a later call on the same instance keeps that release.

        Returns
        -------
        Path
        """
        logger.debug('Fetching chromium browser')
        release, revision = self._cx.get_browser_release(version)
        return self._cx.get_browser(str(release), str(revision))
