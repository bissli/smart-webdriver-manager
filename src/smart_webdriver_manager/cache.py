import backoff
import datetime
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from filelock import FileLock
from platformdirs import PlatformDirs
from smart_webdriver_manager.utils import unpack_zip

logger = logging.getLogger(__name__)


dirs = PlatformDirs(appname='swm', roaming=True)
DEFAULT_BASE_PATH = list(dirs.iter_data_dirs())[0]


class SmartCache(ABC):
    """Shared Cache parent, controls cache behavior"""

    def __init__(self, cache_name, base_path=None):
        self._base_path = Path(base_path or DEFAULT_BASE_PATH).expanduser()
        self._cache_json_path = self._base_path.joinpath(f'{cache_name}.json')
        self._cache_base_path = self._base_path.joinpath(cache_name)

    @abstractmethod
    def get(self, typ: str, release: str, revision: str | None = None) -> Path | None:
        metadata = self._read_metadata()
        key = f"{typ}_{release}{'_' if revision else ''}{revision or ''}"

        if key not in metadata:
            logger.info(f'There is no {key}, {release}, {revision=} in cache')
            return None

        path = Path(metadata[key]['binary_path'])
        if not path.exists():
            self._sync_cache()
            metadata = self._read_metadata()
            if key not in metadata:
                logger.info(f'There is no {key}, {release}, {revision=} in cache after sync')
                return None
            path = Path(metadata[key]['binary_path'])
            if not path.exists():
                logger.info(f'{key} binary not found at {path} after cache sync')
                return None

        logger.info(f'{key} found in cache at path {path}')
        return path

    @abstractmethod
    def put(self, f: Path, typ: str, release: str, revision: str | None = None) -> Path:
        path = Path(self._cache_base_path, typ, release, revision or '')
        path.mkdir(parents=True, mode=0o755, exist_ok=True)

        f = Path(f)
        zip_path = f.replace(path.joinpath(f.name))
        logger.debug('Unzipping...')
        files = unpack_zip(zip_path)

        if platform.system() == 'Darwin':
            subprocess.run(['xattr', '-cr', str(path)], check=False, capture_output=True)

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
            if f.endswith('/'):
                continue
            name = Path(f).name
            re_match = re.compile(r'(ium)?(.(exe|app))?$')
            if f'{re_match.sub("", name).lower()}' in f'{typ}':
                return Path(f)
        raise Exception(f"Can't get binary for {typ} among {files}")

    def remove(self, typ: str, release: str, revision: str | None = None) -> None:
        """Remove a cached entry from filesystem and metadata.
        """
        key = f"{typ}_{release}{'_' if revision else ''}{revision or ''}"
        path = Path(self._cache_base_path, typ, release, revision or '')
        if path.exists():
            shutil.rmtree(path, ignore_errors=False)
        with self._lock():
            metadata = self._read_metadata()
            metadata.pop(key, None)
            self._atomic_write_metadata(metadata)

    def clear(self) -> None:
        """Remove all cached entries and metadata.
        """
        if self._cache_base_path.exists():
            shutil.rmtree(self._cache_base_path, ignore_errors=False)
        with self._lock():
            if self._cache_json_path.exists():
                self._cache_json_path.unlink()

    def _rebuild_metadata_from_filesystem(self) -> dict:
        """Rebuild JSON metadata by scanning the actual filesystem structure.

        Treats the filesystem as the source of truth for cache contents.
        Scans the cache directory structure and recreates metadata entries
        for all valid binaries found on disk.

        Returns
            Dictionary containing rebuilt metadata based on filesystem contents
        """
        metadata = {}

        if not self._cache_base_path.exists():
            return metadata

        for typ_dir in self._cache_base_path.iterdir():
            if not typ_dir.is_dir():
                continue

            typ = typ_dir.name

            for release_dir in typ_dir.iterdir():
                if not release_dir.is_dir():
                    continue

                release = release_dir.name

                for item in release_dir.iterdir():
                    if item.is_dir() and item.name:
                        revision = item.name
                        binary_path = self._find_binary_in_dir(item, typ)
                        if binary_path:
                            key = f'{typ}_{release}_{revision}'
                            metadata[key] = {
                                'timestamp': datetime.date.today().strftime('%m/%d/%Y'),
                                'binary_path': str(binary_path)
                            }
                    else:
                        binary_path = self._find_binary_in_dir(release_dir, typ)
                        if binary_path:
                            key = f'{typ}_{release}'
                            metadata[key] = {
                                'timestamp': datetime.date.today().strftime('%m/%d/%Y'),
                                'binary_path': str(binary_path)
                            }
                            break

        logger.debug(f'Rebuilt metadata with {len(metadata)} entries from filesystem')
        return metadata

    def _find_binary_in_dir(self, directory: Path, typ: str) -> Path | None:
        """Find the binary file in a directory that matches the type.

        Searches for executable files in the given directory and attempts
        to match them against the expected binary type using existing
        matching logic.

        Parameters
            directory: Directory to search for binary files
            typ: Type name to match against binary files

        Returns
            Path to the binary file if found, None otherwise
        """
        try:
            files = [f for f in directory.iterdir() if f.is_file()]
            binary_name = self._match_binary([str(f) for f in files], typ)
            return Path(directory, binary_name) if binary_name else None
        except Exception:
            return None

    def _sync_cache(self) -> None:
        """Synchronize JSON metadata with filesystem state.

        Rebuilds the entire JSON metadata file based on what actually
        exists in the filesystem cache directories. This ensures the
        cache metadata stays in sync with the actual file contents.

        Notes
        -----
        - Runs under the per-cache lock and replaces the whole map. It is
          only reached from ``get`` when a recorded binary is missing, never
          on the clean cold different-version path.
        """
        with self._lock():
            rebuilt_metadata = self._rebuild_metadata_from_filesystem()
            self._atomic_write_metadata(rebuilt_metadata)
        logger.debug('Synchronized cache metadata with filesystem')

    def _lock(self) -> FileLock:
        """Return the cross-process lock guarding this cache's metadata file.

        Returns
        -------
        FileLock
            A lock bound to ``<cache_json>.lock``.

        Notes
        -----
        - Held around every metadata read-modify-write so concurrent
          processes provisioning different versions cannot corrupt the
          shared JSON.
        """
        self._base_path.mkdir(parents=True, exist_ok=True)
        return FileLock(f'{self._cache_json_path}.lock')

    def _atomic_write_metadata(self, metadata: dict) -> None:
        """Persist the metadata map atomically.

        Serializes ``metadata`` to a temporary file in the cache directory,
        fsyncs and closes it, then swaps it into place with ``os.replace`` so
        a concurrent lock-free reader always sees a complete file.

        Parameters
        ----------
        metadata : dict
            The full metadata map to persist.

        Notes
        -----
        - The temp file is closed before the replace; Windows rejects
          replacing a destination while the source handle is still open.
        - ``os.replace`` is retried on ``PermissionError`` to absorb the
          Windows case where a reader briefly holds the destination open; a
          no-op on POSIX, where the rename is atomic.
        """
        self._base_path.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=self._base_path,
            prefix=f'{self._cache_json_path.name}.',
            suffix='.tmp',
            )

        @backoff.on_exception(backoff.expo, PermissionError, max_time=10)
        def replace() -> None:
            os.replace(tmp_path, self._cache_json_path)

        try:
            with os.fdopen(fd, 'w') as outfile:
                json.dump(metadata, outfile, indent=4)
                outfile.flush()
                os.fsync(outfile.fileno())
            replace()
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _write_metadata(
        self,
        binary_path: Path,
        typ: str,
        release: str,
        revision: str | None) -> None:
        """Write a metadata entry for a cached binary.

        Parameters
        ----------
        binary_path : Path
            Path to the binary file.
        typ : str
            Type of binary (e.g. 'chromedriver', 'chrome').
        release : str
            Release version string.
        revision : str | None
            Optional revision string for the binary.

        Notes
        -----
        - The read-modify-write runs under the per-cache lock, so concurrent
          writers for different keys cannot clobber each other's entries.
        """
        key = f"{typ}_{release}{'_' if revision else ''}{revision or ''}"
        entry = {
            'timestamp': datetime.date.today().strftime('%m/%d/%Y'),
            'binary_path': str(binary_path),
            }
        with self._lock():
            metadata = self._read_metadata()
            metadata[key] = entry
            self._atomic_write_metadata(metadata)

    def _read_metadata(self) -> dict:
        """Read metadata from JSON cache file.

        Returns
            Dictionary containing cache metadata, empty dict if file doesn't exist
        """
        if Path(self._cache_json_path).exists():
            with Path(self._cache_json_path).open() as outfile:
                return json.load(outfile)
        return {}


class DriverCache(SmartCache):
    """Driver Cache"""

    def __init__(self, driver_name, base_path=None):
        super().__init__('drivers', base_path)
        self._driver_name = driver_name

    def get(self, release: str) -> Path | None:
        """Get cached driver for the specified release.

        Parameters
            release: Driver release version string

        Returns
            Path to the cached driver binary, None if not found
        """
        return super().get(self._driver_name, release)

    def put(self, f: Path, release: str) -> Path:
        """Cache a driver binary for the specified release.

        Parameters
            f: Path to the driver zip file to cache
            release: Driver release version string

        Returns
            Path to the cached driver binary
        """
        return super().put(f, self._driver_name, release)

    def remove(self, release: str) -> None:
        """Remove cached driver for the specified release.
        """
        super().remove(self._driver_name, release)

    def clear(self) -> None:
        """Remove all cached drivers.
        """
        super().clear()

    def find_release_for_version(self, version: int) -> str | None:
        """Find a cached release matching the given major version.
        """
        metadata = self._read_metadata()
        for key, entry in metadata.items():
            if not key.startswith(f'{self._driver_name}_'):
                continue
            release_str = key.removeprefix(f'{self._driver_name}_')
            major = int(release_str.split('.', maxsplit=1)[0] or 0)
            if major == version and Path(entry['binary_path']).exists():
                return release_str
        return None


class BrowserCache(SmartCache):
    """Browser Cache"""

    def __init__(self, browser_name, base_path=None):
        super().__init__('browsers', base_path)
        self._browser_name = browser_name

    def get(self, release: str, revision: str | None = None) -> Path | None:
        """Get cached browser for the specified release and revision.

        Parameters
            release: Browser release version string
            revision: Optional browser revision string

        Returns
            Path to the cached browser binary, None if not found
        """
        return super().get(self._browser_name, release, revision)

    def put(self, f: Path, release: str, revision: str | None = None) -> Path:
        """Cache a browser binary for the specified release and revision.

        Parameters
            f: Path to the browser zip file to cache
            release: Browser release version string
            revision: Optional browser revision string

        Returns
            Path to the cached browser binary
        """
        return super().put(f, self._browser_name, release, revision)

    def remove(self, release: str, revision: str | None = None) -> None:
        """Remove cached browser for the specified release and revision.
        """
        super().remove(self._browser_name, release, revision)

    def clear(self) -> None:
        """Remove all cached browsers.
        """
        super().clear()


class BrowserUserDataCache:
    """Browser User Data Cache"""

    def __init__(self, browser_name, base_path=None):
        self._browser_cache = BrowserCache(browser_name, base_path)

    def _calc_user_data_path(self, release: str, revision: str | None = None) -> Path:
        """Calculate the user data directory path for a browser release.

        Parameters
            release: Browser release version string
            revision: Optional browser revision string

        Returns
            Path to the user data directory for the browser release
        """
        browser_path = self._browser_cache.get(release, revision)
        if not browser_path:
            raise AssertionError('get_browser() not yet called')
        user_data_path = Path(*browser_path.parts[: browser_path.parts.index(release) + 1])
        user_data_path = user_data_path.joinpath('UserData')
        return user_data_path

    def get(self, release: str, revision: str | None = None) -> Path:
        """Get the user data directory for a browser release.

        Creates the user data directory if it doesn't exist and returns
        the path for browser profile storage.

        Parameters
            release: Browser release version string
            revision: Optional browser revision string

        Returns
            Path to the user data directory
        """
        user_data_path = self._calc_user_data_path(release, revision)
        user_data_path.mkdir(mode=0o755, exist_ok=True)
        logger.info(f'Got user data {user_data_path} for {self._browser_cache._browser_name}')
        return user_data_path

    def remove(self, release: str, revision: str | None = None) -> None:
        """Remove the user data directory for a browser release.

        Parameters
            release: Browser release version string
            revision: Optional browser revision string
        """
        user_data_path = self._calc_user_data_path(release, revision)
        if not Path(user_data_path).exists():
            logger.warning(f'{user_data_path} does not exist')
            return
        try:
            shutil.rmtree(user_data_path, ignore_errors=False)
            logger.info(f'Removed {user_data_path}')
        except OSError as err:
            logger.exception(err)
