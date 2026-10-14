const state = {
  plugins: [],
  // GitLab path -> newest available versions, from /api/updates.
  updates: {},
  updatesStatus: "loading",
};

const body = document.querySelector("#pluginsBody");
const output = document.querySelector("#output");
const metaLine = document.querySelector("#metaLine");
const categoryFilter = document.querySelector("#categoryFilter");
const installedFilter = document.querySelector("#installedFilter");
const updatesFilter = document.querySelector("#updatesFilter");
const scopeSelect = document.querySelector("#scopeSelect");
const installMode = document.querySelector("#installMode");
const selectAll = document.querySelector("#selectAll");
const pluginCount = document.querySelector("#pluginCount");
const selectedCount = document.querySelector("#selectedCount");
const updatesCount = document.querySelector("#updatesCount");
const statusPill = document.querySelector("#statusPill");

function queryParams() {
  const params = new URLSearchParams();
  if (categoryFilter.value) params.set("category", categoryFilter.value);
  if (installedFilter.checked) params.set("installed", "1");
  return params;
}

// keepConsole: refresh the list after an action without wiping its log.
// refreshUpdates: ask PyPI/GitLab again instead of the server's cache.
async function loadPlugins({keepConsole = false, refreshUpdates = false} = {}) {
  setStatus("loading");
  if (!keepConsole) output.textContent = ONEPIX.t("plugins.meta_loading");
  selectAll.checked = false;

  const response = await fetch(`/plugins_manager/api/plugins?${queryParams().toString()}`);
  const data = await response.json();

  if (!data.ok) {
    setStatus("error");
    const message = data.error || ONEPIX.t("plugins.unknown_error");
    if (keepConsole) appendOutput(message + "\n");
    else output.textContent = message;
    return;
  }

  state.plugins = data.plugins;
  renderPlugins();

  const tokenState = data.meta.has_token ? ONEPIX.t("plugins.token_ok") : ONEPIX.t("plugins.token_missing");
  metaLine.textContent = `${data.meta.group} - ${tokenState} - ${ONEPIX.t("plugins.dev_dir_label")} ${data.meta.dev_dir} - ${state.plugins.length} ${ONEPIX.t("plugins.plugin_suffix")}`;
  // A plugin group that couldn't be read (e.g. private without a token)
  // doesn't block the others - say so instead of just missing plugins.
  const warnings = data.meta.warnings || [];
  if (!keepConsole) output.textContent = [ONEPIX.t("plugins.console_ready"), ...warnings].join("\n");
  setStatus("ready");
  updateCounts();
  loadUpdates({refresh: refreshUpdates});
}

let updatesRequest = 0;

// Available versions come from PyPI and GitLab, slower than the list
// itself: fetched once it's shown, then filled in.
async function loadUpdates({refresh = false} = {}) {
  const request = ++updatesRequest;
  state.updatesStatus = "loading";
  updateCounts();

  try {
    const response = await fetch(`/plugins_manager/api/updates${refresh ? "?refresh=1" : ""}`);
    const data = await response.json();
    if (request !== updatesRequest) return;
    if (!data.ok) throw new Error(data.error);
    state.updates = data.updates;
    state.updatesStatus = "ready";
  } catch (error) {
    if (request !== updatesRequest) return;
    state.updatesStatus = "error";
  }

  renderPlugins();
  updateCounts();
}

// What an update would install in the selected install mode, and
// whether that's newer than the installed version.
function updateInfo(plugin) {
  const info = state.updates[plugin.path];
  if (!info) return {available: "", hasUpdate: false, title: ""};

  const dev = installMode.value === "dev";
  return {
    available: (dev ? info.target_dev : info.target_pypi) || "",
    hasUpdate: plugin.installed && (dev ? info.update_dev : info.update_pypi),
    title: ONEPIX.t("plugins.version_available", {pypi: info.pypi || "–", git: info.git || "–"}),
  };
}

function visiblePlugins() {
  if (!updatesFilter.checked) return state.plugins;
  return state.plugins.filter((plugin) => updateInfo(plugin).hasUpdate);
}

function renderPlugins() {
  // Rows are rebuilt when available versions arrive: keep the selection.
  const selected = new Set(selectedTargets());
  body.replaceChildren();

  for (const plugin of visiblePlugins()) {
    const update = updateInfo(plugin);

    let version = escapeHtml(plugin.version || "-");
    if (update.hasUpdate) {
      version += ` <span class="version-next">→ ${escapeHtml(update.available)}</span>`;
    } else if (!plugin.installed && update.available) {
      version = `<span class="version-available">${escapeHtml(update.available)}</span>`;
    }

    let pill = `<span class="pill off">${ONEPIX.t("plugins.pill_missing")}</span>`;
    if (update.hasUpdate) {
      pill = `<span class="pill update">${ONEPIX.t("plugins.pill_update")}</span>`;
    } else if (plugin.installed) {
      pill = `<span class="pill">${ONEPIX.t("plugins.pill_installed")}</span>`;
    }

    const row = document.createElement("tr");
    row.innerHTML = `
      <td><input class="plugin-check" type="checkbox" value="${escapeAttr(plugin.path)}" aria-label="${escapeAttr(plugin.name)}"></td>
      <td><strong>${escapeHtml(plugin.name)}</strong></td>
      <td>${escapeHtml(plugin.category)}</td>
      <td class="package">${escapeHtml(plugin.pypi_name)}</td>
      <td class="version" title="${escapeAttr(update.title)}">${version}</td>
      <td>${pill}</td>
      <td class="path">${escapeHtml(plugin.path)}</td>
    `;
    row.querySelector(".plugin-check").checked = selected.has(plugin.path);
    body.append(row);
  }

  for (const checkbox of document.querySelectorAll(".plugin-check")) {
    checkbox.addEventListener("change", updateCounts);
  }
}

// GitLab paths: unique, unlike plugin names.
function selectedTargets() {
  return [...document.querySelectorAll(".plugin-check:checked")].map((input) => input.value);
}

function updateCounts() {
  const selected = selectedTargets().length;
  const shown = visiblePlugins().length;
  pluginCount.textContent = shown === 1
    ? ONEPIX.t("plugins.plugin_count_singular")
    : ONEPIX.t("plugins.plugin_count_plural", {n: shown});
  selectedCount.textContent = ONEPIX.t("plugins.selected_count", {n: selected});

  let text = ONEPIX.t("plugins.updates_checking");
  let tone = "badge-neutral";
  if (state.updatesStatus === "error") {
    text = ONEPIX.t("plugins.updates_failed");
  } else if (state.updatesStatus === "ready") {
    const updates = state.plugins.filter((plugin) => updateInfo(plugin).hasUpdate).length;
    if (updates === 0) {
      text = ONEPIX.t("plugins.updates_none");
      tone = "badge-success";
    } else {
      text = updates === 1
        ? ONEPIX.t("plugins.updates_count_singular")
        : ONEPIX.t("plugins.updates_count_plural", {n: updates});
      tone = "badge-warning";
    }
  }
  updatesCount.textContent = text;
  updatesCount.className = `badge ${tone}`;
}

async function runAction(action) {
  // "Filtered" with the updates-only filter on means the rows shown,
  // which the server's category filter alone can't express.
  const scope = scopeSelect.value;
  const onlyShown = scope === "filtered" && updatesFilter.checked;
  const payload = {
    action,
    targets: scope === "selected" ? selectedTargets()
      : onlyShown ? visiblePlugins().map((plugin) => plugin.path)
      : [],
    scope,
    category: categoryFilter.value,
    install_mode: installMode.value,
  };

  if ((scope === "selected" || onlyShown) && payload.targets.length === 0) {
    output.textContent = ONEPIX.t("plugins.none_selected");
    return;
  }

  setStatus("running");
  output.textContent = ONEPIX.t("plugins.executing");

  const response = await fetch("/plugins_manager/api/actions", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });

  // Errors before the action starts (bad request, another action
  // already running) come back as a single JSON object.
  if (!response.ok || (response.headers.get("Content-Type") || "").includes("application/json")) {
    const data = await response.json();
    output.textContent = data.error || ONEPIX.t("plugins.unknown_error");
    setStatus("error");
    return;
  }

  output.textContent = "";
  const result = await readActionStream(response);

  if (!result) {
    // Stream cut before the end (server restarted, network drop): the
    // action itself may still have completed on the server.
    appendOutput("\n" + ONEPIX.t("plugins.unknown_error") + "\n");
    setStatus("error");
    return;
  }

  if (!result.ok) {
    setStatus("error");
    return;
  }

  appendOutput(ONEPIX.t("plugins.done") + "\n");
  await loadPlugins({keepConsole: true});
}

// The response is newline-delimited JSON: {"type": "log", "text"} chunks
// as pip/git print them, then one {"type": "done", ok, status}. Returns
// that final object, or null if the stream ends without it.
async function readActionStream(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result = null;

  for (;;) {
    const {value, done} = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, {stream: true});

    let newline;
    while ((newline = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, newline);
      buffer = buffer.slice(newline + 1);
      if (!line.trim()) continue;

      const message = JSON.parse(line);
      if (message.type === "log") {
        appendOutput(message.text);
      } else if (message.type === "done") {
        result = message;
      }
    }
  }

  return result;
}

// Follows new output like a terminal, unless the user scrolled up to
// read something earlier.
function appendOutput(text) {
  const atBottom = output.scrollHeight - output.scrollTop - output.clientHeight < 24;
  output.textContent += text;
  if (atBottom) output.scrollTop = output.scrollHeight;
}

function setStatus(stateKey) {
  const labels = {
    ready: ONEPIX.t("plugins.status_ready"),
    loading: ONEPIX.t("plugins.status_loading"),
    running: ONEPIX.t("plugins.status_running"),
    error: ONEPIX.t("plugins.status_error"),
  };
  statusPill.textContent = labels[stateKey] || stateKey;
  statusPill.dataset.state = stateKey;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[char]));
}

function escapeAttr(value) {
  return escapeHtml(value);
}

document.querySelector("#refreshButton").addEventListener("click", () => loadPlugins({refreshUpdates: true}));
categoryFilter.addEventListener("change", () => loadPlugins());
installedFilter.addEventListener("change", () => loadPlugins());

// Both only change which rows count as updatable: no reload needed.
for (const control of [updatesFilter, installMode]) {
  control.addEventListener("change", () => {
    renderPlugins();
    updateCounts();
  });
}

selectAll.addEventListener("change", () => {
  for (const checkbox of document.querySelectorAll(".plugin-check")) {
    checkbox.checked = selectAll.checked;
  }
  updateCounts();
});

for (const button of document.querySelectorAll("[data-action]")) {
  button.addEventListener("click", () => runAction(button.dataset.action));
}

loadPlugins();
