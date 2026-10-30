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
  const patternSelect = document.getElementById("tuningPatternSelect");
  const framesBox = document.getElementById("tuningFrames");
  const frameWarning = document.getElementById("tuningFrameWarning");
  const stabilityValue = document.getElementById("tuningStabilityValue");
  const patternValue = document.getElementById("tuningPatternValue");
  const adviceBox = document.getElementById("tuningAdvice");
  const useRecommendedBtn = document.getElementById("tuningUseRecommendedBtn");

  const POLL_INTERVAL_MS = 400;

  let pollTimer = null;
  let running = false;
  let chartInitialized = false;
  let lastRecommended = null;
  let lastAdvice = null;
  let frameMultiples = [];
  let framesKey = "";
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
    patternSelect.disabled = isRunning;          // the pattern is chosen when the measurement starts
    applyBtn.disabled = !isRunning || lastRecommended === null;
    useRecommendedBtn.disabled = !isRunning || !lastAdvice;
    framesBox.querySelectorAll("button").forEach(b => { b.disabled = !isRunning; });
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

  function fmt(value) {
    return String(Number(Number(value).toFixed(2)));
  }

  function nearestMultiple(value) {
    if (!frameMultiples.length) return null;
    return frameMultiples.reduce((best, ms) => Math.abs(ms - value) < Math.abs(best - value) ? ms : best);
  }

  // The chips are the whole numbers of display frames: the integration times that average out the
  // projector's flicker. The one matching the current integration time is highlighted.
  function renderFrameChips(current) {
    const active = frameMultiples.findIndex(ms => Math.abs(ms - current) < 0.05);
    const key = frameMultiples.join(",") + "|" + active;
    if (key === framesKey) return;
    framesKey = key;

    framesBox.textContent = "";
    frameMultiples.forEach((ms, index) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "btn btn-outline btn-sm" + (index === active ? " is-active" : "");
      chip.textContent = `${fmt(ms)} ms`;
      chip.title = ONEPIX.t("acquisition_settings.tuning.frames_chip_title", { n: index + 1 });
      chip.dataset.ms = ms;
      chip.disabled = !running;
      framesBox.appendChild(chip);
    });
  }

  function brightText(advice) {
    return advice.suggested_max_gray_level
      ? ONEPIX.t("acquisition_settings.tuning.advice_too_bright_level", {
          level: advice.suggested_max_gray_level, current: advice.current_max_gray_level })
      : ONEPIX.t("acquisition_settings.tuning.advice_too_bright");
  }

  function setNote(box, kind, text) {
    if (!text) {
      box.hidden = true;
      box.textContent = "";
      return;
    }
    box.hidden = false;
    box.className = "tuning-note" + (kind ? ` tuning-note-${kind}` : "");
    box.textContent = text;
  }

  function renderNotes(spectrum) {
    if (!spectrum) {
      setNote(frameWarning, null, "");
      setNote(adviceBox, null, "");
      return;
    }

    if (spectrum.is_whole_frames === false) {
      setNote(frameWarning, "warning", ONEPIX.t("acquisition_settings.tuning.frame_warning", {
        ms: fmt(spectrum.integration_time_ms),
        frame: fmt(frameMultiples[0] || 0),
        near: fmt(nearestMultiple(spectrum.integration_time_ms) || 0),
      }));
    } else {
      setNote(frameWarning, null, "");
    }

    const advice = spectrum.advice;
    if (!advice) {
      setNote(adviceBox, null, "");
    } else if (advice.saturated) {
      let text = ONEPIX.t("acquisition_settings.tuning.advice_saturated", { ms: fmt(advice.recommended_ms) });
      if (advice.too_bright) text += " " + brightText(advice);
      setNote(adviceBox, "danger", text);
    } else if (advice.too_bright) {
      setNote(adviceBox, "danger", brightText(advice));
    } else if (spectrum.stability_status === "poor" || spectrum.stability_status === "fair") {
      setNote(adviceBox, "warning", ONEPIX.t("acquisition_settings.tuning.advice_unstable", {
        pct: fmt(spectrum.stability_pct) }));
    } else if (spectrum.stability_status === "good" && spectrum.is_whole_frames && spectrum.status === "ok") {
      setNote(adviceBox, "good", ONEPIX.t("acquisition_settings.tuning.advice_ok"));
    } else {
      setNote(adviceBox, null, "");
    }
  }

  function updateMetrics(spectrum) {
    if (!spectrum) {
      peakValue.textContent = "—";
      peakPctValue.textContent = "—";
      recommendedValue.textContent = "—";
      stabilityValue.textContent = "—";
      stabilityValue.className = "";
      lastRecommended = null;
      lastAdvice = null;
      renderNotes(null);
      return;
    }

    peakValue.textContent = Math.round(spectrum.peak);
    peakPctValue.textContent = `${spectrum.peak_pct}%`;
    lastRecommended = spectrum.recommended_integration_time_ms;
    lastAdvice = spectrum.advice || null;

    recommendedValue.textContent = lastAdvice
      ? `${fmt(lastAdvice.recommended_ms)} ms · ${ONEPIX.t("acquisition_settings.tuning.frames_count", { n: lastAdvice.frames })}`
      : `${spectrum.recommended_integration_time_ms} ms`;

    if (spectrum.stability_pct === null || spectrum.stability_pct === undefined) {
      stabilityValue.textContent = ONEPIX.t("acquisition_settings.tuning.stability_measuring");
      stabilityValue.className = "";
    } else {
      stabilityValue.textContent =
        `${fmt(spectrum.stability_pct)} % · ${ONEPIX.t("acquisition_settings.tuning.stability_" + spectrum.stability_status)}`;
      stabilityValue.className = `tuning-stability-${spectrum.stability_status}`;
    }

    renderFrameChips(spectrum.integration_time_ms);
    renderNotes(spectrum);
    useRecommendedBtn.disabled = !running || !lastAdvice;

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
      numberInput.step = "any";                  // whole frames are not whole milliseconds (16.67, 33.33...)
      frameMultiples = data.bounds.frame_multiples_ms || [];
      renderFrameChips(Number(numberInput.value));
    }

    patternValue.textContent = data.pattern
      ? ONEPIX.t("acquisition_settings.tuning.pattern_" + data.pattern)
      : "—";

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
        body: JSON.stringify({ pattern: patternSelect.value }),
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

  function setIntegration(value) {
    slider.value = value;
    numberInput.value = value;
    renderFrameChips(value);
    clearTimeout(integrationEditTimer);
    pushIntegrationTime(value);
  }

  framesBox.addEventListener("click", (event) => {
    const chip = event.target.closest("button[data-ms]");
    if (chip && running) setIntegration(Number(chip.dataset.ms));
  });

  useRecommendedBtn.addEventListener("click", () => {
    if (lastAdvice) setIntegration(lastAdvice.recommended_ms);
  });

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
