# install.py

import platform
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
INSTALL_DIR = ROOT_DIR / "install"


def run(cmd, cwd=None):

    cmd = [str(c) for c in cmd]

    print(f"\n>>> {' '.join(cmd)}")
    print(f">>> cwd={cwd}\n")

    subprocess.check_call(cmd, cwd=cwd)


def is_raspberry_pi():

    try:
        with open("/proc/device-tree/model") as f:
            return "raspberry pi" in f.read().lower()

    except Exception:
        return False


def install_standard():

    print("🟢 Standard system detected")
    print(f"ROOT_DIR = {ROOT_DIR}")

    # install package + deps depuis pyproject.toml
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-e",
            ".",
            "--break-system-packages"
        ],
        cwd=ROOT_DIR
    )


def install_raspberry():

    print("🟢 Raspberry Pi detected")
    print(f"ROOT_DIR = {ROOT_DIR}")

    script_path = INSTALL_DIR / "install_rpi.sh"

    if not script_path.exists():
        raise FileNotFoundError(f"{script_path} not found")

    # rendre executable
    run(
        ["chmod", "+x", script_path],
        cwd=INSTALL_DIR
    )

    # install dépendances système Raspberry Pi
    run(
        ["bash", script_path],
        cwd=INSTALL_DIR
    )

    # install package python sans deps
    # (déjà gérées par install_rpi.sh)
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-e",
            ".",
            "--no-deps",
            "--break-system-packages"
        ],
        cwd=ROOT_DIR
    )


def main():

    print("======================================")
    print("ONE-PIX INSTALLER")
    print("======================================")

    print(f"OS detected: {platform.system()}")

    if platform.system() == "Linux" and is_raspberry_pi():
        install_raspberry()
    else:
        install_standard()

    print("\n✅ Installation completed successfully")


if __name__ == "__main__":
    main()