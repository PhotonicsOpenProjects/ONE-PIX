/* ============================================================
   ONE-PIX — shared UI helpers (toast notifications).
   Loaded on every page from global_base.html. Does not touch
   any fetch/API logic — purely presentational.
   ============================================================ */

window.ONEPIX = (function () {

  function t(key, vars) {

    const table = window.ONEPIX_I18N || {};

    let str = Object.prototype.hasOwnProperty.call(table, key)
      ? table[key]
      : key;

    if (vars) {
      Object.keys(vars).forEach(name => {
        str = str.split("{" + name + "}").join(vars[name]);
      });
    }

    return str;
  }

  function ensureRegion() {
    let region = document.getElementById("onepix-toast-region");
    if (!region) {
      region = document.createElement("div");
      region.id = "onepix-toast-region";
      region.setAttribute("aria-live", "polite");
      region.setAttribute("aria-atomic", "false");
      document.body.appendChild(region);
    }
    return region;
  }

  function toast(message, type, duration) {
    type = type || "info";
    duration = duration || 4500;

    const region = ensureRegion();

    const el = document.createElement("div");
    el.className = "onepix-toast toast-" + type;
    el.setAttribute("role", type === "error" ? "alert" : "status");

    const dot = document.createElement("span");
    dot.className =
      "status-dot " +
      (type === "error" ? "is-error" : type === "success" ? "is-success" : "is-idle");

    const msg = document.createElement("span");
    msg.className = "onepix-toast-msg";
    msg.textContent = message;

    el.appendChild(dot);
    el.appendChild(msg);
    region.appendChild(el);

    requestAnimationFrame(() => el.classList.add("is-visible"));

    setTimeout(() => {
      el.classList.remove("is-visible");
      setTimeout(() => el.remove(), 250);
    }, duration);
  }

  return {
    toast: toast,
    t: t,
  };

})();
