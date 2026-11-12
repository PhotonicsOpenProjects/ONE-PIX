"""ONE-PIX must import and run on a Python without tkinter (server without a screen, container)."""
import subprocess
import sys

BLOCK_TKINTER = (
    "import sys\n"
    "for name in ('tkinter', 'tkinter.filedialog', 'tkinter.messagebox'):\n"
    "    sys.modules[name] = None\n"      # an import now fails as it does when python3-tk is absent
)


def run(code):
    return subprocess.run([sys.executable, "-c", BLOCK_TKINTER + code], capture_output=True, text=True, timeout=180)


def test_the_core_imports_without_tkinter():
    result = run(
        "import onepix.Acquisition, onepix.Analysis, onepix.Reconstruction, onepix.export\n"
        "import onepix.hardware.coregistration_lib\n"
        "print('imported')\n"
    )
    assert result.returncode == 0 and "imported" in result.stdout, result.stderr[-800:]


def test_a_folder_dialog_without_tkinter_says_what_to_do():
    result = run(
        "from onepix import utils\n"
        "try:\n"
        "    utils.ask_directory('x', '.')\n"
        "except RuntimeError as exc:\n"
        "    print(exc)\n"
    )
    assert "python3-tk" in result.stdout and "explicitly" in result.stdout, result.stderr[-800:]
