import re
import requests
import platform
import backoff
import json

from abc import ABCMeta, abstractmethod
from packaging.version import Version, parse
from pathlib import Path

from smart_webdriver_manager.cache import (
    DriverCache,
    BrowserCache,
    BrowserUserDataCache,
    DEFAULT_BASE_PATH,
)
from smart_webdriver_manager.utils import download_file

from . import logger


class SmartContextManager(metaclass=ABCMeta):
    def __init__(self, browser_name, base_path=None):
        self._base_path = base_path or DEFAULT_BASE_PATH
        self._browser_name = browser_name
        self._driver_name = self._browser_to_driver()
        self._driver_cache = DriverCache(self._driver_name, base_path)

    @property
    def driver_platform(self):
        return {"Windows": "win32", "Linux": "linux64", "Darwin": "mac64"}.get(platform.system())

    @property
    def browser_platform(self):
        return {
            "Windows": "Win_x64",
            "Linux": "Linux_x64",
            "Darwin": "Mac",
        }.get(platform.system())

    @abstractmethod
    def get_driver_release(self, version: int = 0) -> Version:
        """Translate the version to a release"""
        pass

    @abstractmethod
    def get_browser_release(self, version: int = 0) -> (Version, Version):
        """Translate the version to a release"""
        pass

    @abstractmethod
    def get_browser_user_data(self, version: int = 0) -> str:
        pass

    @abstractmethod
    def get_driver(self, release) -> str:
        pass

    @abstractmethod
    def get_browser(self, release, revision=None) -> str:
        pass

    def _browser_to_driver(self):
        if re.search(r"chrom|goog", self._browser_name, re.I):
            return "chromedriver"
        raise NotImplementedError("Other browers are not avaialble")


class SmartChromeContextManager(SmartContextManager):
    """Downloads and saves chromedriver packages
    - Manages chromedriver
    - Optionally also manages Chromium

    Chromedriver LATEST_RELEASE gives the latest version of Chromedriver, ie 96
    But if downloading Chromium, the latest is 98, not supported by Chromedriver 96

    """

    def __init__(self, base_path=None):
        super().__init__("chrome", base_path)
        self._browser_cache = BrowserCache(self._browser_name, self._base_path)
        self._browser_user_data_cache = BrowserUserDataCache(self._browser_name, self._base_path)

        self.url_driver_repo = "https://chromedriver.storage.googleapis.com"
        self.url_driver_repo_latest = f"{self.url_driver_repo}/LATEST_RELEASE"

        url_browser_repo = "https://www.googleapis.com/download/storage/v1/b/chromium-browser-snapshots/o"
        self.url_browser_zip = f"{url_browser_repo}/{self.browser_platform}%2F{{}}%2Fchrome-{{}}.zip?alt=media"

    def browser_zip(self, revision: str):
        win = lambda x: "win" if x > 591479 else "win32"  # naming changes (roughly v70)
        return {
            "Windows": win(int(revision)),
            "Linux": "linux",
            "Darwin": "mac",
        }.get(platform.system())

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_time=30)
    def get_driver_release(self, version: int = 0) -> Version:
        """Find the latest driver version corresponding to the browser release"""
        logger.debug(f"Getting {self._driver_name} version for {version}")
        _version = f"_{version}" if version else ""
        url = f"{self.url_driver_repo_latest}{_version}"
        resp = requests.get(url)
        if resp.status_code == 404:
            raise ValueError(f"There is no driver for version {version}")
        elif resp.status_code != 200:
            raise ValueError(
                f"response body:\n{resp.json()}\n"
                f"request url:\n{resp.request.url}\n"
                f"response headers:\n{dict(resp.headers)}\n"
            )
        return parse(resp.text.rstrip())

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_time=30)
    def get_browser_release(self, version: int = 0) -> (Version, Version):
        """Find latest corresponding chromium relese to specified/latest chromedriver
        """
        release = self.get_driver_release(version)

        revision_url = 'https://chromiumdash.appspot.com/fetch_milestones?only_branched=true'
        revisions = json.loads(requests.get(revision_url).content.decode())
        if not version:
            revisions = sorted(revisions, key=lambda x: int(x['milestone']), reverse=True)
        else:
            revisions = [d for d in revisions if int(d['milestone']) == version]
        revision = int(revisions[0]['chromium_main_branch_position'])

        while 1:
            logger.debug(f"Trying revision {revision} ... ")
            browser_zip = self.browser_zip(revision)
            url_browser_zip = self.url_browser_zip.format(revision, browser_zip)
            status_code = requests.head(url_browser_zip).status_code
            if status_code == 200:
                break
            revision -= 1

        logger.debug(f"Chromedriver version {version} supports chromium {release=} {revision=}")
        return release, parse(str(revision))

    def get_driver(self, release: str) -> Path:
        """Get driver zip for version"""
        binary_path = self._driver_cache.get(release)
        if binary_path:
            logger.debug(f"Already have latest version for release {release}")
            return binary_path

        zip_file = f"chromedriver_{self.driver_platform}.zip"
        url_zip = f"{self.url_driver_repo}/{release}/{zip_file}"
        logger.debug(f"Getting {zip_file} from {url_zip}")

        with download_file(url_zip) as f:
            binary_path = self._driver_cache.put(f, release)
            logger.debug(f"Downloaded {zip_file}")

        return binary_path

    def get_browser(self, release: str, revision: str = None) -> Path:
        """An extension of `get_supported_chromium_revision`"""
        binary_path = self._browser_cache.get(release, revision)
        if binary_path:
            logger.debug(f"Already have latest version for {release=} {revision=}")
            return binary_path

        browser_zip = self.browser_zip(revision)
        zip_file = f"{revision}-chrome-{browser_zip}.zip"
        url_zip = self.url_browser_zip.format(revision, browser_zip)
        logger.debug(f"Getting {zip_file} from {url_zip}")

        with download_file(url_zip) as f:
            binary_path = self._browser_cache.put(f, release, revision)
            logger.debug(f"Downloaded {zip_file}")

        return binary_path

    def get_browser_user_data(self, release: str, revision: str) -> Path:
        """Get browser user data dir that matches release version
        - revision is ignored (data dir is same level as major version)
        """
        data_dir_path = self._browser_user_data_cache.get(release, revision)

        return str(data_dir_path)
