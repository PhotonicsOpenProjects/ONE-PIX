# install.py

import platform
import subprocess
import sys
import os
from pathlib import Path

INSTALL_DIR = Path("install").resolve()

def is_raspberry_pi():
    # Detect if the current system is a Raspberry Pi
    try:
        with open("/proc/device-tree/model") as f:
            return "raspberry pi" in f.read().lower()
    except FileNotFoundError:
        return False

def install_requirements(file_path):
    # Install dependencies from a given requirements file
    print(f"Installing dependencies from {file_path}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(file_path)])

def install_raspberry():
    # Run the install.sh script from within the install/ directory
    script_path = INSTALL_DIR / "install.sh"

    if not script_path.exists():
        print(f"install.sh not found at {script_path}")
        sys.exit(1)

    print(f"Running Raspberry Pi install script: {script_path}")

    # Save current directory and change to INSTALL_DIR
    prev_cwd = os.getcwd()
    os.chdir(str(INSTALL_DIR))

    try:
        subprocess.check_call(["chmod", "+x", "install.sh"])
        subprocess.check_call(["./install.sh"])
    finally:
        os.chdir(prev_cwd)

def main():
    if is_raspberry_pi():
        print("🟢 Raspberry Pi detected.")
        install_raspberry()
    else:
        print("🟢 Standard system detected (Windows/Linux/Mac).")
        req_path = INSTALL_DIR / "requirements.txt"
        if req_path.exists():
            install_requirements(req_path)
        else:
            print("requirements.txt not found in /install.")
            sys.exit(1)

if __name__ == "__main__":
    main()
