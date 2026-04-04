const RANGE_OPTIONS = [7, 30, 90, 365];
const DEFAULT_RANGE = 30;

const SUMMARY_FIELDS = [
  ["total_users", "Total users"],
  ["total_lobbies_created", "Lobbies created"],
  ["total_games_started", "Games started"],
  ["total_games_completed", "Games completed"],
  ["total_games_abandoned", "Games abandoned"],
];

const RECENT_FIELDS = [
  ["games_played_today", "Games today"],
  ["games_played_last_7_days", "Games 7d"],
  ["games_played_last_30_days", "Games 30d"],
  ["lobbies_created_today", "Lobbies today"],
  ["lobbies_created_last_7_days", "Lobbies 7d"],
  ["lobbies_created_last_30_days", "Lobbies 30d"],
  ["new_users_last_7_days", "New users 7d"],
  ["new_users_last_30_days", "New users 30d"],
  ["returning_users_last_7_days", "Returning 7d"],
  ["returning_users_last_30_days", "Returning 30d"],
];

const CHARTS = [
  ["daily_games_completed", "Daily games completed", "#7ad7b8"],
  ["daily_lobbies_created", "Daily lobbies created", "#7ea8ff"],
  ["daily_games_started", "Daily games started", "#f4bf63"],
  ["daily_new_users", "Daily new users", "#ff8e7d"],
];

const state = {
  days: DEFAULT_RANGE,
};

const dom = {};

function init() {
  dom.status = document.getElementById("status-banner");
  dom.summaryGrid = document.getElementById("summary-grid");
  dom.conversionGrid = document.getElementById("conversion-grid");
  dom.recentGrid = document.getElementById("recent-grid");
  dom.chartsGrid = document.getElementById("charts-grid");
  dom.metaLine = document.getElementById("meta-line");
  dom.rangeSelector = document.getElementById("range-selector");

  const urlDays = Number.parseInt(new URLSearchParams(window.location.search).get("days") || "", 10);
  if (RANGE_OPTIONS.includes(urlDays)) {
    state.days = urlDays;
  }

  renderRangeSelector();
  loadStats(state.days);
}

function setStatus(message, kind = "loading") {
  dom.status.className = `status-banner status-banner--${kind}`;
  dom.status.replaceChildren();

  const text = document.createElement("span");
  text.textContent = message;
  dom.status.appendChild(text);
}

function renderRangeSelector() {
  dom.rangeSelector.replaceChildren();

  for (const days of RANGE_OPTIONS) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = days === state.days ? "segmented__button is-active" : "segmented__button";
    button.textContent = `${days}d`;
    button.setAttribute("aria-pressed", String(days === state.days));
    button.addEventListener("click", () => {
      if (state.days === days) {
        return;
      }
      state.days = days;
      window.history.replaceState({}, "", `${window.location.pathname}?days=${days}`);
      renderRangeSelector();
      loadStats(days);
    });
    dom.rangeSelector.appendChild(button);
  }
}

async function loadStats(days) {
  setStatus(`Loading ${days}-day stats...`, "loading");
  dom.summaryGrid.innerHTML = skeletonCards(5);
  dom.conversionGrid.innerHTML = skeletonCards(2);
  dom.recentGrid.innerHTML = skeletonCards(10);
  dom.chartsGrid.innerHTML = chartSkeletons();
  dom.metaLine.textContent = "Loading latest snapshot...";

  try {
    const response = await fetch(`/stats?days=${days}`, {
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    const payload = await response.json();
    renderDashboard(payload);
  } catch (_error) {
    renderError();
  }
}

function renderDashboard(payload) {
  const totals = payload?.totals || {};
  const conversion = payload?.conversion || {};
  const recent = payload?.recent || {};
  const activity = payload?.activity || {};
  const meta = payload?.meta || {};

  if (!hasUsableData(totals, conversion, recent, activity)) {
    renderEmpty(payload);
    return;
  }

  setStatus(`Showing ${state.days}-day stats.`, "ready");

  dom.summaryGrid.innerHTML = SUMMARY_FIELDS.map(([key, label]) =>
    metricCard(label, formatInteger(totals[key]), "summary-card")
  ).join("");

  dom.conversionGrid.innerHTML = [
    metricCard(
      "Lobby to game start",
      formatPercent(conversion.lobby_to_game_start_rate),
      "conversion-card"
    ),
    metricCard("Game completion", formatPercent(conversion.game_completion_rate), "conversion-card"),
  ].join("");

  dom.recentGrid.innerHTML = RECENT_FIELDS.map(([key, label]) =>
    metricCard(label, formatInteger(recent[key]), "recent-card")
  ).join("");

  dom.chartsGrid.innerHTML = CHARTS.map(([key, title, color]) =>
    renderChartCard(title, activity[key], color, activity.range_days || state.days)
  ).join("");

  dom.metaLine.textContent = buildMetaLine(meta, activity, state.days);
}

function renderEmpty(payload) {
  setStatus("No usable stats were returned by the server.", "empty");
  dom.summaryGrid.innerHTML = emptyCard("No summary data available.");
  dom.conversionGrid.innerHTML = emptyCard("No conversion data available.");
  dom.recentGrid.innerHTML = emptyCard("No recent activity data available.");
  dom.chartsGrid.innerHTML = emptyChart(payload?.activity?.range_days || state.days);
  dom.metaLine.textContent = "Aggregate-only data.";
}

function renderError() {
  setStatus("Could not load stats right now. Please try again.", "error");
  dom.summaryGrid.innerHTML = emptyCard("Stats are unavailable.");
  dom.conversionGrid.innerHTML = emptyCard("Stats are unavailable.");
  dom.recentGrid.innerHTML = emptyCard("Stats are unavailable.");
  dom.chartsGrid.innerHTML = emptyCard("Charts could not be loaded.");
  dom.metaLine.textContent = "Last request failed.";

  const retry = document.createElement("button");
  retry.type = "button";
  retry.className = "retry-button";
  retry.textContent = "Retry";
  retry.addEventListener("click", () => loadStats(state.days));

  dom.status.appendChild(retry);
}

function hasUsableData(totals, conversion, recent, activity) {
  const hasValue = (value) => value !== null && value !== undefined;
  const hasArrayData = (value) => Array.isArray(value) && value.length > 0;

  return [
    Object.values(totals).some(hasValue),
    Object.values(conversion).some(hasValue),
    Object.values(recent).some(hasValue),
    Object.values(activity).some(hasArrayData),
  ].some(Boolean);
}

function metricCard(label, value, extraClass = "") {
  return `
    <article class="metric-card ${extraClass}">
      <div class="metric-value">${value}</div>
      <div class="metric-label">${label}</div>
    </article>
  `;
}

function emptyCard(message) {
  return `
    <article class="metric-card metric-card--empty">
      <div class="metric-label">${message}</div>
    </article>
  `;
}

function skeletonCards(count) {
  return Array.from({ length: count }, () => `
    <article class="metric-card metric-card--skeleton">
      <div class="skeleton skeleton--value"></div>
      <div class="skeleton skeleton--label"></div>
    </article>
  `).join("");
}

function chartSkeletons() {
  return CHARTS.map(([, title]) => `
    <article class="chart-card">
      <div class="section-heading section-heading--chart">
        <h3>${title}</h3>
      </div>
      <div class="chart-skeleton"></div>
    </article>
  `).join("");
}

function emptyChart(rangeDays) {
  return `
    <article class="chart-card chart-card--empty">
      <div class="section-heading section-heading--chart">
        <h3>Daily activity</h3>
      </div>
      <p class="chart-empty-copy">No chart data is available for the selected ${rangeDays}-day range.</p>
    </article>
  `;
}

function renderChartCard(title, series, color, rangeDays) {
  if (!Array.isArray(series) || series.length === 0) {
    return `
      <article class="chart-card chart-card--empty">
        <div class="section-heading section-heading--chart">
          <h3>${title}</h3>
        </div>
        <p class="chart-empty-copy">No data available for the selected ${rangeDays}-day range.</p>
      </article>
    `;
  }

  const values = series.map((point) => Number(point?.count || 0));
  const maxValue = Math.max(1, ...values);
  const width = 720;
  const height = 280;
  const padding = { top: 24, right: 24, bottom: 48, left: 48 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const xFor = (index) => {
    if (series.length === 1) {
      return padding.left + innerWidth / 2;
    }
    return padding.left + (index * innerWidth) / (series.length - 1);
  };
  const yFor = (value) => padding.top + innerHeight - (value / maxValue) * innerHeight;
  const points = values
    .map((value, index) => `${xFor(index).toFixed(1)},${yFor(value).toFixed(1)}`)
    .join(" ");
  const areaPath = buildAreaPath(values, xFor, yFor, padding.top + innerHeight, series.length);
  const ticks = buildTickIndexes(series.length);
  const yTicks = buildYTicks(maxValue);
  const fillId = `${slugify(title)}-fill`;

  return `
    <article class="chart-card">
      <div class="section-heading section-heading--chart">
        <h3>${title}</h3>
      </div>
      <svg
        class="chart-svg"
        viewBox="0 0 ${width} ${height}"
        role="img"
        aria-label="${title} for the selected ${rangeDays}-day range"
      >
        <defs>
          <linearGradient id="${fillId}" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stop-color="${color}" stop-opacity="0.3"></stop>
            <stop offset="100%" stop-color="${color}" stop-opacity="0.05"></stop>
          </linearGradient>
        </defs>
        ${renderGridLines(yTicks, padding.left, padding.left + innerWidth, yFor)}
        <path d="${areaPath}" fill="url(#${fillId})"></path>
        <polyline
          points="${points}"
          fill="none"
          stroke="${color}"
          stroke-width="3"
          stroke-linecap="round"
          stroke-linejoin="round"
        ></polyline>
        ${renderXAxisLabels(series, ticks, xFor, padding.top + innerHeight + 28)}
        ${renderYAxisLabels(yTicks, padding.left - 10, yFor)}
      </svg>
    </article>
  `;
}

function renderGridLines(ticks, x1, x2, yFor) {
  return ticks
    .map(
      (tick) => `
        <line
          x1="${x1}"
          x2="${x2}"
          y1="${yFor(tick)}"
          y2="${yFor(tick)}"
          class="chart-grid-line"
        ></line>
      `
    )
    .join("");
}

function renderXAxisLabels(series, ticks, xFor, y) {
  return ticks
    .map((index) => {
      const point = series[index];
      const label = formatShortDate(point?.date);
      return `
        <text x="${xFor(index)}" y="${y}" text-anchor="middle" class="chart-axis-label">
          ${label}
        </text>
      `;
    })
    .join("");
}

function renderYAxisLabels(ticks, x, yFor) {
  return ticks
    .map(
      (tick) => `
        <text x="${x}" y="${yFor(tick) + 4}" text-anchor="end" class="chart-axis-label chart-axis-label--y">
          ${formatCompactNumber(tick)}
        </text>
      `
    )
    .join("");
}

function buildAreaPath(values, xFor, yFor, baseline, seriesLength) {
  const firstX = xFor(0);
  const lastX = xFor(seriesLength - 1);
  const segments = values
    .map((value, index) => `${index === 0 ? "M" : "L"} ${xFor(index).toFixed(1)} ${yFor(value).toFixed(1)}`)
    .join(" ");
  return `${segments} L ${lastX.toFixed(1)} ${baseline} L ${firstX.toFixed(1)} ${baseline} Z`;
}

function buildTickIndexes(length) {
  if (length <= 1) {
    return [0];
  }
  const desiredTicks = Math.min(7, length);
  const step = Math.max(1, Math.round((length - 1) / (desiredTicks - 1)));
  const indexes = new Set([0, length - 1]);
  for (let index = 0; index < length; index += step) {
    indexes.add(index);
  }
  return Array.from(indexes).sort((a, b) => a - b);
}

function buildYTicks(maxValue) {
  if (maxValue <= 0) {
    return [0];
  }
  const midpoint = Math.max(1, Math.ceil(maxValue / 2));
  return Array.from(new Set([0, midpoint, maxValue])).sort((a, b) => a - b);
}

function buildMetaLine(meta, activity, days) {
  const parts = [`Range: ${activity?.range_days || days} days`];
  if (meta?.generated_at) {
    parts.push(`Updated: ${formatDateTime(meta.generated_at, meta.timezone)}`);
  }
  if (meta?.timezone) {
    parts.push(`Timezone: ${meta.timezone}`);
  }
  return parts.join(" | ");
}

function formatInteger(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  return new Intl.NumberFormat().format(Number(value));
}

function formatCompactNumber(value) {
  return new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(
    Number(value || 0)
  );
}

function formatPercent(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function formatDateTime(value, timezone) {
  const date = new Date(value);
  const options = {
    dateStyle: "medium",
    timeStyle: "short",
  };
  if (timezone) {
    options.timeZone = timezone;
  }
  return new Intl.DateTimeFormat(undefined, options).format(date);
}

function formatShortDate(value) {
  const date = new Date(`${value}T00:00:00Z`);
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
  }).format(date);
}

function slugify(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

document.addEventListener("DOMContentLoaded", init);
