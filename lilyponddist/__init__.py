from __future__ import annotations
import sys

import platform
import sysconfig
import os
import re
import logging
import tempfile
import appdirs
import subprocess
import functools


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import progressbar
    import pathlib


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
    },
    (2, 25, 15): {
        ('windows', 'x86_64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.15/downloads/lilypond-2.25.15-mingw-x86_64.zip',
        ('linux', 'x86_64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.15/downloads/lilypond-2.25.15-linux-x86_64.tar.gz',
        ('darwin', 'x86_64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.15/downloads/lilypond-2.25.15-darwin-x86_64.tar.gz',
        ('darwin', 'arm64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.15/downloads/lilypond-2.25.15-darwin-arm64.tar.gz'
    },
    (2, 25, 24): {
        ('windows', 'x86_64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.24/downloads/lilypond-2.25.24-mingw-x86_64.zip',
        ('linux', 'x86_64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.24/downloads/lilypond-2.25.24-linux-x86_64.tar.gz',
        ('darwin', 'x86_64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.24/downloads/lilypond-2.25.24-darwin-x86_64.tar.gz',
        ('darwin', 'arm64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.24/downloads/lilypond-2.25.24-darwin-arm64.tar.gz'
    },
    (2, 25, 26): {
        ('windows', 'x86_64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.26/downloads/lilypond-2.25.26-mingw-x86_64.zip',
        ('linux', 'x86_64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.26/downloads/lilypond-2.25.26-linux-x86_64.tar.gz',
        ('darwin', 'x86_64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.26/downloads/lilypond-2.25.26-darwin-x86_64.tar.gz',
        ('darwin', 'arm64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.26/downloads/lilypond-2.25.26-darwin-arm64.tar.gz'
    },
    (2, 25, 30): {
        ('windows', 'x86_64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.30/downloads/lilypond-2.25.30-mingw-x86_64.zip',
        ('linux', 'x86_64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.30/downloads/lilypond-2.25.30-linux-x86_64.tar.gz',
        ('darwin', 'x86_64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.30/downloads/lilypond-2.25.30-darwin-x86_64.tar.gz',
        ('darwin', 'arm64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.30/downloads/lilypond-2.25.30-darwin-arm64.tar.gz'
    },
    (2, 25, 31): {
        ('windows', 'x86_64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.31/downloads/lilypond-2.25.31-mingw-x86_64.zip',
        ('linux', 'x86_64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.31/downloads/lilypond-2.25.31-linux-x86_64.tar.gz',
        ('darwin', 'x86_64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.31/downloads/lilypond-2.25.31-darwin-x86_64.tar.gz',
        ('darwin', 'arm64'): 'https://gitlab.com/lilypond/lilypond/-/releases/v2.25.31/downloads/lilypond-2.25.31-darwin-arm64.tar.gz'
    },
}


LASTVERSION = max(_urls.keys())


logger = logging.getLogger("lilyponddist")

_handler = logging.StreamHandler()
_formatter = logging.Formatter(fmt='%(name)s:%(lineno)4s:%(levelname)8s >> %(message)s')
_handler.setFormatter(_formatter)
logger.addHandler(_handler)
logger.setLevel("INFO")


class LilypondNotFoundError(RuntimeError):
    pass


class _ProgressBar():

    def __init__(self):
        self.pbar: progressbar.ProgressBar | None = None

    def __call__(self, block_num, block_size, total_size):
        if not self.pbar:
            import progressbar
            self.pbar = progressbar.ProgressBar(maxval=total_size)
            self.pbar.start()
        assert self.pbar is not None

        downloaded = block_num * block_size
        if downloaded < total_size:
            self.pbar.update(downloaded)
        else:
            self.pbar.finish()


def _download(url: str, destFolder: pathlib.Path, showprogress=True, skip=True) -> pathlib.Path:
    import pathlib
    assert destFolder.exists() and destFolder.is_dir()
    fileName = os.path.split(url)[1]
    dest = pathlib.Path(destFolder) / fileName

    if dest.exists():
        if skip:
            logger.info("Destination '%s' already exists, no need to download", dest)
            return dest
        else:
            logger.info("Destination '%s' already exists, overwriting", dest)
            os.remove(dest)
    import urllib.request
    if showprogress:
        print(f"Downloading {url}")
        urllib.request.urlretrieve(url, dest, _ProgressBar())
    else:
        logger.info("Downloading '%s'", url)
        urllib.request.urlretrieve(url, dest)
    logger.info("   ... saved to '%s'", dest)
    return dest


def _uncompress(path: pathlib.Path, destfolder: pathlib.Path):
    def _zipextract(zippedfile: pathlib.Path, destfolder: pathlib.Path):
        import zipfile
        with zipfile.ZipFile(zippedfile, 'r') as z:
            z.extractall(destfolder)

    def _targzextract(f: pathlib.Path, destfolder: pathlib.Path):
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


def _lilyponddist_folder() -> pathlib.Path:
    import pathlib
    return pathlib.Path(appdirs.user_data_dir('lilyponddist'))


def _select_version(minversion: tuple[int, int, int], versions: list[tuple[int, int, int]], matchop=">="
                    ) -> tuple[int, int, int] | None:
    if matchop == ">=":
        possible_versions = [v for v in versions if v >= minversion]
    elif matchop == ">":
        possible_versions = [v for v in versions if v > minversion]
    else:
        raise ValueError(f"Invalid matchop, expected one of '>=' or '>', got {matchop}")
    if not possible_versions:
        return None
    return max(possible_versions)


def _latest_version_for_platform(minversion: tuple[int, int, int]=(24, 0, 0), matchop=">=", platform: tuple[str, str] | None = None
                                 ) -> tuple[int, int, int] | None:
    if platform:
        osname, arch = platform
    else:
        osname, arch = get_platform()
    versions = [v for v, urls in _urls.items() if (osname, arch) in urls]
    if not versions:
        return None
    return _select_version(minversion=minversion, versions=versions, matchop=matchop)


def _parse_version(version: str) -> tuple[tuple[int, int, int], str]:
    """
    Parses a version str of the form "2.24.0", ">=2.25.12", ">2.24", etc.

    Returns:
        a tuple (versiontup: tuple[int, int, int], matchop: str), where matchop is
        one of "=", ">" or ">="
    """
    matchop = "="
    if version.startswith(">="):
        version = version[2:]
        matchop = ">="
    elif version.startswith(">"):
        version = version[1:]
        matchop = ">"
    elif version.startswith("="):
        version = version[1:]
    versiontup = _parse_version_tuple(version)
    return versiontup, matchop


def install_lilypond(version: tuple[int, int, int] | str = '',
                     matchop="=",
                     osname='',
                     arch=''
                     ) -> None:
    """
    Downloads and install lilypond, expands it and returns the root path

    Args:
        version: the version to download/install
        matchop: one of "=", ">=", ">". The matching operator can also be
            given as a part of version if this is a string (eg ">=2.24.0")
        osname: one of 'linux', 'windows', 'darwin'
        arch: one of 'x86_64', 'arm64'.

    """
    import pathlib
    _osname, _arch = get_platform()
    if not osname:
        osname = _osname
    if not arch:
        arch = _arch

    if not version:
        versiontup = _latest_version_for_platform(minversion=(2, 25, 24), matchop=">=", platform=(osname, arch))
        if not versiontup:
            raise ValueError(f"Could not find any version for {osname}/{arch}")

    elif isinstance(version, str):
        versiontup, matchop = _parse_version(version)
    else:
        versiontup = version

    assert isinstance(versiontup, tuple) and len(versiontup) == 3 and all(isinstance(part, int) for part in versiontup)
    if matchop == "=":
        urls = _urls.get(versiontup)
        if not urls:
            raise ValueError(f"Version {versiontup} unknown. Possible versions: {_urls.keys()}")
        url = urls.get((osname, arch))
        if url is None:
            raise KeyError(f"Platform {osname}-{arch} not supported for version {versiontup}")
    else:
        assert matchop in (">=", ">")
        matchedversion = _latest_version_for_platform(minversion=versiontup, matchop=matchop, platform=(osname, arch))
        if not matchedversion:
            raise ValueError(f"Could not find any url for {osname}/{arch} with version {matchop} {versiontup}.")

    tempdir = pathlib.Path(tempfile.gettempdir())
    payload = _download(url, tempdir, showprogress=True)
    if not payload.exists():
        raise OSError(f"Failed to download file {payload}, file does not exist")

    destfolder = _lilyponddist_folder()

    logger.info("Creating folder '%s' if needed", destfolder)
    destfolder.mkdir(parents=True, exist_ok=True)

    logger.debug("Uncompressing '%s' to '%s'", payload, destfolder)
    _uncompress(payload, destfolder)

    assert destfolder.exists()
    _reset_cache()
    _fix_times(versiontup)


def _is_first_run() -> bool:
    return not _lilyponddist_folder().exists()


def _fix_times(version: tuple[int, int, int]):
    lilyroot = lilypondroot()
    if lilyroot is None or not lilyroot.exists():
        raise RuntimeError(f"Folder '{lilyroot}' does not exist")

    major, minor, patch = version
    versionstr = f"{major}.{minor}.{patch}"

    guileroot = lilyroot / "lib/guile"
    # match any version "<lilypondroot>/lib/guile/?.?/ccache". Depending on the lilypond version
    # this can be 2.2 or 3.0
    for guiledir in guileroot.glob("?.?"):
        guilecache = guiledir / "ccache"
        if guilecache.exists():
            for f in guilecache.rglob("*.go"):
                f.touch(exist_ok=True)
            logger.info(f"Fixed times of lilyponds guile cache {guilecache}")
        else:
            logger.warning(f"Guile cache not found: '{guilecache}'")

    ccache = lilyroot / f"lib/lilypond/{versionstr}/ccache/lily"
    if ccache.exists():
        for f in ccache.rglob("*.go"):
            f.touch(exist_ok=True)
        logger.info("Fixed times of lilyponds binaries at %s", ccache)
    else:
        logger.warning(f"Lilypond .go cached files not found: {ccache}/*.go")


def available_versions() -> list[tuple[str, list[str]]]:
    """
    Returns a list of available versions

    Each version consists of a tuple (versionstr, list of platforms with downloads available)

    Example
    ~~~~~~~

    >>> available_versions()
    [("2.24.13", ["linux-x86_64", "darwin-x86_64", "darwin-arm64", "windows-x86:64"])]

    """
    out = []
    for version, urls in _urls.items():
        versionstr = ".".join(map(str, version))
        platforms = [f"{osname}-{arch}" for osname, arch in urls.keys()]
        out.append((versionstr, platforms))
    return out


def available_versions_for_platform(platform='') -> list[str]:
    """
    List of versions available for a given platform

    Args:
        platform: the platform id to query versions for, or an
            empty string to query versions for the current platform.
            A platform is a string with the form <osname>-<architecture>,
            like 'linux-x86_64', 'windows-x86_64' or 'darwin-arm64'.

    Returns:
        a list of lilypond versions available for the given platform.
        Notice that not all versions are available for all platforms.
    """
    if not platform:
        platform = get_platform_id()
    supported_platforms = set()
    versions = available_versions()
    for version, platforms in versions:
        supported_platforms.update(platforms)
    if platform not in supported_platforms:
        raise ValueError(f"Platform '{platform}' unknown. Supported platforms: {sorted(supported_platforms)}")

    out = [version for version, platforms in versions if platform in platforms]
    return out


@functools.cache
def installed_versions() -> dict[tuple[int, int, int], pathlib.Path]:
    """
    Returns a dict mapping version to its root directory

    These are versions installed by lilyponddist in its own location,
    we never query the system for any other kind of installation
    """
    base = _lilyponddist_folder()
    exe = _lilyexe()
    out = {}

    for entry in base.glob("lilypond-*"):
        versionstr = entry.name.split("-")[1]
        absentry = entry.absolute()
        logger.debug(f"Searching lilypond in '{absentry}'")
        if absentry.is_dir() and (absentry/"bin"/exe).exists():
            logger.debug("... found!")
            out[_parse_version_tuple(versionstr)] = absentry

    return out


def is_lilypond_installed(version='') -> bool:
    """
    Returns True if lilypond is installed via lilyponddist

    We never check if lilypond is installed by any other means.
    The general idea of this package is to generate an isolated
    lilypond installation

    Args:
        version: the version to check. Can be an expression of the sort '>=2.25.0'.
            Leave empty to match any version

    Returns:
        True if a lilypond version matching the given version is installed
    """
    lilybin = _find_lilypond(version=version)
    return lilybin is not None and lilybin.exists()


def _initlib(autoupdate=False):
    osname, arch = get_platform()
    if osname == 'darwin':
        logger.info("For macos it is recommended to install via homebrew as there are no"
                    " prebuilt binaries of lilypond for macos/arm64 at the moment")
        return

    if not is_lilypond_installed():
        logger.info("Lilypond not installed, downloading version %s", LASTVERSION)
        install_lilypond(osname=osname)
    elif autoupdate and can_update():
        logger.info("Lilypond is installed but needs to be updated, downloading and installing version %s", LASTVERSION)
        install_lilypond(osname=osname)
    else:
        currentversion, versionline = lilypond_version()
        logger.debug("Lilypond is installed (version: %s, version line: %s). ", currentversion, versionline)
        if currentversion < LASTVERSION:
            logger.debug("Lilypond can be updated to version %s", LASTVERSION)


@functools.cache
def get_platform(normalize=True) -> tuple[str, str]:
    """
    Return a string with current platform (system and machine architecture).

    This attempts to improve upon `sysconfig.get_platform` by fixing some
    issues when running a Python interpreter with a different architecture than
    that of the system (e.g. 32bit on 64bit system, or a multiarch build),
    which should return the machine architecture of the currently running
    interpreter rather than that of the system (which didn't seem to work
    properly). The reported machine architectures follow platform-specific
    naming conventions (e.g. "x86_64" on Linux, but "x64" on Windows).
    Use normalize=True to reduce those labels (returns one of 'x86_64', 'arm64', 'x86')

    Example output strings for common platforms::

        darwin_(ppc|ppc64|i368|x86_64|arm64)
        linux_(i686|x86_64|armv7l|aarch64)
        windows_(x86|x64|arm32|arm64)

    Normalizations:

    * aarch64 -> arm64
    * x64 -> x86_64
    * amd64 -> x86_64

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


def get_platform_id() -> str:
    osname, arch = get_platform()
    return f"{osname}-{arch}"


@functools.cache
def _parse_version_tuple(versionstr: str) -> tuple[int, int, int]:
    """
    Parses a version str of the form <major>.<minor>.<patch>, where minor and patch are optional
    """
    parts = versionstr.split(".")
    major = int(parts[0])
    minor = 0
    patch = 0
    if len(parts) >= 2:
        minor = int(parts[1])
    if len(parts) >= 3:
        patch = int(parts[2])
    if len(parts) >= 4:
        logger.warning(f"Unexpected version string '{versionstr}', parsed as {major}.{minor}.{patch}")
    return major, minor, patch


def lilypondroot(version='') -> pathlib.Path | None:
    """
    The root folder of the lilypond installation

    Args:
        version: the lilypond version, as "<major>.<minor>.<patch>". If not
            given, the latest installed version is used. Can be an expression
            of the form '>=2.25.0' to match any version higher than the given
            one

    Returns:
        the root path, or None if no installation was found
    """
    _installed_versions = installed_versions()

    if not _installed_versions:
        base = _lilyponddist_folder()
        logger.info(f"Did not find any lilypond version installed under '{base}'. Folder content: {list(base.glob('*'))}")
        return None

    if not version:
        versiontup = max(_installed_versions.keys())
        return _installed_versions[versiontup]

    versiontup, matchop = _parse_version(version)
    if matchop == "=":
        if path := _installed_versions.get(versiontup):
            return path
    else:
        if matched_version := _select_version(minversion=versiontup, versions=list(_installed_versions.keys()), matchop=matchop):
            return _installed_versions[matched_version]
    logger.error(f"No installation found for requested version {matchop} {versiontup}. "
                    f"Installed versions: {_installed_versions.keys()}")
    return None


@functools.cache
def lilypond_version() -> tuple[tuple[int, int, int], str]:
    """
    Returns a tuple (version, versionline)

    where version is a tuple (major: int, minor: int, patch: int) and
    versionline is the line where the version is defined (normally the
    first line printed by lilypond when called as 'lilypond --version')

    Raises RuntimeError if LilyPond is not installed via lilyponddist or
    if an error occurs while running 'lilypond --version'
    """
    lilybin = _find_lilypond()
    if not lilybin or not lilybin.exists():
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


def can_update() -> tuple[int, int, int] | None:
    """
    The version to which to update to, or None if no update is needed
    """
    installed = installed_versions()
    if not installed:
        return _latest_version_for_platform()
    latest_installed = max(installed.keys())
    latest_available = _latest_version_for_platform()
    return latest_available if latest_available is not None and latest_available > latest_installed else None


def update() -> tuple[int, int, int] | None:
    """
    Update the current installation if needed

    Returns:
        either the version to which lilypond has been updated, or None
        if no update was needed
    """
    if latest := can_update():
        install_lilypond(version=latest)
        return latest
    else:
        logger.debug("No need to update")
    return None


def _lilyexe() -> str:
    if sys.platform == 'win32':
        return 'lilypond.exe'
    else:
        return 'lilypond'


def _lilypond_binary(root: pathlib.Path) -> pathlib.Path:
    assert root.exists()
    lilypath = root / 'bin' / _lilyexe()
    if not lilypath.exists():
        raise RuntimeError(f"The lilypond path '{lilypath}' does not exist")
    return lilypath


def _find_lilypond(version='') -> pathlib.Path | None:
    installed = installed_versions()
    if not installed:
        logger.debug("No lilypond installation found")
        return None

    if not version:
        versiontup = max(installed.keys())
        root = installed[versiontup]
    else:
        versiontup, matchop = _parse_version(version)
        if matchop == "=":
            root = installed.get(versiontup)
            if not root:
                logger.debug("No lilypond installation found for version %s", versiontup)
                return None
        else:
            maxversion = max(installed)
            if (matchop == ">=" and maxversion >= versiontup) or (matchop == ">" and maxversion > versiontup):
                root = installed[maxversion]
            else:
                logger.error(f"No lilypond installation found for version {matchop} {version}. "
                            f"Installed versions are: {installed.keys()}")
                return None

    try:
        return _lilypond_binary(root=root)
    except RuntimeError as e:
        logger.error(str(e))
        return None


def _reset_cache():
    # lilypondroot.cache_clear()
    # lilypond_version.cache_clear()
    installed_versions.cache_clear()


def lilypondbin(version='') -> pathlib.Path:
    """
    Get the lilypond binary for this platform.

    Args:
        version: the version to use, or an empty string to
            use the latest version installed, or the latest
            version available. Can also be a min. version,
            as ">=2.25.10"

    Returns:
        the path of the lilypond binary as a Path object
    """
    installed = installed_versions()
    if not installed:
        install_lilypond(version=version)

    lily = _find_lilypond(version=version)
    if not lily:
        available = available_versions()
        raise RuntimeError(f"Could not find lilypond binary for version '{version}'. "
                           f"Installed versions: {installed.keys()}, available versions: {available}")

    if newversion := can_update():
        logger.debug(f"There is an update available, {newversion}. To update, call the `update()` function")

    return lily
