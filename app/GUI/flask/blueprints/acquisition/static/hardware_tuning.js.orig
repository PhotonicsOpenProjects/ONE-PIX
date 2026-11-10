/* ============================================================
   ONE-PIX — Spectrometer integration-time live tuning panel.
   Polls /acquisition/hardware/tuning/snapshot while a session is
   running and drives the Plotly live spectrum chart.
   ============================================================ */

(function () {

  const urls = window.ONEPIX_TUNING_URLS;
  if (!urls) return;

  const startBtn = document.getElementById("tuningStartBtn");
  const stopBtn = document.getElementById("tuningStopBtn");
  const slider = document.getElementById("tuningIntegrationSlider");
  const numberInput = document.getElementById("tuningIntegrationInput");
  const statusBadge = document.getElementById("tuningStatusBadge");
  const statusLabel = document.getElementById("tuningStatusLabel");
  const errorBox = document.getElementById("tuningErrorBox");
  const chartEl = document.getElementById("tuningChart");
  const emptyState = document.getElementById("tuningEmptyState");
  const peakValue = document.getElementById("tuningPeakValue");
  const peakPctValue = document.getElementById("tuningPeakPctValue");
  const recommendedValue = document.getElementById("tuningRecommendedValue");
  const applyBtn = document.getElementById("tuningApplyBtn");
  const applyStatus = document.getElementById("tuningApplyStatus");

  const POLL_INTERVAL_MS = 400;

  let pollTimer = null;
  let running = false;
  let chartInitialized = false;
  let lastRecommended = null;
  let integrationEditTimer = null;

  const STATUS_MAP = {
    idle: ["badge-neutral", "is-idle", () => ONEPIX.t("acquisition_settings.tuning.status_idle")],
    low: ["badge-warning", "is-busy", () => ONEPIX.t("acquisition_settings.tuning.status_low")],
    ok: ["badge-success", "is-success", () => ONEPIX.t("acquisition_settings.tuning.status_ok")],
    saturation: ["badge-danger", "is-error", () => ONEPIX.t("acquisition_settings.tuning.status_saturation")],
    error: ["badge-danger", "is-error", () => ONEPIX.t("acquisition_settings.tuning.status_error")],
  };

  function setStatus(state) {
    const [badgeClass, dotClass, label] = STATUS_MAP[state] || STATUS_MAP.idle;

    statusBadge.classList.remove("badge-neutral", "badge-warning", "badge-success", "badge-danger");
    statusBadge.querySelector(".status-dot").classList.remove("is-idle", "is-busy", "is-success", "is-error");

    statusBadge.classList.add(badgeClass);
    statusBadge.querySelector(".status-dot").classList.add(dotClass);
    statusLabel.textContent = label();
  }

  function setRunningUI(isRunning) {
    running = isRunning;
    startBtn.disabled = isRunning;
    stopBtn.disabled = !isRunning;
    slider.disabled = !isRunning;
    numberInput.disabled = !isRunning;
    applyBtn.disabled = !isRunning || lastRecommended === null;
  }

  function showError(message) {
    if (!message) {
      errorBox.hidden = true;
      errorBox.textContent = "";
      return;
    }
    errorBox.hidden = false;
    errorBox.textContent = message;
  }

  function ensureChart() {
    if (chartInitialized || typeof Plotly === "undefined") return;

    Plotly.newPlot(
      chartEl,
      [{ x: [], y: [], mode: "lines", line: { width: 2 } }],
      {
        margin: { t: 10, r: 10, b: 40, l: 50 },
        xaxis: { title: ONEPIX.t("acquisition_settings.tuning.chart_xaxis") },
        yaxis: { title: ONEPIX.t("acquisition_settings.tuning.chart_yaxis") },
      },
      { displayModeBar: false, responsive: true }
    );

    chartInitialized = true;
  }

  function updateChart(spectrum) {
    if (!spectrum) return;

    ensureChart();
    emptyState.style.display = "none";
    chartEl.style.display = "block";

    Plotly.react(
      chartEl,
      [{ x: spectrum.wavelengths, y: spectrum.intensities, mode: "lines", line: { width: 2 } }],
      chartEl.layout,
      { displayModeBar: false, responsive: true }
    );
  }

  function updateMetrics(spectrum) {
    if (!spectrum) {
      peakValue.textContent = "—";
      peakPctValue.textContent = "—";
      recommendedValue.textContent = "—";
      lastRecommended = null;
      return;
    }

    peakValue.textContent = Math.round(spectrum.peak);
    peakPctValue.textContent = `${spectrum.peak_pct}%`;
    recommendedValue.textContent = `${spectrum.recommended_integration_time_ms} ms`;
    lastRecommended = spectrum.recommended_integration_time_ms;

    // Reflect the live integration time in the controls unless the user is
    // actively dragging/typing (avoid fighting their input mid-edit).
    if (document.activeElement !== slider && document.activeElement !== numberInput) {
      slider.value = spectrum.integration_time_ms;
      numberInput.value = spectrum.integration_time_ms;
    }
  }

  function applySnapshot(data) {
    if (data.bounds) {
      slider.min = numberInput.min = data.bounds.min_integration_time_ms;
      slider.max = numberInput.max = data.bounds.max_integration_time_ms;
    }

    setRunningUI(data.running);
    showError(data.error);

    if (!data.running) {
      setStatus(data.error ? "error" : "idle");
      stopPolling();
      return;
    }

    if (!pollTimer) startPolling();

    updateChart(data.spectrum);
    updateMetrics(data.spectrum);
    setStatus(data.spectrum ? data.spectrum.status : "idle");
    applyBtn.disabled = lastRecommended === null;
  }

  async function poll() {
    try {
      const response = await fetch(urls.snapshot);
      const data = await response.json();
      applySnapshot(data);
    } catch (error) {
      console.error(error);
    }
  }

  function startPolling() {
    stopPolling();
    pollTimer = setInterval(poll, POLL_INTERVAL_MS);
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  async function start() {
    startBtn.disabled = true;
    showError(null);

    try {
      // No integration_time_ms override here: the session starts from
      // whatever is already configured (acquisition_parameters.json), and
      // the controls sync to that real value once the first snapshot
      // comes back. Explicit user changes go through pushIntegrationTime().
      const response = await fetch(urls.start, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      const data = await response.json();

      if (!data.ok) {
        showError(data.error || ONEPIX.t("acquisition_settings.tuning.toast_start_failed"));
        setRunningUI(false);
        return;
      }

      applySnapshot(data);

    } catch (error) {
      console.error(error);
      showError(String(error));
      setRunningUI(false);
    }
  }

  async function stop(useBeacon) {
    stopPolling();

    if (useBeacon && navigator.sendBeacon) {
      navigator.sendBeacon(urls.stop);
      setRunningUI(false);
      return;
    }

    try {
      const response = await fetch(urls.stop, { method: "POST" });
      const data = await response.json();
      applySnapshot(data);
    } catch (error) {
      console.error(error);
      setRunningUI(false);
    }
  }

  async function pushIntegrationTime(value) {
    try {
      const response = await fetch(urls.integrationTime, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ integration_time_ms: value }),
      });

      const data = await response.json();

      if (!data.ok) {
        showError(data.error || ONEPIX.t("acquisition_settings.tuning.toast_integration_failed"));
        return;
      }

      showError(null);

    } catch (error) {
      console.error(error);
      showError(String(error));
    }
  }

  function onIntegrationInput(event) {
    const value = Number(event.target.value);

    // Keep both controls in sync immediately (UI feedback), but debounce
    // the network call so dragging the slider doesn't flood the backend.
    slider.value = value;
    numberInput.value = value;

    clearTimeout(integrationEditTimer);
    integrationEditTimer = setTimeout(() => pushIntegrationTime(value), 150);
  }

  async function applyToSettings() {
    if (lastRecommended === null) return;

    const value = Number(numberInput.value);
    applyBtn.disabled = true;

    try {
      const response = await fetch(urls.apply, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ integration_time_ms: value }),
      });

      const data = await response.json();

      if (!data.ok) {
        applyStatus.textContent = data.error || ONEPIX.t("acquisition_settings.tuning.toast_apply_failed");
        ONEPIX.toast(applyStatus.textContent, "error");
        return;
      }

      applyStatus.textContent = ONEPIX.t("acquisition_settings.tuning.apply_success");
      ONEPIX.toast(ONEPIX.t("acquisition_settings.tuning.toast_apply_success"), "success");

    } catch (error) {
      console.error(error);
      applyStatus.textContent = String(error);

    } finally {
      applyBtn.disabled = false;
    }
  }

  startBtn.addEventListener("click", start);
  stopBtn.addEventListener("click", () => stop(false));
  slider.addEventListener("input", onIntegrationInput);
  numberInput.addEventListener("change", onIntegrationInput);
  applyBtn.addEventListener("click", applyToSettings);

  // Best-effort cleanup: if the user navigates away or closes the tab
  // while a tuning session is running, stop it server-side too (otherwise
  // the background thread, the projector pattern and the hardware lock
  // would keep running with nobody watching).
  window.addEventListener("pagehide", () => {
    if (running) stop(true);
  });

  setRunningUI(false);
  setStatus("idle");
  poll();

})();
