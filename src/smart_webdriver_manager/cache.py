import datetime
import json
import logging
import os
import re
import shutil
from abc import ABCMeta, abstractmethod
from pathlib import Path

from platformdirs import PlatformDirs

logger = logging.getLogger(__name__)


from smart_webdriver_manager.utils import unpack_zip

dirs = PlatformDirs(appname='swm', roaming=True)
DEFAULT_BASE_PATH = list(dirs.iter_data_dirs())[0]


class SmartCache(metaclass=ABCMeta):
    """Shared Cache parent, controls cache behavior"""

    def __init__(self, cache_name, base_path=None):
        self._base_path = Path(base_path or DEFAULT_BASE_PATH).expanduser()
        self._cache_json_path = self._base_path.joinpath(f'{cache_name}.json')
        self._cache_base_path = self._base_path.joinpath(cache_name)

    @abstractmethod
    def get(self, typ, release, revision=None) -> Path:
        metadata = self._read_metadata()
        key = f"{typ}_{release}{'_' if revision else ''}{revision or ''}"
        if key not in metadata:
            logger.info(f'There is no {key}, {release}, {revision=} in cache')
            return
        driver_info = metadata[key]
        path = driver_info['binary_path']
        logger.info(f'{key} found in cache at path {path}')
        return Path(path)

    @abstractmethod
    def put(self, f, typ, release, revision=None) -> Path:
        path = Path(self._cache_base_path, typ, release, revision or '')
        path.mkdir(parents=True, mode=0o755, exist_ok=True)

        f = Path(f)
        zip_path = f.replace(path.joinpath(f.name))
        logger.debug('Unzipping...')
        files = unpack_zip(zip_path)

        binary = self._match_binary(files, typ)
        binary_path = Path(path, binary)
        self._write_metadata(binary_path, typ, release, revision)
        logger.info(f'{typ} has been saved in cache at path {path}')
        return binary_path

    def _match_binary(self, files: list, typ: str) -> Path:
        logger.debug(f'Matching {typ} in candidate files')
        if len(files) == 1:
            return files[0]
        for f in files:
            name = Path(f).name
            # FIXME: Mac will not return the correct app
            re_match = re.compile(r'(ium)?(.(exe|app))?$')
            if f'{re_match.sub("", name).lower()}' in f'{typ}':
                return Path(f)
        raise Exception(f"Can't get binary for {typ} among {files}")

    def _write_metadata(self, binary_path, typ, release, revision):
        metadata = self._read_metadata()
        key = f"{typ}_{release}{'_' if revision else ''}{revision or ''}"
        data = {
            key: {
                'timestamp': datetime.date.today().strftime('%m/%d/%Y'),
                'binary_path': str(binary_path),
            }
        }
        metadata.update(data)
        with open(self._cache_json_path, 'w+') as outfile:
            json.dump(metadata, outfile, indent=4)

    def _read_metadata(self):
        if Path(self._cache_json_path).exists():
            with open(self._cache_json_path, 'r') as outfile:
                return json.load(outfile)
        return {}


class DriverCache(SmartCache):
    """Driver Cache"""

    def __init__(self, driver_name, base_path=None):
        super().__init__('drivers', base_path)
        self._driver_name = driver_name

    def get(self, release):
        return super().get(self._driver_name, release)

    def put(self, f, release):
        return super().put(f, self._driver_name, release)


class BrowserCache(SmartCache):
    """Browser Cache"""

    def __init__(self, browser_name, base_path=None):
        super().__init__('browsers', base_path)
        self._browser_name = browser_name

    def get(self, release, revision=None):
        return super().get(self._browser_name, release, revision)

    def put(self, f, release, revision=None):
        return super().put(f, self._browser_name, release, revision)


class BrowserUserDataCache:
    """Browser User Data Cache"""

    def __init__(self, browser_name, base_path=None):
        self._browser_cache = BrowserCache(browser_name, base_path)

    def _calc_user_data_path(self, release, revision=None):
        browser_path = self._browser_cache.get(release, revision)
        if not browser_path:
            raise AssertionError('get_browser() not yet called')
        user_data_path = Path(*browser_path.parts[: browser_path.parts.index(release) + 1])
        user_data_path = user_data_path.joinpath('UserData')
        return user_data_path

    def get(self, release, revision=None):
        user_data_path = self._calc_user_data_path(release, revision)
        user_data_path.mkdir(mode=0o755, exist_ok=True)
        logger.info(f'Got user data {user_data_path} for {self._browser_cache._browser_name}')
        return user_data_path

    def remove(self, release, revision=None):
        user_data_path = self._calc_user_data_path(release, revision)
        if not os.path.exists(user_data_path):
            logger.warning(f'{user_data_path} does not exist')
            return
        try:
            shutil.rmtree(user_data_path, ignore_errors=False)
            logger.info(f'Removed {user_data_path}')
        except OSError as err:
            logger.exception(err)
