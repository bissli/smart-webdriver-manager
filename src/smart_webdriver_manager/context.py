import json
import logging
import platform
import re
from abc import ABC, abstractmethod
from functools import cache
from pathlib import Path

import backoff
import requests
from packaging.version import Version, parse
from smart_webdriver_manager.cache import DEFAULT_BASE_PATH, BrowserCache
from smart_webdriver_manager.cache import BrowserUserDataCache, DriverCache
from smart_webdriver_manager.utils import download_file
from smart_webdriver_manager.utils import url_path_join as urljoin

logger = logging.getLogger(__name__)


class SmartContextManager(ABC):
    def __init__(self, browser_name, base_path=None):
        self._base_path = base_path or DEFAULT_BASE_PATH
        self._browser_name = browser_name
        self._driver_name = self._browser_to_driver()
        self._driver_cache = DriverCache(self._driver_name, base_path)

    @property
    def driver_platform(self):
        return {
            'Windows': 'win32',
            'Linux': 'linux64',
            'Darwin': 'mac64',
        }.get(platform.system())

    @property
    def browser_platform(self):
        return {
            'Windows': 'Win_x64',
            'Linux': 'Linux_x64',
            'Darwin': 'Mac',
        }.get(platform.system())

    @abstractmethod
    def get_driver_release(self, version: int = 0) -> Version:
        """Translate the version to a release
        """

    @abstractmethod
    def get_browser_release(self, version: int = 0) -> tuple[Version, Version]:
        """Translate the version to a release
        """

    @abstractmethod
    def get_browser_user_data(self, version: int = 0) -> str:
        pass

    @abstractmethod
    def get_driver(self, release: str) -> str:
        pass

    @abstractmethod
    def get_browser(self, release: str, revision: str = None) -> str:
        pass

    def _browser_to_driver(self):
        if re.search(r'chrom|goog', self._browser_name, re.I):
            return 'chromedriver'
        raise NotImplementedError('Other browsers are not available')


CHROME_BROWSER_SNAPSHOT_REPO = urljoin('https://www.googleapis.com/',
                                       'download/storage/v1/b/',
                                       'chromium-browser-snapshots')
CHROMEDRIVER_114_AND_BELOW_REPO = 'https://chromedriver.storage.googleapis.com/'
CHROMEDRIVER_115_AND_ABOVE_REPO = 'https://googlechromelabs.github.io/chrome-for-testing/'
CHROMEDRIVER_115_AND_ABOVE_REPO_DL ='https://storage.googleapis.com/chrome-for-testing-public/'


class SmartChromeContextManager(SmartContextManager):
    """Downloads and saves chromedriver packages
    - Manages chromedriver
    - Optionally also manages Chromium

    Chromedriver LATEST_RELEASE gives the latest version of Chromedriver, ie 96
    But if downloading Chromium, the latest is 98, not supported by Chromedriver 96
    """

    def __init__(self, base_path=None):
        super().__init__('chrome', base_path)
        self._browser_cache = BrowserCache(self._browser_name, self._base_path)
        self._browser_user_data_cache = BrowserUserDataCache(self._browser_name, self._base_path)
        self._release_map = {}

    @cache
    def browser_zip(self, revision: str):
        win = lambda x: 'win' if x > 591479 else 'win32'  # naming changes (roughly v70)
        return {
            'Windows': win(int(revision)),
            'Linux': 'linux',
            'Darwin': 'mac',
        }.get(platform.system())

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_time=30)
    def get_driver_release(self, version: int = 0) -> Version:
        """Find the latest driver version corresponding to the browser release

        from https://chromedriver.chromium.org/ ...

        Starting with M115 the latest Chrome + ChromeDriver releases per
        release channel (Stable, Beta, Dev, Canary) are available at the
        `Chrome for Testing availability dashboard`.
        """
        logger.debug(f'Getting {self._driver_name} version for {version or "Latest"}')
        if 1 <= (version or 0) < 115:
            url = f'{CHROMEDRIVER_114_AND_BELOW_REPO}LATEST_RELEASE_{version}'
        else:
            url = f'{CHROMEDRIVER_115_AND_ABOVE_REPO}LATEST_RELEASE_{version or "STABLE"}'
        resp = requests.get(url)
        if resp.status_code == 404:
            raise ValueError(f'There is no driver for version {version}')
        if resp.status_code != 200:
            raise ValueError(
                f'response body:\n{resp.json()}\n'
                f'request url:\n{resp.request.url}\n'
                f'response headers:\n{dict(resp.headers)}\n'
            )
        release = parse(resp.text.rstrip())
        self._release_map[version] = release
        return release

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_time=30)
    def get_browser_release(self, version: int = 0) -> tuple[Version, Version]:
        """Find latest corresponding chromium relese to specified/latest chromedriver
        """
        release = self._release_map.get(version, self.get_driver_release(version))

        revision_url = urljoin('https://chromiumdash.appspot.com',
                               'fetch_milestones?only_branched=true')
        revisions = json.loads(requests.get(revision_url).content.decode())
        if not version:
            revisions = sorted(revisions, key=lambda x: int(x['milestone']), reverse=True)
        else:
            revisions = [d for d in revisions if int(d['milestone']) == version]
        revision = int(revisions[0]['chromium_main_branch_position'])

        while True:
            logger.debug(f'Trying revision {revision} ... ')
            chromium_zip = f'{revision}-chrome-{self.browser_zip(revision)}.zip'
            chromium_url = urljoin(CHROME_BROWSER_SNAPSHOT_REPO, 'o', (
                f'{self.browser_platform}%2F'
                f'{revision}%2Fchrome-'
                f'{self.browser_zip(revision)}.zip'
                '?alt=media'
                ))
            logger.debug(f'Getting {chromium_zip} from {chromium_url}')
            status_code = requests.head(chromium_url).status_code
            if status_code == 200:
                break
            revision -= 1

        logger.debug(f'Chromedriver version {version} supports chromium {release=} {revision=}')
        return release, parse(str(revision))

    def get_driver(self, release: str) -> Path:
        """Get driver zip for version
        """
        binary_path = self._driver_cache.get(release)
        if binary_path:
            logger.debug(f'Already have latest version for release {release}')
            return binary_path
        version = int(release.split('.')[0] or 0)
        if 1 <= version < 115:
            zip_file = f'chromedriver_{self.driver_platform}.zip'
            chromedriver_url = urljoin(CHROMEDRIVER_114_AND_BELOW_REPO, release, zip_file)
        else:
            zip_file = f'chromedriver-{self.driver_platform}.zip'
            chromedriver_url = urljoin(CHROMEDRIVER_115_AND_ABOVE_REPO_DL, release,
                                       self.driver_platform, zip_file)
        logger.debug(f'Getting {zip_file} from {chromedriver_url}')
        with download_file(chromedriver_url) as f:
            binary_path = self._driver_cache.put(f, release)
            logger.debug(f'Downloaded {zip_file}')

        return binary_path

    def get_browser(self, release: str, revision: str = None) -> Path:
        """An extension of `get_supported_chromium_revision`
        """
        binary_path = self._browser_cache.get(release, revision)
        if binary_path:
            logger.debug(f'Already have latest version for {release=} {revision=}')
            return binary_path

        chromium_zip = f'{revision}-chrome-{self.browser_zip(revision)}.zip'
        chromium_url = urljoin(CHROME_BROWSER_SNAPSHOT_REPO, 'o', (
            f'{self.browser_platform}%2F'
            f'{revision}%2Fchrome-'
            f'{self.browser_zip(revision)}.zip'
            '?alt=media'
            ))
        logger.debug(f'Getting {chromium_zip} from {chromium_url}')

        with download_file(chromium_url) as f:
            binary_path = self._browser_cache.put(f, release, revision)
            logger.debug(f'Downloaded {chromium_zip}')

        return binary_path

    def get_browser_user_data(self, release: str, revision: str) -> Path:
        """Get browser user data dir that matches release version
        - revision is ignored (data dir is same level as major version)
        """
        return str(self._browser_user_data_cache.get(release, revision))

    def remove_browser_user_data(self, release: str, revision: str):
        """Remove UserData folder matching release and revision
        """
        self._browser_user_data_cache.remove(release, revision)
