"""Shared filesystem-safety helpers for blueprints that read/write
files named by the client (data_manager, analysis).
"""

from pathlib import Path

from werkzeug.utils import secure_filename as _secure_filename


def safe_path(base_dir, filename):
    """Resolve `filename` under `base_dir`, refusing to leave it.

    Returns the resolved Path, or None if `filename` is empty or would
    resolve outside `base_dir` (absolute path, ".." traversal, etc.).
    Callers must check for None before using the result.
    """
    if not filename:
        return None

    base_dir = Path(base_dir).resolve()
    candidate = (base_dir / filename).resolve()

    try:
        candidate.relative_to(base_dir)
    except ValueError:
        return None

    return candidate


def secure_filename(filename):
    """Sanitize a client-supplied filename before saving it to disk."""
    return _secure_filename(filename or "")
