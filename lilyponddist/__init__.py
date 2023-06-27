import sys


__VERSION__ = "0.4.0"

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--version':
        print(__VERSION__)
    sys.exit(0)


from pathlib import Path
import platform
import sysconfig
import os
import logging
import urllib.request
import tempfile
import appdirs
import shutil
import progressbar
from typing import Union


urls = {
    ('windows', 'x86_64'): "https://gitlab.com/lilypond/lilypond/-/releases/v2.24.1/downloads/lilypond-2.24.1-mingw-x86_64.zip",
    ('linux', 'x86_64'): "https://gitlab.com/lilypond/lilypond/-/releases/v2.24.1/downloads/lilypond-2.24.1-linux-x86_64.tar.gz",
    ('darwin', 'x86_64'): "https://gitlab.com/lilypond/lilypond/-/releases/v2.24.1/downloads/lilypond-2.24.1-darwin-x86_64.tar.gz"
}
    

logger = logging.getLogger("lilyponddist")


class _ProgressBar():

    def __init__(self):
        self.pbar = None

    def __call__(self, block_num, block_size, total_size):
        if not self.pbar:
            self.pbar=progressbar.ProgressBar(maxval=total_size)
            self.pbar.start()

        downloaded = block_num * block_size
        if downloaded < total_size:
            self.pbar.update(downloaded)
        else:
            self.pbar.finish()


def _download(url: str, destFolder: Path, showprogress=True) -> Path:
    assert destFolder.exists() and destFolder.is_dir()
    fileName = os.path.split(url)[1]
    dest = Path(destFolder) / fileName
    if dest.exists():
        logger.warning(f"Destination {dest} already exists, overwriting")
        os.remove(dest)
    logger.info(f"Downloading {url}")
    if showprogress:
        urllib.request.urlretrieve(url, dest, _ProgressBar())
    else:
        urllib.request.urlretrieve(url, dest)
    logger.info(f"   ... saved to {dest}")
    return dest


def _uncompress(path: Path, destfolder: Path):
    def _zipextract(zippedfile: Path, destfolder: Path):
        import zipfile
        with zipfile.ZipFile(zippedfile, 'r') as z:
            z.extractall(destfolder)

    def _targzextract(f: Path, destfolder: Path):
        import tarfile
        tfile = tarfile.open(f)
        tfile.extractall(destfolder)

    destfolder.mkdir(exist_ok=True, parents=True)

    if path.name.endswith('.zip'):
        _zipextract(path, destfolder)
    elif path.name.endswith('.tar.gz'):
        _targzextract(path, destfolder)
    else:
        raise RuntimeError(f"File format of {path} not supported")


def _lilyponddist_folder() -> Path:
    return Path(appdirs.user_data_dir('lilyponddist'))


def download_lilypond(osname: str = '', arch='', showprogress=True) -> Path:
    """
    Downloads lilypond, expands it and returns the root path

    Args:
        osname: one of 'linux', 'windows', 'darwin'
        arch: one of 'x86_64', 'arm64'. At the moment only x86_64 is supported

    Returns:
        the destination folder. This will be something like '~/.local/share/lilyponddist/lilypond-2.24.1'
    """
    _osname, _arch = _get_platform()
    if not osname:
        osname = _osname 
    if not arch:
        arch = _arch
        
    url = urls.get((osname, arch))
    if url is None:
        platforms = [f"{osname}-{arch}" for osname, arch in urls.keys()]
        raise KeyError(f"Platform {osname}-{arch} not supported. Possible platforms: {platforms}")

    tempdir = Path(tempfile.gettempdir())
    payload = _download(url, tempdir, showprogress=showprogress)
    if not payload.exists():
        raise OSError(f"Failed to download file {payload}, file does not exist")

    destfolder = _lilyponddist_folder()
    if destfolder.exists():
        shutil.rmtree(destfolder)
    _uncompress(payload, destfolder)
    assert destfolder.exists()

    _fix_times()
    return destfolder


def _is_first_run() -> bool:
    return not _lilyponddist_folder().exists()


def _fix_times():
    lilyroot = lilypondroot()
    if not lilyroot.exists():
        raise RuntimeError(f"folder {lilyroot} does not exist")

    ccache = lilyroot / "lib/guile/2.2/ccache"
    if ccache.exists():
        for f in ccache.rglob("*.go"):
            f.touch(exist_ok=True)
    ccache = lilyroot / "lib/lilypond/2.24.1/ccache/lily"
    if ccache.exists():
        for f in ccache.rglob("*.go"):
            f.touch(exist_ok=True)


def _initlib():
    osname, arch = _get_platform()
    if osname == 'darwin':
        logger.error("For macos it is recommended to install via homebrew at the moment")
        return

    if arch not in ('x64', 'x86_64'):
        logger.error(f"At the moment only x64 architecture is supported, got {arch}")
        return

    download_lilypond(osname=osname)


def _get_platform() -> tuple[str, str]:
    """
    Return a string with current platform (system and machine architecture).

    This attempts to improve upon `sysconfig._get_platform` by fixing some
    issues when running a Python interpreter with a different architecture than
    that of the system (e.g. 32bit on 64bit system, or a multiarch build),
    which should return the machine architecture of the currently running
    interpreter rather than that of the system (which didn't seem to work
    properly). The reported machine architectures follow platform-specific
    naming conventions (e.g. "x86_64" on Linux, but "x64" on Windows).

    Example output strings for common platforms:

        darwin_(ppc|ppc64|i368|x86_64|arm64)
        linux_(i686|x86_64|armv7l|aarch64)
        windows_(x86|x64|arm32|arm64)

    """

    system = platform.system().lower()
    machine = sysconfig.get_platform().split("-")[-1].lower()
    is_64bit = sys.maxsize > 2 ** 32

    if system == "darwin": # get machine architecture of multiarch binaries
        if any([x in machine for x in ("fat", "intel", "universal")]):
            machine = platform.machine().lower()

    elif system == "linux":  # fix running 32bit interpreter on 64bit system
        if not is_64bit and machine == "x86_64":
            machine = "i686"
        elif not is_64bit and machine == "aarch64":
            machine = "armv7l"

    elif system == "windows": # return more precise machine architecture names
        if machine == "amd64":
            machine = "x64"
        elif machine == "win32":
            if is_64bit:
                machine = platform.machine().lower()
            else:
                machine = "x86"

    # some more fixes based on examples in https://en.wikipedia.org/wiki/Uname
    if not is_64bit and machine in ("x86_64", "amd64"):
        if any([x in system for x in ("cygwin", "mingw", "msys")]):
            machine = "i686"
        else:
            machine = "i386"

    return system, machine


def lilypondroot() -> Path:
    return _lilyponddist_folder() / "lilypond-2.24.1"


def lilypondbin() -> Path:
    """
    Get the lilypond binary for this platform. 

    Will raise RuntimeError if this platform is not supported
    """
    if sys.platform == 'win32':
        binary = 'lilypond.exe'
    else:
        binary = 'lilypond'

    return lilypondroot() / 'bin' / binary


if _is_first_run():
    print("lilyponddist -- First Run. Will download lilypond")
    _initlib()
