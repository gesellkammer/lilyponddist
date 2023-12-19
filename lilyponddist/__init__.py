from __future__ import annotations
import sys


__VERSION__ = "0.5"


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--version':
        print(__VERSION__)
    sys.exit(0)


from pathlib import Path
import platform
import sysconfig
import os
import re
import logging
import urllib.request
import tempfile
import appdirs
import shutil
import progressbar
import subprocess


_urls = {
    (2, 24, 1): {
        ('windows', 'x86_64'): "https://gitlab.com/lilypond/lilypond/-/releases/v2.24.1/downloads/lilypond-2.24.1-mingw-x86_64.zip",
        ('linux', 'x86_64'): "https://gitlab.com/lilypond/lilypond/-/releases/v2.24.1/downloads/lilypond-2.24.1-linux-x86_64.tar.gz",
        ('darwin', 'x86_64'): "https://gitlab.com/lilypond/lilypond/-/releases/v2.24.1/downloads/lilypond-2.24.1-darwin-x86_64.tar.gz"
    },
    (2, 24, 3): {
        ('windows', 'x86_64'): "https://gitlab.com/lilypond/lilypond/-/releases/v2.24.3/downloads/lilypond-2.24.3-mingw-x86_64.zip",
        ('linux', 'x86_64'): "https://gitlab.com/lilypond/lilypond/-/releases/v2.24.3/downloads/lilypond-2.24.3-linux-x86_64.tar.gz",
        ('darwin', 'x86_64'): "https://gitlab.com/lilypond/lilypond/-/releases/v2.24.3/downloads/lilypond-2.24.3-darwin-x86_64.tar.gz"
    }
}


LASTVERSION = (2, 24, 3)
urls = _urls[LASTVERSION]


logger = logging.getLogger("lilyponddist")
logger.setLevel("INFO")


class LilypondNotFound(RuntimeError): pass


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


def _download(url: str, destFolder: Path, showprogress=True, skip=True) -> Path:
    assert destFolder.exists() and destFolder.is_dir()
    fileName = os.path.split(url)[1]
    dest = Path(destFolder) / fileName
    if dest.exists():
        if skip:
            logger.warning(f"Destination {dest} already exists, no need to download")
            return dest
        else:
            logger.warning(f"Destination {dest} already exists, overwriting")
            os.remove(dest)
    if showprogress:
        print(f"Downloading {url}")
        urllib.request.urlretrieve(url, dest, _ProgressBar())
    else:
        logger.info(f"Downloading {url}")
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


def download_lilypond(version: tuple[int, int, int] = LASTVERSION,
                      osname='',
                      arch=''
                      ) -> Path:
    """
    Downloads and install lilypond, expands it and returns the root path

    Args:
        version: the version to download/install
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

    urls = _urls.get(version)
    if not urls:
        raise ValueError(f"Version {version} unknown. Possible versions: {_urls.keys()}")

    url = urls.get((osname, arch))
    if url is None:
        platforms = [f"{osname}-{arch}" for osname, arch in urls.keys()]
        raise KeyError(f"Platform {osname}-{arch} not supported. Possible platforms: {platforms}")

    tempdir = Path(tempfile.gettempdir())
    payload = _download(url, tempdir, showprogress=True)
    if not payload.exists():
        raise OSError(f"Failed to download file {payload}, file does not exist")

    destfolder = _lilyponddist_folder()
    # destfolder = lilypondroot()

    if destfolder.exists():
        logger.info(f"Destination folder {destfolder} already exists, removing")
        shutil.rmtree(destfolder)

    _uncompress(payload, destfolder)
    assert destfolder.exists()

    _fix_times()
    return destfolder


def _is_first_run() -> bool:
    return not _lilyponddist_folder().exists()


def _fix_times(version=(2, 24, 1)):
    lilyroot = lilypondroot()
    major, minor, patch = version
    versionstr = f"{major}.{minor}.{patch}"
    if not lilyroot.exists():
        raise RuntimeError(f"folder {lilyroot} does not exist")

    ccache = lilyroot / "lib/guile/2.2/ccache"
    if ccache.exists():
        for f in ccache.rglob("*.go"):
            f.touch(exist_ok=True)
        logger.info(f"Fixed times of lilyponds guile cache {ccache}")

    ccache = lilyroot / f"lib/lilypond/{versionstr}/ccache/lily"
    if ccache.exists():
        for f in ccache.rglob("*.go"):
            f.touch(exist_ok=True)
        logger.info(f"Fixed times of lilyponds binaries at {ccache}")


def is_lilypond_installed() -> bool:
    """
    Returns True if lilypond is installed via lilyponddist

    We never check if lilypond is installed by any other means.
    The general idea of this package is to generate an isolated
    lilypond installation
    """
    try:
        lilybin = lilypondbin()
        return lilybin.exists()
    except LilypondNotFound:
        return False


def _initlib():
    osname, arch = _get_platform()
    if osname == 'darwin':
        logger.error("For macos it is recommended to install via homebrew at the moment")
        return

    if arch not in ('x64', 'x86_64'):
        logger.error(f"At the moment only x64 architecture is supported, got {arch}")
        return

    if not is_lilypond_installed() or needs_update():
        download_lilypond(osname=osname)
    else:
        currentversion, versionline = lilypond_version()
        logger.info(f"lilypond is installed and up to date (current version: {currentversion}, version line: {versionline})")


def _get_platform(normalize=True) -> tuple[str, str]:
    """
    Return a string with current platform (system and machine architecture).

    This attempts to improve upon `sysconfig._get_platform` by fixing some
    issues when running a Python interpreter with a different architecture than
    that of the system (e.g. 32bit on 64bit system, or a multiarch build),
    which should return the machine architecture of the currently running
    interpreter rather than that of the system (which didn't seem to work
    properly). The reported machine architectures follow platform-specific
    naming conventions (e.g. "x86_64" on Linux, but "x64" on Windows).
    Use normalize=True to reduce those labels (returns one of 'x86_64', 'arm64', 'x86')
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

    if normalize:
        machine = {
            'x64': 'x86_64',
            'aarch64': 'arm64',
            'amd64': 'x86_64'
        }.get(machine, machine)
    return system, machine


def lilypondroot() -> Path | None:
    """
    The root folder of the lilypond installation
    """
    base = _lilyponddist_folder()
    for entry in base.glob("lilypond-*"):
        absentry = entry.absolute()
        logger.debug(f"Searching lilypond in '{absentry}'")
        if absentry.is_dir() and (absentry/"bin/lilypond").exists():
            return absentry
    logger.info("Did not find lilypond root")
    return None


def lilypond_version() -> tuple[tuple[int, int, int], str]:
    """
    Returns a tuple (version, versionline)

    where version is a tuple (major: int, minor: int, patch: int) and
    verisonline is the line where the version is defined (normally the
    first line printed by lilypond when called as 'lilypond --version')
    """
    lilybin = lilypondbin()
    if not lilybin.exists():
        raise RuntimeError("Lilypond has not been installed via lilyponddist")

    proc = subprocess.run([lilybin, '--version'], capture_output=True)
    if proc.returncode != 0:
        logger.error(proc.stderr)
        raise RuntimeError(f"Error while running '{lilybin} --version', error code: {proc.returncode}")
    for line in proc.stdout.decode().splitlines():
        if match := re.search(r"GNU LilyPond (\d+)\.(\d+)\.(\d+)", line):
            major = int(match.group(1))
            minor = int(match.group(2))
            patch = int(match.group(3))
            return ((major, minor, patch), line)
    return ((0, 0, 0), '')


def needs_update() -> bool:
    """
    Is there an update available for the current version of lilypond installed via lilyponddist
    """
    if not is_lilypond_installed():
        raise RuntimeError("No version of lilypond installed via lilyponddist")
    currentversion, versionline = lilypond_version()
    if currentversion[0] == 0:
        raise RuntimeError("Could not fetch the current version of lilypond")
    return currentversion < LASTVERSION


def update() -> tuple[int, int, int] | None:
    """
    Update the current installation if needed

    Returns:
        either the version to which lilypond has been updated, or None
        if no update was needed
    """
    if not is_lilypond_installed():
        download_lilypond(version=LASTVERSION)
        return LASTVERSION

    if needs_update():
        download_lilypond(version=LASTVERSION)
        return LASTVERSION

    logger.debug("No need to update")
    return None


def lilypondbin() -> Path:
    """
    Get the lilypond binary for this platform.

    Will raise RuntimeError if this platform is not supported
    """
    if sys.platform == 'win32':
        binary = 'lilypond.exe'
    else:
        binary = 'lilypond'

    root = lilypondroot()
    if root is None:
        raise LilypondNotFound("lilypond root folder not found")

    if needs_update():
        logger.info(f"There is an update available, {LASTVERSION}. To update, call the `update()` function")
    return root / 'bin' / binary


if _is_first_run():
    print("lilyponddist -- First Run. Will download lilypond")
    _initlib()