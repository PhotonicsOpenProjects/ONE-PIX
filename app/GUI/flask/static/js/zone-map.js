/* ============================================================
   ONE-PIX — Zone map for zone-based results.

   For results measured zone by zone (one spectrum per zone plus its
   mask - see zones.py), shows the photo with every zone tinted and
   outlined in the color of its spectrum in the chart
   (spectra-chart.js) and labelled with its name. Hovering a zone
   names it; clicking it calls back, so the page can isolate its
   spectrum.

   The map is composed on a canvas and handed to the page's existing
   <img> as a data URL, so the viewer's zoom and fullscreen keep
   working on it unchanged.

   Needs spectra-chart.js loaded first.
   ============================================================ */

(function () {

    var FILL_ALPHA = 0.45;
    var DESATURATION = 0.7;
    var FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";

    // <img> -> its map: {data, labels, photo, onZoneClick, tooltip, shown}
    var maps = new Map();

    function cssVar(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }

    function toRgb(color) {
        var m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(color);
        return m ? [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)] : [128, 128, 128];
    }

    function loadImage(url) {
        return new Promise(function (resolve, reject) {
            var img = new Image();
            img.onload = function () { resolve(img); };
            img.onerror = function () { reject(new Error("Could not load " + url)); };
            img.src = url;
        });
    }

    // Label map pixel values (zone index + 1, 0 = none), one per pixel.
    function readLabels(image, width, height) {
        var canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        var ctx = canvas.getContext("2d", { willReadFrequently: true });
        ctx.drawImage(image, 0, 0, width, height);

        var rgba = ctx.getImageData(0, 0, width, height).data;
        var labels = new Uint8Array(width * height);
        for (var p = 0; p < labels.length; p++) labels[p] = rgba[p * 4];
        return labels;
    }

    function zoneName(map, i) {
        return ONEPIX.spectraSeriesLabel(map.data.zones[i].name, i);
    }

    // ---- composing the map ----

    // The photo is desaturated underneath, so each tint reads as its
    // true color whatever the scene's own colors; zone outlines are
    // drawn in full color, thicker on large images.
    function tintZones(ctx, map) {
        var width = map.data.width;
        var height = map.data.height;
        var labels = map.labels;
        var last = width * height;
        var colors = map.data.zones.map(function (_, i) {
            return toRgb(ONEPIX.spectraSeriesColor(i));
        });

        var edges = new Uint8Array(last);
        var p, x, label;

        for (p = 0; p < last; p++) {
            label = labels[p];
            if (!label) continue;
            x = p % width;
            edges[p] =
                (x > 0 && labels[p - 1] !== label) ||
                (x < width - 1 && labels[p + 1] !== label) ||
                (p >= width && labels[p - width] !== label) ||
                (p < last - width && labels[p + width] !== label) ? 1 : 0;
        }

        if (width >= 600) {
            var thick = edges.slice();
            for (p = 0; p < last; p++) {
                label = labels[p];
                if (!label || edges[p]) continue;
                x = p % width;
                thick[p] =
                    (x > 0 && edges[p - 1] && labels[p - 1] === label) ||
                    (x < width - 1 && edges[p + 1] && labels[p + 1] === label) ||
                    (p >= width && edges[p - width] && labels[p - width] === label) ||
                    (p < last - width && edges[p + width] && labels[p + width] === label) ? 1 : 0;
            }
            edges = thick;
        }

        var image = ctx.getImageData(0, 0, width, height);
        var px = image.data;

        for (p = 0; p < last; p++) {
            var o = p * 4;
            var gray = 0.299 * px[o] + 0.587 * px[o + 1] + 0.114 * px[o + 2];
            var r = px[o] + (gray - px[o]) * DESATURATION;
            var g = px[o + 1] + (gray - px[o + 1]) * DESATURATION;
            var b = px[o + 2] + (gray - px[o + 2]) * DESATURATION;

            label = labels[p];
            if (label) {
                var color = colors[label - 1];
                var alpha = edges[p] ? 1 : FILL_ALPHA;
                r += (color[0] - r) * alpha;
                g += (color[1] - g) * alpha;
                b += (color[2] - b) * alpha;
            }

            px[o] = r;
            px[o + 1] = g;
            px[o + 2] = b;
        }

        ctx.putImageData(image, 0, 0);
    }

    function roundedRect(ctx, x, y, w, h, r) {
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.arcTo(x + w, y, x + w, y + h, r);
        ctx.arcTo(x + w, y + h, x, y + h, r);
        ctx.arcTo(x, y + h, x, y, r);
        ctx.arcTo(x, y, x + w, y, r);
        ctx.closePath();
    }

    function overlaps(a, b) {
        return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
    }

    // Where a chip centered on anchor goes: there, or nudged up or
    // down until it doesn't cover a chip already placed.
    function placeChip(anchor, chipWidth, chipHeight, width, height, placed) {
        var x = Math.min(Math.max(anchor[0] - chipWidth / 2, 2), width - chipWidth - 2);
        var baseY = anchor[1] - chipHeight / 2;

        for (var step = 0; step < 15; step++) {
            var shift = Math.ceil(step / 2) * (step % 2 ? 1 : -1) * (chipHeight + 4);
            var y = Math.min(Math.max(baseY + shift, 2), height - chipHeight - 2);
            var rect = { x: x, y: y, w: chipWidth, h: chipHeight };
            if (!placed.some(function (other) { return overlaps(rect, other); })) return rect;
        }

        return { x: x, y: Math.min(Math.max(baseY, 2), height - chipHeight - 2), w: chipWidth, h: chipHeight };
    }

    // A chip - color swatch + name - on each of the zone's anchors (the
    // point deepest inside each of its large parts).
    function drawLabels(ctx, map) {
        var width = map.data.width;
        var height = map.data.height;
        var font = Math.max(12, Math.round(width / 50));
        var pad = Math.round(font * 0.45);
        var swatch = Math.round(font * 0.75);
        var chipHeight = font + pad * 2;
        var placed = [];

        ctx.font = "600 " + font + "px " + FONT_FAMILY;
        ctx.textBaseline = "middle";

        map.data.zones.forEach(function (zone, i) {
            var text = zoneName(map, i);
            var chipWidth = pad + swatch + pad + ctx.measureText(text).width + pad;

            (zone.anchors || []).forEach(function (anchor) {
                var rect = placeChip(anchor, chipWidth, chipHeight, width, height, placed);
                placed.push(rect);

                ctx.shadowColor = "rgba(0, 0, 0, 0.35)";
                ctx.shadowBlur = Math.round(font / 3);
                roundedRect(ctx, rect.x, rect.y, rect.w, rect.h, chipHeight / 2);
                ctx.fillStyle = "rgba(255, 255, 255, 0.94)";
                ctx.fill();
                ctx.shadowBlur = 0;

                roundedRect(ctx, rect.x + pad, rect.y + (chipHeight - swatch) / 2, swatch, swatch, swatch / 4);
                ctx.fillStyle = ONEPIX.spectraSeriesColor(i);
                ctx.fill();

                ctx.fillStyle = "#16191f";
                ctx.fillText(text, rect.x + pad + swatch + pad, rect.y + chipHeight / 2 + 1);
            });
        });
    }

    function compose(map) {
        var canvas = document.createElement("canvas");
        canvas.width = map.data.width;
        canvas.height = map.data.height;
        var ctx = canvas.getContext("2d", { willReadFrequently: true });

        if (map.photo) {
            ctx.drawImage(map.photo, 0, 0, canvas.width, canvas.height);
        } else {
            ctx.fillStyle = cssVar("--surface-sunken") || "#eef0f3";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        }

        tintZones(ctx, map);
        drawLabels(ctx, map);
        return canvas.toDataURL("image/png");
    }

    // ---- hover / click ----

    function zoneAt(imgEl, map, event) {
        var rect = imgEl.getBoundingClientRect();
        if (!rect.width || !rect.height) return -1;

        var x = Math.floor((event.clientX - rect.left) / rect.width * map.data.width);
        var y = Math.floor((event.clientY - rect.top) / rect.height * map.data.height);
        if (x < 0 || y < 0 || x >= map.data.width || y >= map.data.height) return -1;

        return map.labels[y * map.data.width + x] - 1;
    }

    function tooltipFor(imgEl) {
        var host = imgEl.parentElement;
        var tooltip = host.querySelector(":scope > .zone-tooltip");
        if (!tooltip) {
            tooltip = document.createElement("div");
            tooltip.className = "zone-tooltip";
            tooltip.hidden = true;
            host.appendChild(tooltip);
        }
        return tooltip;
    }

    function showTooltip(imgEl, map, zone, event) {
        var tooltip = map.tooltip;
        var info = map.data.zones[zone];

        tooltip.replaceChildren();

        var title = document.createElement("div");
        title.className = "zone-tooltip-title";
        var swatch = document.createElement("span");
        swatch.className = "zone-tooltip-swatch";
        swatch.style.background = ONEPIX.spectraSeriesColor(zone);
        title.appendChild(swatch);
        title.appendChild(document.createTextNode(zoneName(map, zone)));

        var detail = document.createElement("div");
        detail.className = "zone-tooltip-detail";
        detail.textContent = ONEPIX.t("zones.tooltip_detail", {
            pct: (info.area * 100).toFixed(info.area < 0.1 ? 1 : 0),
        });

        tooltip.appendChild(title);
        tooltip.appendChild(detail);
        tooltip.hidden = false;

        // Next to the cursor, flipped to stay inside the viewer.
        var host = imgEl.parentElement.getBoundingClientRect();
        var x = event.clientX - host.left + 14;
        var y = event.clientY - host.top + 14;
        if (x + tooltip.offsetWidth > host.width - 4) x -= tooltip.offsetWidth + 28;
        if (y + tooltip.offsetHeight > host.height - 4) y -= tooltip.offsetHeight + 28;
        tooltip.style.left = Math.max(4, x) + "px";
        tooltip.style.top = Math.max(4, y) + "px";
    }

    function hideTooltip(map) {
        if (map && map.tooltip) map.tooltip.hidden = true;
    }

    function attachEvents(imgEl) {
        if (imgEl.dataset.zoneMapEvents) return;
        imgEl.dataset.zoneMapEvents = "1";

        imgEl.addEventListener("mousemove", function (event) {
            var map = maps.get(imgEl);
            if (!map || !map.shown) return;

            var zone = zoneAt(imgEl, map, event);
            imgEl.style.cursor = zone >= 0 ? "pointer" : "";

            if (zone >= 0) showTooltip(imgEl, map, zone, event);
            else hideTooltip(map);
        });

        imgEl.addEventListener("mouseleave", function () {
            hideTooltip(maps.get(imgEl));
            imgEl.style.cursor = "";
        });

        imgEl.addEventListener("click", function (event) {
            var map = maps.get(imgEl);
            if (!map || !map.shown || !map.onZoneClick) return;

            var zone = zoneAt(imgEl, map, event);
            if (zone >= 0) map.onZoneClick(zone);
        });
    }

    // ---- public entry points ----

    // data: GET .../zones; baseUrl: that same URL, whose labels.png and
    // rgb.jpg it then loads. Resolves to true once the map is shown.
    async function renderZoneMap(imgEl, baseUrl, data, options) {
        var previous = maps.get(imgEl);
        var map = {
            data: data,
            onZoneClick: options && options.onZoneClick,
            tooltip: tooltipFor(imgEl),
            shown: false,
        };
        hideTooltip(previous);
        maps.set(imgEl, map);
        attachEvents(imgEl);

        var stamp = "?t=" + Date.now();
        var loads = [loadImage(baseUrl + "/labels.png" + stamp)];
        if (data.has_rgb) loads.push(loadImage(baseUrl + "/rgb.jpg" + stamp));

        var images = await Promise.all(loads);

        // Another result was loaded meanwhile: this map is stale.
        if (maps.get(imgEl) !== map) return false;

        map.labels = readLabels(images[0], data.width, data.height);
        map.photo = images[1] || null;
        imgEl.src = compose(map);
        map.shown = true;
        return true;
    }

    // The <img> shows something else now (no zones): stop reacting.
    function clearZoneMap(imgEl) {
        var map = maps.get(imgEl);
        hideTooltip(map);
        maps.delete(imgEl);
        imgEl.style.cursor = "";
    }

    // The theme toggle changes the palette: recolor the shown maps.
    new MutationObserver(function () {
        maps.forEach(function (map, imgEl) {
            if (map.shown && imgEl.isConnected) imgEl.src = compose(map);
        });
    }).observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-theme"],
    });

    window.ONEPIX = window.ONEPIX || {};
    window.ONEPIX.renderZoneMap = renderZoneMap;
    window.ONEPIX.clearZoneMap = clearZoneMap;

})();
