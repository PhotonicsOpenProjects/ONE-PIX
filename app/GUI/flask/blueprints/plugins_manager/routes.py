import json
import queue
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from flask import Response, jsonify, render_template, request

from . import bp
from i18n import t

from onepix_plugins_manager import cli


# One plugin action at a time: two pip runs on the same environment at
# once can leave it half-installed.
_action_lock = threading.Lock()

# Newest versions available on PyPI/GitLab, per project path, as
# (time fetched, cli.available_versions()). Trusted for _AVAILABLE_TTL
# seconds, so changing a filter doesn't query every plugin again; the
# page's Refresh button bypasses it.
_AVAILABLE_TTL = 600
_available_cache = {}

# Projects found by the last listing (all categories) and the GitLab
# access used, reused by /api/updates instead of discovering again.
_last_discovery = {}


class _ThreadRoutedStdout:
    """sys.stdout stand-in that sends what a registered thread prints to
    that thread's own queue, and everything else to the real stdout.

    contextlib.redirect_stdout swaps sys.stdout for the whole process,
    so every other request's print() ended up in the plugin console for
    as long as an action ran."""

    def __init__(self, real):
        self.real = real
        self.queues = {}

    def write(self, text):
        target = self.queues.get(threading.get_ident())
        if target is None:
            return self.real.write(text)
        if text:
            target.put(text)
        return len(text)

    def flush(self):
        self.real.flush()

    def __getattr__(self, name):
        return getattr(self.real, name)


def _routed_stdout():
    if not isinstance(sys.stdout, _ThreadRoutedStdout):
        sys.stdout = _ThreadRoutedStdout(sys.stdout)
    return sys.stdout


@bp.route("/")
def plugins_manager_page():
    return render_template(
        "plugins_manager.html",
        categories=sorted(cli.PLUGIN_CATEGORIES),
    )


@bp.route("/api/plugins")
def api_plugins():
    try:
        projects, meta = load_projects(
            category=request.args.get("category") or None,
            installed_only=request.args.get("installed") == "1",
        )
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify(
        {
            "ok": True,
            "plugins": projects,
            "meta": meta,
        }
    )


@bp.route("/api/updates")
def api_updates():
    """For each plugin (by GitLab path): the newest versions available
    on PyPI and on GitLab, the version an update would install in PyPI
    mode and in dev mode, and whether that's newer than the installed
    one."""
    refresh = request.args.get("refresh") == "1"

    try:
        projects, token, base = discovered_projects()
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    now = time.monotonic()
    stale = [
        project
        for project in projects
        if refresh
        or project["path"] not in _available_cache
        or now - _available_cache[project["path"]][0] > _AVAILABLE_TTL
    ]

    if stale:
        with ThreadPoolExecutor(max_workers=8) as pool:
            found = pool.map(
                lambda project: cli.available_versions(project, token=token, base=base),
                stale,
            )
            for project, versions in zip(stale, found):
                _available_cache[project["path"]] = (now, versions)

    installed_by_path = cli.resolve_installed(projects, cli.get_installed_plugins())
    updates = {}

    for project in projects:
        versions = _available_cache[project["path"]][1]
        installed = installed_by_path[project["path"]]
        installed_version = installed.get("version", "") if installed else ""

        target_pypi = cli.update_target_version(versions)
        target_dev = cli.update_target_version(versions, dev=True)

        updates[project["path"]] = {
            "pypi": versions["pypi"],
            "git": versions["git"],
            "target_pypi": target_pypi,
            "target_dev": target_dev,
            "update_pypi": cli.is_newer(target_pypi, installed_version),
            "update_dev": cli.is_newer(target_dev, installed_version),
        }

    return jsonify({"ok": True, "updates": updates})


@bp.route("/api/actions", methods=["POST"])
def api_actions():
    payload = request.get_json(silent=True) or {}
    action = payload.get("action")

    if action not in {"install", "update", "uninstall"}:
        return jsonify({"ok": False, "error": "Action inconnue."}), 400

    try:
        projects, meta, all_projects = resolve_action_projects(payload)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    # What's really installed for each project, so uninstall removes
    # that package even when its name isn't the expected one.
    installed_by_path = cli.resolve_installed(all_projects, cli.get_installed_plugins())

    if not _action_lock.acquire(blocking=False):
        return jsonify({"ok": False, "error": t("plugins.action_busy")}), 409

    install_mode = payload.get("install_mode") or "pypi"
    dev = install_mode == "dev" or bool(payload.get("dev", False))
    lines = queue.Queue()
    result = {"status": 0}

    def run_action():
        stdout = _routed_stdout()
        stdout.queues[threading.get_ident()] = lines
        try:
            for project in projects:
                if action == "install":
                    rc = cli.install_project(
                        project,
                        token=meta["token"],
                        base=meta["base"],
                        dev=dev,
                        dry_run=False,
                        dev_dir=meta["dev_dir"],
                    )
                elif action == "update":
                    rc = cli.update_project(
                        project,
                        token=meta["token"],
                        base=meta["base"],
                        dev=dev,
                        dry_run=False,
                        dev_dir=meta["dev_dir"],
                    )
                else:
                    installed = installed_by_path.get(project["path"]) or {}
                    rc = cli.uninstall_project(
                        project,
                        dry_run=False,
                        package_name=installed.get("package"),
                    )

                if rc != 0:
                    result["status"] = rc
                    print(f"Echec de {action} pour {project['name']} (code {rc}).")
        except Exception as exc:
            result["status"] = result["status"] or 1
            print(f"Erreur : {exc}")
        finally:
            stdout.queues.pop(threading.get_ident(), None)
            lines.put(None)
            _action_lock.release()

    # The action runs in its own thread (and keeps running if the page
    # is closed mid-install); this response streams what it prints, as
    # newline-delimited JSON: {"type": "log", "text": ...} chunks, then
    # one final {"type": "done", "ok": ..., "status": ...}.
    threading.Thread(target=run_action, name="plugins-action", daemon=True).start()

    def stream():
        finished = False
        while not finished:
            chunks = [lines.get()]
            while True:
                try:
                    chunks.append(lines.get_nowait())
                except queue.Empty:
                    break
            if None in chunks:
                finished = True
                chunks = chunks[:chunks.index(None)]
            if chunks:
                yield json.dumps({"type": "log", "text": "".join(chunks)}) + "\n"

        yield json.dumps({
            "type": "done",
            "ok": result["status"] == 0,
            "status": result["status"],
            "count": len(projects),
        }) + "\n"

    return Response(
        stream(),
        mimetype="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def load_context():
    args = SimpleNamespace(
        config=None,
        group=None,
        token=None,
    )
    config = cli.get_config(args)
    token = cli.get_token(args, config)
    base = cli.get_gitlab_base(config)
    sources = cli.get_group_sources(args, config)

    return {
        "config": config,
        "token": token,
        "base": base,
        "sources": sources,
        "group_path": sources[0][0],
        "dev_dir": cli.get_dev_dir(config),
    }


def load_projects(category=None, installed_only=False):
    ctx = load_context()
    projects, warnings = cli.discover_sources(
        ctx["sources"],
        token=ctx["token"],
        base=ctx["base"],
    )
    remember_discovery(projects, ctx)
    # Over every project, before filtering: see cli.resolve_installed().
    installed_by_path = cli.resolve_installed(projects, cli.get_installed_plugins())
    projects = cli.filter_projects(
        projects,
        category=category,
    )

    enriched = []

    for project in projects:
        installed = installed_by_path[project["path"]]

        if installed_only and not installed:
            continue

        enriched.append(
            {
                "name": project["name"],
                "category": project["category"],
                "pypi_name": project["pypi_name"],
                "path": project["path"],
                "installed": bool(installed),
                "version": installed.get("version", "") if installed else "",
            }
        )

    return enriched, public_meta(ctx, warnings)


def remember_discovery(projects, ctx):
    _last_discovery.update(
        projects=projects,
        token=ctx["token"],
        base=ctx["base"],
    )


def discovered_projects():
    """(projects, token, base) of the last listing, discovering them
    first if nothing was listed yet."""
    if not _last_discovery:
        ctx = load_context()
        projects, _warnings = cli.discover_sources(
            ctx["sources"],
            token=ctx["token"],
            base=ctx["base"],
        )
        remember_discovery(projects, ctx)

    return (
        _last_discovery["projects"],
        _last_discovery["token"],
        _last_discovery["base"],
    )


def resolve_action_projects(payload):
    """(projects to act on, action meta, every discovered project).
    The page sends each plugin's GitLab path as its target - unique,
    unlike names (onepix_spectral_indices and spectral-indices look
    alike to cli.find_project())."""
    ctx = load_context()
    targets = [
        item
        for item in payload.get("targets", [])
        if item
    ]
    category = payload.get("category") or None
    scope = payload.get("scope") or "selected"

    projects, _warnings = cli.discover_sources(
        ctx["sources"],
        token=ctx["token"],
        base=ctx["base"],
    )

    if targets:
        selected = []
        for target in targets:
            matches = cli.find_project(
                projects,
                target,
            )
            if not matches:
                raise RuntimeError(f"Aucun depot trouve pour '{target}'.")
            if len(matches) > 1:
                choices = ", ".join(
                    project["path"]
                    for project in matches
                )
                raise RuntimeError(f"Plusieurs correspondances pour '{target}': {choices}")
            selected.append(matches[0])
        return selected, action_meta(ctx), projects

    if scope == "all":
        return projects, action_meta(ctx), projects

    if scope != "filtered":
        raise RuntimeError("Selectionne au moins un plugin ou choisis une portee.")

    return cli.filter_projects(
        projects,
        category=category,
    ), action_meta(ctx), projects


def public_meta(ctx, warnings=()):
    return {
        "group": ctx["group_path"],
        "groups": [path for path, _category in ctx["sources"]],
        "warnings": list(warnings),
        "base": ctx["base"],
        "config": ctx["config"].get("_config_path"),
        "dev_dir": str(ctx["dev_dir"]),
        "has_token": bool(ctx["token"]),
    }


def action_meta(ctx):
    return {
        "token": ctx["token"],
        "base": ctx["base"],
        "dev_dir": ctx["dev_dir"],
    }
