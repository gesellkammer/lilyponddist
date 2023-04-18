from pathlib import Path
import sys
import platform
import sysconfig


__VERSION__ = "0.1.3"


def _is_first_run() -> bool:
    datadir = _datadir()
    beacon = datadir / 'lastrun.txt'
    if beacon.exists():
        beacontxt = open(beacon).read()
        line = beacontxt.splitlines()[0]
        assert line.startswith('Version')
        version = line.split(":")[1].strip()
        if version == __VERSION__:
            return False
        else:
            print(f"Found version {version}, but own version is {__VERSION__}")
    open(beacon, 'w').write(f"Version: {__VERSION__}")
    return True


def _initlib():
    lilyroot = lilypondroot()
    ccache = lilyroot / "lib/guile/2.2/ccache"
    if ccache.exists():
        for f in ccache.rglob("*.go"):
            f.touch(exist_ok=True)
    ccache = lilyroot / "lib/lilypond/2.24.1/ccache/lily"
    if ccache.exists():
        for f in ccache.rglob("*.go"):
            f.touch(exist_ok=True)


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


def _datadir() -> Path:
    return Path(__file__).parent / "data"


def lilypondroot() -> Path:
    """
    Get the path of the lilypond distributed binaries for this platform

    Will raise RuntimeError if the platform is not supported
    Will raise IOError if the distributed binaries were not found
    """
    datadir = _datadir()
    osname, arch = _get_platform()
    
    if osname == 'windows':
        if arch != 'x64':
            raise RuntimeError(f"lilypond.org only provides binaries for x64, "
                               f"there is no support for {arch}")
        lilyroot = datadir / 'windows-x86_64'
    elif sys.platform == 'linux':
        if arch != 'x86_64':
            raise RuntimeError(f"lilypond.org only provides binaries for x86_64, "
                               f"there is no support for {arch}")
        lilyroot = datadir / 'linux-x86_64'
    elif sys.platform == 'darwin':
        _, arch = _get_platform()
        if arch == 'x86_64':
            lilyroot = datadir / 'macos-x86_64'
        elif arch == 'arm64':
            raise RuntimeError("lilypond.org does not provide binaries for arm64. "
                               "Use homebrew to install lilypond")
        else:
            raise RuntimeError(f"Architecture {arch} not supported")
    else:
        raise RuntimeError(f"Platform {sys.platform} not supported")

    if not lilyroot.exists():
        raise IOError(f"lilypond distributed files not found. Path: {lilyroot}")
    return lilyroot
    

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


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--version':
        print(__VERSION__)
elif _is_first_run():
    print("lilyponddist -- first run")
    _initlib()
