import os
import zipfile
import shutil
import tempfile
import requests
import backoff
import platform
import tqdm
from contextlib import contextmanager
from urllib.parse import urlparse, unquote
from pathlib import Path
from packaging.version import parse, Version

from . import logger


class LinuxZipFileWithPermissions(zipfile.ZipFile):
    """Class for extract files in linux with right permissions
    https://stackoverflow.com/a/54748564
    """

    def _extract_member(self, member, targetpath=None, pwd=None):
        if not isinstance(member, zipfile.ZipInfo):
            member = self.getinfo(member)
        if targetpath is None:
            targetpath = os.getcwd()
        target = super()._extract_member(member, targetpath, pwd)
        attr = member.external_attr >> 16
        if attr != 0:
            os.chmod(target, attr)
        return target


def unpack_zip(zip_path):
    """Unzip zip to same diretory"""
    zip_class = zipfile.ZipFile if platform.system() == "Windows" else LinuxZipFileWithPermissions
    archive = zip_class(zip_path)
    try:
        archive.extractall(Path(zip_path).parent)
    except Exception as e:
        if e.args[0] not in [26, 13] and e.args[1] not in ["Text file busy", "Permission denied"]:
            raise e
    return archive.namelist()


@contextmanager
def download_file(url) -> Path:
    """Better download"""
    name = Path(urlparse(unquote(url)).path).name
    with mktempdir() as tmpdir:

        @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_time=30)
        def get():
            with requests.get(url, stream=True) as r:
                save_path = tmpdir.joinpath(name)
                total = int(r.headers.get('content-length', 0))
                chunk = 16 * 1024 * 1024
                with open(save_path, "wb") as f, tqdm.tqdm(total=total, desc=name, unit='B', unit_scale=True) as p:
                    while buf := r.raw.read(chunk):
                        f.write(buf)
                        p.update(len(buf))
                return save_path

        yield get()


@contextmanager
def mktempdir() -> Path:
    """Having errors removing temp directories in Widnows..."""
    try:
        tmp = tempfile.mkdtemp()
        yield Path(tmp)
    finally:

        @backoff.on_exception(backoff.expo, shutil.Error, max_time=10)
        def remove():
            shutil.rmtree(tmp, ignore_errors=False)
            logger.debug(f"Removed {tmp}")

        remove()
