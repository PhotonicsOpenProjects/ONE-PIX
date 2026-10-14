/* ============================================================
   ONE-PIX — Shared interactive spectra chart (Plotly).

   Used by the acquisition and analysis pages for HAS-style
   per-cluster spectra: each page fetches its own GET .../spectra
   endpoint and calls ONEPIX.renderSpectraChart(elements, data,
   axisLabels) with the three mount points (chart / legend / table)
   and the JSON payload.

   Plotly's own legend is deliberately not used - a plain HTML
   legend below the chart (flex-wrap, click-to-isolate) can never
   overlap the plot or the axis title the way a built-in legend can
   once cluster names run long or a chart gets narrow, and it comes
   with toggle-to-isolate for free.
   ============================================================ */

(function () {

    // The data-viz skill's validated default categorical palette -
    // 8 hues, fixed order. Past 8 simultaneous spectra a line chart
    // stops reading cleanly regardless of color, so slot 9+ cycles
    // back through the same 8 rather than inventing new hues (a
    // documented, deliberate tradeoff - not an oversight).
    var SERIES_SLOTS = 8;

    function cssVar(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }

    function seriesColor(i) {
        return cssVar("--chart-series-" + ((i % SERIES_SLOTS) + 1));
    }

    function seriesLabel(name, i) {
        return name || ("Cluster " + (i + 1));
    }

    function labelFor(data, i) {
        return seriesLabel(data.cluster_name && data.cluster_name[i], i);
    }

    function chartLayout(axisLabels) {
        var textColor = cssVar("--text");
        var mutedColor = cssVar("--text-faint");
        var gridColor = cssVar("--border");
        var surfaceColor = cssVar("--surface-elevated");

        return {
            margin: { t: 16, r: 20, b: 52, l: 60 },
            showlegend: false,
            paper_bgcolor: "transparent",
            plot_bgcolor: "transparent",
            font: {
                family: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                color: textColor,
                size: 12,
            },
            hovermode: "x unified",
            hoverlabel: {
                bgcolor: surfaceColor,
                bordercolor: gridColor,
                font: { color: textColor, family: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" },
            },
            xaxis: {
                title: { text: axisLabels.x, standoff: 10 },
                color: mutedColor,
                gridcolor: gridColor,
                linecolor: gridColor,
                zeroline: false,
                automargin: true,
            },
            yaxis: {
                title: { text: axisLabels.y, standoff: 10 },
                color: mutedColor,
                gridcolor: gridColor,
                linecolor: gridColor,
                zeroline: false,
                automargin: true,
            },
        };
    }

    function buildTraces(data) {
        return data.spectra.map(function (values, i) {
            return {
                x: data.wavelengths,
                y: values,
                mode: "lines",
                line: { color: seriesColor(i), width: 2 },
                name: labelFor(data, i),
                hoverlabel: { namelength: -1 },
            };
        });
    }

    // ---- custom HTML legend (click a swatch to isolate that
    // series; click again to restore all) ----

    function renderLegend(legendEl, chartEl, data) {
        legendEl.innerHTML = "";
        legendEl.setAttribute("role", "group");

        var isolated = null;

        function applyVisibility() {
            var visibility = data.spectra.map(function (_, i) {
                return isolated === null || isolated === i ? true : "legendonly";
            });
            Plotly.restyle(chartEl, { visible: visibility });

            Array.prototype.forEach.call(legendEl.children, function (item, i) {
                item.classList.toggle("is-dimmed", isolated !== null && isolated !== i);
            });
        }

        data.spectra.forEach(function (_, i) {
            var item = document.createElement("button");
            item.type = "button";
            item.className = "spectra-legend-item";

            var swatch = document.createElement("span");
            swatch.className = "spectra-legend-swatch";
            swatch.style.background = seriesColor(i);

            var label = document.createElement("span");
            label.className = "spectra-legend-label";
            label.textContent = labelFor(data, i);

            item.appendChild(swatch);
            item.appendChild(label);

            item.addEventListener("click", function () {
                isolated = isolated === i ? null : i;
                applyVisibility();
            });

            legendEl.appendChild(item);
        });
    }

    // ---- table view (the accessible, copy-pasteable twin of the
    // chart - same data, no hover required) ----

    function renderTable(tableWrapEl, data, axisLabels) {
        tableWrapEl.innerHTML = "";

        var table = document.createElement("table");
        table.className = "data-table";

        var thead = document.createElement("thead");
        var headRow = document.createElement("tr");
        var xHeader = document.createElement("th");
        xHeader.textContent = axisLabels.x;
        headRow.appendChild(xHeader);

        data.spectra.forEach(function (_, i) {
            var th = document.createElement("th");
            th.textContent = labelFor(data, i);
            headRow.appendChild(th);
        });
        thead.appendChild(headRow);
        table.appendChild(thead);

        var tbody = document.createElement("tbody");
        data.wavelengths.forEach(function (wl, rowIdx) {
            var row = document.createElement("tr");
            var wlCell = document.createElement("td");
            wlCell.textContent = typeof wl === "number" ? wl.toFixed(1) : "—";
            row.appendChild(wlCell);

            data.spectra.forEach(function (series) {
                var cell = document.createElement("td");
                var value = series[rowIdx];
                // null marks an invalid reading (saturated/dead
                // channel) sanitized server-side for valid JSON -
                // show it as a dash, not the word "null".
                cell.textContent = typeof value === "number" ? value.toFixed(4) : "—";
                row.appendChild(cell);
            });

            tbody.appendChild(row);
        });
        table.appendChild(tbody);

        var wrap = document.createElement("div");
        wrap.className = "table-wrap spectra-table-scroll";
        wrap.appendChild(table);
        tableWrapEl.appendChild(wrap);
    }

    // ---- live re-theming (the toggle in the nav flips data-theme
    // on <html> without a page reload - already-rendered charts
    // would otherwise keep stale light/dark colors) ----

    var mounted = [];

    function retheme() {
        mounted.forEach(function (entry) {
            if (!entry.chartEl.isConnected) return;

            var colors = entry.data.spectra.map(function (_, i) { return seriesColor(i); });
            Plotly.restyle(entry.chartEl, { "line.color": colors });

            var layout = chartLayout(entry.axisLabels);
            Plotly.relayout(entry.chartEl, {
                "font.color": layout.font.color,
                "xaxis.color": layout.xaxis.color,
                "yaxis.color": layout.yaxis.color,
                "xaxis.gridcolor": layout.xaxis.gridcolor,
                "yaxis.gridcolor": layout.yaxis.gridcolor,
                "xaxis.linecolor": layout.xaxis.linecolor,
                "yaxis.linecolor": layout.yaxis.linecolor,
                "hoverlabel.bgcolor": layout.hoverlabel.bgcolor,
                "hoverlabel.bordercolor": layout.hoverlabel.bordercolor,
                "hoverlabel.font.color": layout.hoverlabel.font.color,
            });

            Array.prototype.forEach.call(entry.legendEl.children, function (item, i) {
                item.querySelector(".spectra-legend-swatch").style.background = colors[i];
            });
        });
    }

    new MutationObserver(retheme).observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-theme"],
    });

    // ---- public entry point ----

    function renderSpectraChart(elements, data, axisLabels) {
        var chartEl = elements.chart;
        var legendEl = elements.legend;
        var tableWrapEl = elements.table;

        if (typeof Plotly === "undefined") return;

        Plotly.react(chartEl, buildTraces(data), chartLayout(axisLabels), {
            responsive: true,
            displaylogo: false,
        });

        renderLegend(legendEl, chartEl, data);
        renderTable(tableWrapEl, data, axisLabels);

        var existing = mounted.find(function (entry) { return entry.chartEl === chartEl; });
        var entry = { chartEl: chartEl, legendEl: legendEl, data: data, axisLabels: axisLabels };
        if (existing) {
            Object.assign(existing, entry);
        } else {
            mounted.push(entry);
            followContainerSize(chartEl);
        }
    }

    // Plotly's `responsive` option only reacts to window resizes. A
    // chart drawn while its card was still hidden (zero width) would
    // otherwise stay at Plotly's 700px default, stuck to the left of a
    // wider card - same after the table/chart toggle or a layout change.
    function followContainerSize(chartEl) {
        if (typeof ResizeObserver === "undefined") return;

        new ResizeObserver(function () {
            if (chartEl.offsetWidth > 0 && chartEl.data) {
                Plotly.Plots.resize(chartEl);
            }
        }).observe(chartEl);
    }

    window.ONEPIX = window.ONEPIX || {};
    window.ONEPIX.renderSpectraChart = renderSpectraChart;
    // Shared with zone-map.js, so a zone and its spectrum always match.
    window.ONEPIX.spectraSeriesColor = seriesColor;
    window.ONEPIX.spectraSeriesLabel = seriesLabel;

})();
