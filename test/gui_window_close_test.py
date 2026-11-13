"""Windows are closed through the GUI thread, never from the thread that cancels an acquisition.

A cv2.destroyAllWindows() issued from another thread broke the Qt backend: the next acquisition's
window came up small and misplaced. The rule is checked on the source (it needs no display), and the
helper itself with a stand-in for the GUI thread."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
CORE = [p for p in (ROOT / "onepix").rglob("*.py") if p.name != "gui_thread.py"]


def test_no_core_module_destroys_windows_outside_the_gui_thread():
    offenders = []
    for path in CORE:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "cv2.destroyAllWindows" in line and "gui_thread.run" not in line and not line.lstrip().startswith("#"):
                offenders.append(f"{path.relative_to(ROOT)}:{n}")
    assert not offenders, offenders


def test_close_all_windows_runs_on_the_gui_thread_and_pumps_events(monkeypatch):
    from onepix.hardware import gui_thread as module

    calls = []

    class Fake:
        def run(self, fn, *args):
            calls.append((fn.__name__, args))

    monkeypatch.setattr(module, "gui_thread", Fake())
    module.close_all_windows()
    assert calls == [("destroyAllWindows", ()), ("waitKey", (1,))]


def test_close_all_windows_never_raises(monkeypatch):
    from onepix.hardware import gui_thread as module

    class Broken:
        def run(self, fn, *args):
            raise module.GuiThreadStuckError("wedged")

    monkeypatch.setattr(module, "gui_thread", Broken())
    module.close_all_windows()
