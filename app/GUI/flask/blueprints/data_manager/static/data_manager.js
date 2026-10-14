// ======================================
// STATE
// ======================================

let allFiles = [];


// ======================================
// TIMESTAMPED FILENAME
// ======================================

function timestampedFilename(prefix, extension) {

    const now = new Date();

    const pad = n => String(n).padStart(2, "0");

    const stamp =
        `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}` +
        `_${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`;

    return `${prefix}_${stamp}.${extension}`;
}

// ======================================
// HTML ESCAPING (file names come from the server, but a file's on-disk
// name is user-controlled at upload time — never trust it in innerHTML)
// ======================================

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

// ======================================
// UI LOCK
// ======================================

function setUIBusy(isBusy) {

    const overlay =
        document.getElementById(
            "loadingOverlay"
        );

    overlay.style.display =
        isBusy ? "flex" : "none";

    const elements =
        document.querySelectorAll(
            "button, input"
        );

    elements.forEach(el => {

        el.disabled = isBusy;
    });
}


// ======================================
// LOAD FILES
// ======================================

async function loadFiles() {

    const response = await fetch(
        "/data_manager/files"
    );

    const files =
        await response.json();

    allFiles = files;

    renderFiles();
}


function renderFiles() {

    const container =
        document.getElementById(
            "fileList"
        );

    const emptyState =
        document.getElementById(
            "fileListEmpty"
        );

    const query = (
        document.getElementById("fileSearch").value || ""
    ).trim().toLowerCase();

    const visibleFiles = query
        ? allFiles.filter(f => f.name.toLowerCase().includes(query))
        : allFiles;

    container.innerHTML = "";

    if (allFiles.length === 0) {

        emptyState.hidden = false;
        emptyState.querySelector(".empty-state-title").textContent = ONEPIX.t("data.empty_title");
        emptyState.querySelector(".empty-state-sub").textContent =
            ONEPIX.t("data.empty_sub");
        updateSelectionUI();
        return;
    }

    if (visibleFiles.length === 0) {

        emptyState.hidden = false;
        emptyState.querySelector(".empty-state-title").textContent = ONEPIX.t("data.empty_search_title");
        emptyState.querySelector(".empty-state-sub").textContent =
            ONEPIX.t("data.empty_search_sub");
        updateSelectionUI();
        return;
    }

    emptyState.hidden = true;

    visibleFiles.forEach(file => {

        const row =
            document.createElement(
                "div"
            );

        row.className =
            "file-item";

        const badgeClass =
            file.type === "reconstruction" ? "badge-primary" : "badge-neutral";

        row.innerHTML = `

            <input
                type="checkbox"
                class="file-checkbox"
                value="${escapeAttr(file.name)}"
                aria-label="${escapeAttr(ONEPIX.t("data.select_file_aria", {name: file.name}))}"
            >

            <span class="badge ${badgeClass} file-type">
                ${escapeHtml(fileTypeLabel(file.type))}
            </span>

            <div class="file-name">
                ${escapeHtml(file.name)}
            </div>

            <div class="file-date">
                ${escapeHtml(formatModified(file.modified))}
            </div>

            <div class="file-size">
                ${escapeHtml(formatSize(file.size))}
            </div>
        `;

        container.appendChild(
            row
        );
    });

    updateSelectionUI();
}


// ======================================
// SEARCH (client-side filter, no backend call)
// ======================================

document
.getElementById("fileSearch")
.addEventListener("input", renderFiles);


// ======================================
// SELECTION STATE
// ======================================

function selectedCheckboxes() {

    return Array.from(
        document.querySelectorAll(
            ".file-checkbox:checked"
        )
    );
}


function updateSelectionUI() {

    const count = selectedCheckboxes().length;

    const bar =
        document.getElementById(
            "selectionBar"
        );

    document.getElementById(
        "selectionCount"
    ).textContent =
        count === 1
            ? ONEPIX.t("data.selection_count_singular")
            : ONEPIX.t("data.selection_count_plural", {n: count});

    bar.hidden = count === 0;

    document.getElementById(
        "downloadBtn"
    ).disabled = count === 0;

    document.getElementById(
        "removeBtn"
    ).disabled = count === 0;
}


document
.getElementById("fileList")
.addEventListener("change", event => {

    if (event.target.classList.contains("file-checkbox")) {

        updateSelectionUI();
    }
});


// ======================================
// SELECT ALL
// ======================================

function selectAllFiles() {

    const checkboxes =

        document.querySelectorAll(
            ".file-checkbox"
        );

    checkboxes.forEach(cb => {

        cb.checked = true;
    });

    updateSelectionUI();
}


// ======================================
// DESELECT ALL
// ======================================

function deselectAllFiles() {

    const checkboxes =

        document.querySelectorAll(
            ".file-checkbox"
        );

    checkboxes.forEach(cb => {

        cb.checked = false;
    });

    updateSelectionUI();
}


// ======================================
// DOWNLOAD
// ======================================

async function downloadSelected() {

    const checked = selectedCheckboxes().map(el => el.value);

    if (!checked.length) {

        ONEPIX.toast(ONEPIX.t("data.toast_none_selected"), "warning");

        return;
    }

    setUIBusy(true);

    try {

        const response = await fetch(

            "/data_manager/download",

            {
                method: "POST",

                headers: {
                    "Content-Type":
                    "application/json"
                },

                body: JSON.stringify({
                    files: checked
                })
            }
        );

        if (!response.ok) {

            ONEPIX.toast(
                ONEPIX.t("data.toast_download_failed"),
                "error"
            );

            return;
        }

        const blob =
            await response.blob();

        const url =
            window.URL.createObjectURL(
                blob
            );

        const a =
            document.createElement("a");

        a.href = url;

        a.download =
            timestampedFilename("onepix_data", "zip");

        document.body.appendChild(a);

        a.click();

        a.remove();

        window.URL.revokeObjectURL(
            url
        );

        ONEPIX.toast(ONEPIX.t("data.toast_download_success", {n: checked.length}), "success");

    } catch(error) {

        console.error(error);

        ONEPIX.toast(
            ONEPIX.t("data.toast_download_failed"),
            "error"
        );

    } finally {

        setUIBusy(false);
    }
}


// ======================================
// REMOVE SELECTED
// ======================================

async function removeSelected() {

    const checked = selectedCheckboxes().map(el => el.value);

    if (!checked.length) {

        ONEPIX.toast(ONEPIX.t("data.toast_none_selected"), "warning");

        return;
    }

    const confirmDelete = confirm(

        ONEPIX.t("data.confirm_delete", {n: checked.length})
    );

    if (!confirmDelete) {

        return;
    }

    setUIBusy(true);

    try {

        const response = await fetch(

            "/data_manager/delete",

            {
                method: "POST",

                headers: {
                    "Content-Type":
                    "application/json"
                },

                body: JSON.stringify({
                    files: checked
                })
            }
        );

        if (!response.ok) {

            ONEPIX.toast(
                ONEPIX.t("data.toast_delete_failed"),
                "error"
            );

            return;
        }

        ONEPIX.toast(ONEPIX.t("data.toast_delete_success", {n: checked.length}), "success");

        await loadFiles();

    } catch(error) {

        console.error(error);

        ONEPIX.toast(
            ONEPIX.t("data.toast_delete_failed"),
            "error"
        );

    } finally {

        setUIBusy(false);
    }
}


// ======================================
// OPEN UPLOAD DIALOG
// ======================================

function openUploadDialog() {

    document
    .getElementById(
        "uploadInput"
    )
    .click();
}


// ======================================
// UPLOAD (shared by the file picker and drag & drop)
// ======================================

async function uploadFiles(files) {

    if (!files.length) {

        return;
    }

    setUIBusy(true);

    try {

        const formData =
            new FormData();

        for (const file of files) {

            formData.append(
                "files",
                file
            );
        }

        const response = await fetch(

            "/data_manager/upload",

            {
                method: "POST",

                body: formData
            }
        );

        if (!response.ok) {

            ONEPIX.toast(
                ONEPIX.t("data.toast_upload_failed"),
                "error"
            );

            return;
        }

        ONEPIX.toast(ONEPIX.t("data.toast_upload_success", {n: files.length}), "success");

        await loadFiles();

    } catch(error) {

        console.error(error);

        ONEPIX.toast(
            ONEPIX.t("data.toast_upload_failed"),
            "error"
        );

    } finally {

        setUIBusy(false);
    }
}


document
.getElementById(
    "uploadInput"
)
.addEventListener(

    "change",

    function () {

        uploadFiles(this.files);

        this.value = "";
    }
);


// ======================================
// DRAG & DROP UPLOAD
// ======================================

const dropZone = document.getElementById("dropZone");

["dragenter", "dragover"].forEach(eventName => {

    dropZone.addEventListener(eventName, event => {

        event.preventDefault();

        dropZone.classList.add("is-drag-over");
    });
});

["dragleave", "drop"].forEach(eventName => {

    dropZone.addEventListener(eventName, event => {

        event.preventDefault();

        dropZone.classList.remove("is-drag-over");
    });
});

dropZone.addEventListener("drop", event => {

    const files = event.dataTransfer?.files;

    if (files && files.length) {

        uploadFiles(files);
    }
});


// ======================================
// INIT
// ======================================

loadFiles();

// ======================================
// DISPLAY FORMATTING
// ======================================

function fileTypeLabel(type) {

    const key = "data.type_" + type;
    const label = ONEPIX.t(key);

    return label === key ? type : label;
}


// The API reports sizes in KB.
function formatSize(kb) {

    const format = new Intl.NumberFormat(
        window.ONEPIX_LANG || undefined,
        {maximumFractionDigits: 1}
    );

    if (kb < 1024) return format.format(kb) + " KB";
    if (kb < 1024 * 1024) return format.format(kb / 1024) + " MB";
    return format.format(kb / (1024 * 1024)) + " GB";
}


// The API reports modification times as Unix seconds.
function formatModified(seconds) {

    if (!seconds) return "";

    return new Date(seconds * 1000).toLocaleString(
        window.ONEPIX_LANG || undefined,
        {dateStyle: "medium", timeStyle: "short"}
    );
}
