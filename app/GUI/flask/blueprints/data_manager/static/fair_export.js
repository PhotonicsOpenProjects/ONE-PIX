// ======================================
// FAIR EXPORT + FAIR METADATA
// Needs data_manager.js (selectedCheckboxes, setUIBusy, timestampedFilename)
// ======================================

const FAIR_FORMATS_KEY = "onepix.fairExportFormats";
const FAIR_DEFAULT_FORMATS = ["hdf5"];

let fairFormats = null;


function fairStoredFormats() {

    try {

        const stored = JSON.parse(localStorage.getItem(FAIR_FORMATS_KEY));

        if (Array.isArray(stored)) return stored;

    } catch (error) { /* storage unavailable: defaults */ }

    return FAIR_DEFAULT_FORMATS;
}


function fairStoreFormats(formats) {

    try {

        localStorage.setItem(FAIR_FORMATS_KEY, JSON.stringify(formats));

    } catch (error) { /* not worth failing the export */ }
}


document.querySelectorAll("[data-close-dialog]").forEach(button => {

    button.addEventListener("click", () => button.closest("dialog").close());
});


// ======================================
// EXPORT
// ======================================

async function openExportDialog() {

    if (!selectedCheckboxes().length) {

        ONEPIX.toast(ONEPIX.t("data.toast_none_selected"), "warning");

        return;
    }

    const box = document.getElementById("exportFormats");

    if (!fairFormats) {

        try {

            const response = await fetch("/data_manager/fair/formats");

            fairFormats = await response.json();

        } catch (error) {

            ONEPIX.toast(ONEPIX.t("data.fair.export_failed"), "error");

            return;
        }
    }

    const chosen = fairStoredFormats();

    box.querySelectorAll(".fair-format").forEach(el => el.remove());

    fairFormats.forEach(format => {

        const label = document.createElement("label");

        label.className = "fair-format" + (format.available ? "" : " is-disabled");

        const input = document.createElement("input");

        input.type = "checkbox";
        input.value = format.id;
        input.disabled = !format.available;
        input.checked = format.available && chosen.includes(format.id);

        const text = document.createElement("span");

        const name = document.createElement("span");

        name.className = "fair-format-label";
        name.textContent = `${format.label} (${format.extension})`;

        const hint = document.createElement("span");

        hint.className = "fair-format-hint";

        hint.textContent = format.available
            ? ONEPIX.t("data.fair.fmt_" + format.id)
            : ONEPIX.t("data.fair.unavailable");

        text.appendChild(name);
        text.appendChild(hint);

        label.appendChild(input);
        label.appendChild(text);

        box.appendChild(label);
    });

    document.getElementById("exportDialog").showModal();
}


function fairSkippedText(skipped) {

    // {file: {format: reason}} or {file: "failed: ..."}
    return Object.entries(skipped).map(([file, what]) => {

        const detail = typeof what === "string"
            ? what
            : Object.entries(what).map(([format, reason]) => `${format} (${reason})`).join(", ");

        return `${file}: ${detail}`;

    }).join(" · ");
}


async function runFairExport() {

    const files = selectedCheckboxes().map(el => el.value);

    const formats = Array.from(
        document.querySelectorAll("#exportFormats input:checked")
    ).map(el => el.value);

    if (!formats.length) {

        ONEPIX.toast(ONEPIX.t("data.fair.pick_format"), "warning");

        return;
    }

    fairStoreFormats(formats);

    document.getElementById("exportDialog").close();

    setUIBusy(true);

    try {

        const response = await fetch("/data_manager/export", {

            method: "POST",

            headers: { "Content-Type": "application/json" },

            body: JSON.stringify({ files, formats })
        });

        if (!response.ok) {

            ONEPIX.toast(ONEPIX.t("data.fair.export_failed"), "error");

            return;
        }

        const blob = await response.blob();

        const url = window.URL.createObjectURL(blob);

        const a = document.createElement("a");

        a.href = url;
        a.download = timestampedFilename("onepix_fair", "zip");

        document.body.appendChild(a);
        a.click();
        a.remove();

        window.URL.revokeObjectURL(url);

        ONEPIX.toast(ONEPIX.t("data.fair.exported", { n: files.length }), "success");

        let skipped = {};

        try {

            skipped = JSON.parse(response.headers.get("X-Export-Skipped") || "{}");

        } catch (error) { /* header unreadable: nothing to add */ }

        if (Object.keys(skipped).length) {

            ONEPIX.toast(
                ONEPIX.t("data.fair.skipped", { details: fairSkippedText(skipped) }),
                "warning",
                9000
            );
        }

    } catch (error) {

        console.error(error);

        ONEPIX.toast(ONEPIX.t("data.fair.export_failed"), "error");

    } finally {

        setUIBusy(false);
    }
}


document.getElementById("exportRunBtn").addEventListener("click", runFairExport);


// ======================================
// FAIR METADATA (who / licence)
// ======================================

async function openFairConfig() {

    let data;

    try {

        const response = await fetch("/data_manager/fair/config");

        data = await response.json();

    } catch (error) {

        ONEPIX.toast(ONEPIX.t("data.fair.save_failed"), "error");

        return;
    }

    const form = document.getElementById("fairForm");

    const select = document.getElementById("fairLicense");

    select.textContent = "";

    Object.keys(data.licenses).forEach(id => {

        const option = document.createElement("option");

        option.value = id;
        option.textContent = id;

        select.appendChild(option);
    });

    const config = data.config;

    form.elements.creator_name.value = config.creator_name || "";
    form.elements.creator_orcid.value = config.creator_orcid || "";
    form.elements.affiliation.value = config.affiliation || "";
    form.elements.contact_email.value = config.contact_email || "";
    form.elements.project.value = config.project || "";
    form.elements.keywords.value = (config.keywords || []).join(", ");
    form.elements.license.value = config.license;

    document.getElementById("fairDialog").showModal();
}


document.getElementById("fairForm").addEventListener("submit", async event => {

    event.preventDefault();

    const form = event.target;

    const values = {};

    ["creator_name", "creator_orcid", "affiliation", "contact_email", "project", "keywords", "license"]
        .forEach(key => { values[key] = form.elements[key].value; });

    try {

        const response = await fetch("/data_manager/fair/config", {

            method: "POST",

            headers: { "Content-Type": "application/json" },

            body: JSON.stringify(values)
        });

        const data = await response.json();

        if (!response.ok) {

            const known = ["orcid", "email", "license"];

            ONEPIX.toast(
                known.includes(data.error)
                    ? ONEPIX.t("data.fair.err_" + data.error)
                    : ONEPIX.t("data.fair.save_failed"),
                "error"
            );

            return;
        }

        document.getElementById("fairDialog").close();

        ONEPIX.toast(ONEPIX.t("data.fair.saved"), "success");

    } catch (error) {

        console.error(error);

        ONEPIX.toast(ONEPIX.t("data.fair.save_failed"), "error");
    }
});
