"use strict";

(() => {
  const DEFAULT_FILTERS = Object.freeze({
    state: "CE",
    start_date: "2025-01-01",
    end_date: "2025-01-31",
    reason: "",
    origin: "",
    ons_id: "",
  });

  const TAB_TITLES = Object.freeze({
    overview: "Visão geral",
    enterprises: "Empreendimentos",
    reasons: "Motivos de restrição",
    quality: "Qualidade e metodologia",
  });

  const REASON_LABELS = Object.freeze({
    REL: "REL — Confiabilidade elétrica",
    CNF: "CNF — Confiabilidade",
    ENE: "ENE — Razão energética",
    PAR: "PAR — Parada / indisponibilidade",
  });

  const ORIGIN_LABELS = Object.freeze({
    LOC: "LOC — Origem local",
    SIS: "SIS — Origem sistêmica",
  });

  const METRIC_META = Object.freeze({
    geracao_verificada_mwh: {
      label: "Geração verificada",
      unit: "MWh",
      decimals: 1,
      stroke: "#2d77b8",
      fill: "#3b82c4",
    },
    intervalos_com_restricao: {
      label: "Intervalos com restrição",
      unit: "intervalos",
      decimals: 0,
      stroke: "#c9851a",
      fill: "#d49b2a",
    },
    geracao_referencia_final_mwh: {
      label: "Referência final",
      unit: "MWh",
      decimals: 1,
      stroke: "#1d7a5f",
      fill: "#289474",
    },
    taxa_intervalos_restricao_pct: {
      label: "Taxa de restrição",
      unit: "%",
      decimals: 2,
      stroke: "#c9851a",
      fill: "#d49b2a",
    },
  });

  const state = {
    activeTab: "overview",
    filters: { ...DEFAULT_FILTERS },
    granularity: "daily",
    chartMetric: "geracao_verificada_mwh",
    enterpriseSearch: "",
    enterpriseLimit: 20,
    enterpriseOffset: 0,
    selectedEnterprise: null,
    cache: new Map(),
    lastTimeseries: [],
    lastEnterprises: [],
    lastReasons: [],
    lastQualityExecutions: [],
  };

  const el = {
    year: document.getElementById("current-year"),
    apiStatus: document.getElementById("api-status-badge"),
    lastUpdate: document.getElementById("last-update-badge"),
    workspaceHeading: document.getElementById("workspace-heading"),
    headerPeriodChip: document.getElementById("header-period-chip"),
    btnExportActive: document.getElementById("btn-export-active"),
    filtersForm: document.getElementById("filters-form"),
    filterState: document.getElementById("filter-state"),
    filterStart: document.getElementById("filter-start-date"),
    filterEnd: document.getElementById("filter-end-date"),
    filterReason: document.getElementById("filter-reason"),
    filterOrigin: document.getElementById("filter-origin"),
    filterOnsId: document.getElementById("filter-ons-id"),
    btnResetFilters: document.getElementById("btn-reset-filters"),
    filterError: document.getElementById("filter-validation-error"),
    globalError: document.getElementById("global-error-banner"),
    globalErrorMsg: document.getElementById("global-error-message"),
    btnRetryGlobal: document.getElementById("btn-retry-global"),
    navButtons: Array.from(document.querySelectorAll(".nav-item")),
    tabPanels: Array.from(document.querySelectorAll(".tab-panel")),

    // Overview
    revisionNotice: document.getElementById("revision-notice-text"),
    overviewEmpty: document.getElementById("overview-empty"),
    kpiStrip: document.getElementById("kpi-strip"),
    kpiGen: document.getElementById("kpi-gen-mwh"),
    kpiGenMeta: document.getElementById("kpi-gen-meta"),
    kpiRef: document.getElementById("kpi-ref-mwh"),
    kpiRefMeta: document.getElementById("kpi-ref-meta"),
    kpiRestricted: document.getElementById("kpi-restricted-count"),
    kpiRestrictedMeta: document.getElementById("kpi-restricted-meta"),
    kpiEnterprises: document.getElementById("kpi-enterprises-count"),
    kpiEnterprisesMeta: document.getElementById("kpi-enterprises-meta"),
    granularityButtons: Array.from(document.querySelectorAll("[data-granularity]")),
    chartMetricSelect: document.getElementById("chart-metric-select"),
    timeseriesChart: document.getElementById("timeseries-chart-container"),
    overviewTopTbody: document.getElementById("overview-top-tbody"),
    overviewReasonsMini: document.getElementById("overview-reasons-mini"),

    // Enterprises
    entSearch: document.getElementById("enterprise-search-input"),
    entEmpty: document.getElementById("enterprises-empty"),
    entTableWrap: document.getElementById("enterprises-table-wrap"),
    entTbody: document.getElementById("enterprises-tbody"),
    entPaginationInfo: document.getElementById("enterprises-pagination-info"),
    btnEntPrev: document.getElementById("btn-ent-prev"),
    btnEntNext: document.getElementById("btn-ent-next"),
    btnExportEnterprises: document.getElementById("btn-export-enterprises"),
    entDetailSection: document.getElementById("enterprise-detail-section"),
    entDetailTitle: document.getElementById("enterprise-detail-title"),
    entDetailSubtitle: document.getElementById("enterprise-detail-subtitle"),
    entDetailChart: document.getElementById("enterprise-detail-chart"),
    btnFilterByEnterprise: document.getElementById("btn-filter-by-enterprise"),
    btnCloseEnterpriseDetail: document.getElementById("btn-close-enterprise-detail"),

    // Reasons
    reasonsBars: document.getElementById("reasons-bars"),
    originsBars: document.getElementById("origins-bars"),
    reasonsEmpty: document.getElementById("reasons-empty"),
    reasonsTableWrap: document.getElementById("reasons-table-wrap"),
    reasonsTbody: document.getElementById("reasons-tbody"),
    descriptionsContainer: document.getElementById("descriptions-container"),
    btnExportReasons: document.getElementById("btn-export-reasons"),

    // Quality
    qEligGen: document.getElementById("q-elig-gen"),
    qEligGenMeta: document.getElementById("q-elig-gen-meta"),
    qCovRef: document.getElementById("q-cov-ref"),
    qCovRefMeta: document.getElementById("q-cov-ref-meta"),
    qCovGnra: document.getElementById("q-cov-gnra"),
    qCovGnraMeta: document.getElementById("q-cov-gnra-meta"),
    qCegSplit: document.getElementById("q-ceg-split"),
    executionsTbody: document.getElementById("executions-tbody"),

    tooltip: document.getElementById("chart-tooltip"),
  };

  /* ========================================================================
     Utilitários
     ======================================================================== */

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatNumber(value, decimals = 0) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "—";
    }
    return new Intl.NumberFormat("pt-BR", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(Number(value));
  }

  function formatUnitValue(value, unit, decimals = 1) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "—";
    }
    return `${formatNumber(value, decimals)} ${unit}`;
  }

  function formatDateShort(isoDate) {
    if (!isoDate) return "—";
    const parts = String(isoDate).slice(0, 10).split("-");
    if (parts.length !== 3) return isoDate;
    return `${parts[2]}/${parts[1]}`;
  }

  function formatDateFull(isoDate) {
    if (!isoDate) return "—";
    const parts = String(isoDate).slice(0, 10).split("-");
    if (parts.length !== 3) return isoDate;
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  }

  function formatUtcTimestamp(isoTs) {
    if (!isoTs) return "—";
    const dt = new Date(isoTs);
    if (Number.isNaN(dt.getTime())) return String(isoTs);
    return (
      new Intl.DateTimeFormat("pt-BR", {
        dateStyle: "short",
        timeStyle: "short",
        timeZone: "UTC",
      }).format(dt) + " UTC"
    );
  }

  function updateHeaderPeriodChip() {
    if (!el.headerPeriodChip) return;
    const start = state.filters.start_date
      ? formatDateFull(state.filters.start_date)
      : "Início";
    const end = state.filters.end_date
      ? formatDateFull(state.filters.end_date)
      : "Atual";
    const extra = state.filters.ons_id ? ` · ${state.filters.ons_id}` : "";
    el.headerPeriodChip.textContent = `${state.filters.state} · ${start} – ${end}${extra}`;
  }

  function buildQueryString(params) {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== null && val !== undefined && String(val).trim() !== "") {
        search.set(key, String(val).trim());
      }
    });
    const qs = search.toString();
    return qs ? `?${qs}` : "";
  }

  async function apiGet(path, params = {}) {
    const url = `${path}${buildQueryString(params)}`;
    if (state.cache.has(url)) {
      return state.cache.get(url);
    }

    const response = await fetch(url, {
      headers: { Accept: "application/json" },
    });

    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }

    if (!response.ok) {
      const detail =
        payload && typeof payload.detail === "string"
          ? payload.detail
          : `Erro HTTP ${response.status} ao consultar ${path}.`;
      throw new Error(detail);
    }

    state.cache.set(url, payload);
    return payload;
  }

  function downloadCsv(filename, headers, rows) {
    if (!rows.length) return;
    const escapeCell = (cell) => {
      const text = cell === null || cell === undefined ? "" : String(cell);
      if (text.includes(";") || text.includes('"') || text.includes("\n")) {
        return `"${text.replaceAll('"', '""')}"`;
      }
      return text;
    };
    const lines = [
      headers.map(escapeCell).join(";"),
      ...rows.map((row) => row.map(escapeCell).join(";")),
    ];
    const blob = new Blob(["\uFEFF" + lines.join("\r\n")], {
      type: "text/csv;charset=utf-8;",
    });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }

  /* ========================================================================
     Tooltip escuro em pílula
     ======================================================================== */

  function showTooltip(event, title, lines) {
    if (!el.tooltip) return;
    el.tooltip.innerHTML =
      `<strong>${escapeHtml(title)}</strong>` +
      lines.map((line) => `<div>${escapeHtml(line)}</div>`).join("");
    el.tooltip.hidden = false;

    const padding = 14;
    const rect = el.tooltip.getBoundingClientRect();
    let x = (event.clientX || 0) + padding;
    let y = (event.clientY || 0) - rect.height - 10;

    if (x + rect.width > window.innerWidth - 12) {
      x = window.innerWidth - rect.width - 12;
    }
    if (y < 12) {
      y = (event.clientY || 0) + padding;
    }
    el.tooltip.style.left = `${Math.max(12, x)}px`;
    el.tooltip.style.top = `${Math.max(12, y)}px`;
  }

  function hideTooltip() {
    if (el.tooltip) {
      el.tooltip.hidden = true;
    }
  }

  /* ========================================================================
     Gráfico SVG de Área + Linha Suave (inspirado na Referência 2)
     ======================================================================== */

  function renderAreaChartSvg(container, items, metricKey) {
    container.innerHTML = "";
    const meta = METRIC_META[metricKey] || METRIC_META.geracao_verificada_mwh;

    if (!items || items.length === 0) {
      container.innerHTML = `
        <div class="state-box state-box--empty">
          <div class="state-box__body">
            <h3>Sem série temporal para este recorte</h3>
            <p>Nenhum ponto foi retornado pela API para o período e filtros aplicados.</p>
          </div>
        </div>`;
      return;
    }

    const values = items.map((item) => {
      const raw = item[metricKey];
      return raw === null || raw === undefined ? null : Number(raw);
    });
    const numericValues = values.filter((v) => v !== null && Number.isFinite(v));

    if (numericValues.length === 0) {
      container.innerHTML = `
        <div class="state-box state-box--empty">
          <div class="state-box__body">
            <h3>Indicador ausente neste recorte</h3>
            <p>Sem registros elegíveis para <strong>${escapeHtml(meta.label)} (${escapeHtml(meta.unit)})</strong>; ausência não vira zero.</p>
          </div>
        </div>`;
      return;
    }

    const maxVal = Math.max(...numericValues, 0.0001);
    const width = 760;
    const height = 225;
    const pad = { top: 22, right: 18, bottom: 34, left: 64 };
    const plotW = width - pad.left - pad.right;
    const plotH = height - pad.top - pad.bottom;

    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("class", "chart-svg");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", `Evolução de ${meta.label} em ${meta.unit}`);

    // Grade horizontal
    for (let i = 0; i <= 3; i += 1) {
      const ratio = i / 3;
      const y = pad.top + plotH - ratio * plotH;
      const tickVal = maxVal * ratio;

      const line = document.createElementNS(svgNS, "line");
      line.setAttribute("x1", String(pad.left));
      line.setAttribute("x2", String(width - pad.right));
      line.setAttribute("y1", y.toFixed(1));
      line.setAttribute("y2", y.toFixed(1));
      line.setAttribute("class", "chart-grid-line");
      svg.appendChild(line);

      const label = document.createElementNS(svgNS, "text");
      label.setAttribute("x", String(pad.left - 10));
      label.setAttribute("y", String(y + 4));
      label.setAttribute("text-anchor", "end");
      label.setAttribute("class", "chart-axis-label");
      label.textContent = formatNumber(tickVal, tickVal >= 100 ? 0 : meta.decimals);
      svg.appendChild(label);
    }

    const unitLabel = document.createElementNS(svgNS, "text");
    unitLabel.setAttribute("x", String(pad.left));
    unitLabel.setAttribute("y", "12");
    unitLabel.setAttribute("class", "chart-axis-label");
    unitLabel.textContent = `Unidade: ${meta.unit}`;
    svg.appendChild(unitLabel);

    const points = [];
    const stepX = items.length > 1 ? plotW / (items.length - 1) : 0;

    items.forEach((item, idx) => {
      const val = values[idx];
      const x = items.length > 1 ? pad.left + idx * stepX : pad.left + plotW / 2;
      if (val !== null && Number.isFinite(val)) {
        const y = pad.top + plotH - (Math.max(val, 0) / maxVal) * plotH;
        points.push({ x, y, val, item, idx });
      }
    });

    if (points.length >= 2) {
      const linePath = points
        .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
        .join(" ");
      const baseY = (pad.top + plotH).toFixed(1);
      const areaPath =
        `${linePath} L ${points[points.length - 1].x.toFixed(1)} ${baseY} ` +
        `L ${points[0].x.toFixed(1)} ${baseY} Z`;

      const area = document.createElementNS(svgNS, "path");
      area.setAttribute("d", areaPath);
      area.setAttribute("fill", meta.fill);
      area.setAttribute("class", "chart-area");
      svg.appendChild(area);

      const path = document.createElementNS(svgNS, "path");
      path.setAttribute("d", linePath);
      path.setAttribute("stroke", meta.stroke);
      path.setAttribute("class", "chart-line");
      svg.appendChild(path);
    }

    const labelEvery = Math.max(1, Math.ceil(items.length / 8));
    items.forEach((item, idx) => {
      if (idx % labelEvery === 0 || idx === items.length - 1) {
        const x = items.length > 1 ? pad.left + idx * stepX : pad.left + plotW / 2;
        const xLabel = document.createElementNS(svgNS, "text");
        xLabel.setAttribute("x", x.toFixed(1));
        xLabel.setAttribute("y", String(height - 10));
        xLabel.setAttribute("text-anchor", "middle");
        xLabel.setAttribute("class", "chart-axis-label");
        xLabel.textContent = formatDateShort(item.periodo_referencia);
        svg.appendChild(xLabel);
      }
    });

    points.forEach((p) => {
      const dot = document.createElementNS(svgNS, "circle");
      dot.setAttribute("cx", p.x.toFixed(1));
      dot.setAttribute("cy", p.y.toFixed(1));
      dot.setAttribute("r", points.length <= 15 ? "4.5" : "3.6");
      dot.setAttribute("fill", meta.stroke);
      dot.setAttribute("tabindex", "0");
      dot.setAttribute("class", "chart-dot");

      const tooltipLines = [
        `${meta.label}: ${formatUnitValue(p.val, meta.unit, meta.decimals)}`,
        `Restrições: ${formatNumber(p.item.intervalos_com_restricao)} / ${formatNumber(p.item.total_intervalos)}`,
        `Taxa: ${formatUnitValue(p.item.taxa_intervalos_restricao_pct, "%", 2)}`,
      ];

      dot.addEventListener("mousemove", (evt) =>
        showTooltip(evt, formatDateFull(p.item.periodo_referencia), tooltipLines)
      );
      dot.addEventListener("mouseleave", hideTooltip);
      dot.addEventListener("focus", () => {
        const box = dot.getBoundingClientRect();
        showTooltip(
          { clientX: box.left, clientY: box.top },
          formatDateFull(p.item.periodo_referencia),
          tooltipLines
        );
      });
      dot.addEventListener("blur", hideTooltip);
      svg.appendChild(dot);
    });

    container.appendChild(svg);
  }

  /* ========================================================================
     Renderização das 4 abas
     ======================================================================== */

  function setGlobalError(message) {
    if (!message) {
      el.globalError.hidden = true;
      el.globalErrorMsg.textContent = "";
      return;
    }
    el.globalErrorMsg.textContent = message;
    el.globalError.hidden = false;
  }

  async function loadHealth() {
    try {
      const data = await apiGet("/api/health");
      el.apiStatus.className = data.database_configured
        ? "status-pill status-pill--ok"
        : "status-pill status-pill--error";
      el.apiStatus.innerHTML = `<span class="status-dot" aria-hidden="true"></span>${
        data.database_configured ? "API + Neon online" : "Banco não configurado"
      }`;
    } catch {
      el.apiStatus.className = "status-pill status-pill--error";
      el.apiStatus.innerHTML =
        '<span class="status-dot" aria-hidden="true"></span>API indisponível';
    }
  }

  async function loadOverview() {
    el.kpiStrip.classList.add("is-loading");
    el.timeseriesChart.innerHTML = '<div class="skeleton-chart"></div>';
    setGlobalError(null);

    try {
      const [overview, timeseries, topEnts, reasons] = await Promise.all([
        apiGet("/api/overview", state.filters),
        apiGet("/api/timeseries", {
          ...state.filters,
          granularity: state.granularity,
        }),
        apiGet("/api/enterprises", {
          state: state.filters.state,
          start_date: state.filters.start_date,
          end_date: state.filters.end_date,
          reason: state.filters.reason,
          origin: state.filters.origin,
          ons_id: state.filters.ons_id,
          limit: 5,
          offset: 0,
        }),
        apiGet("/api/reasons", {
          state: state.filters.state,
          start_date: state.filters.start_date,
          end_date: state.filters.end_date,
          ons_id: state.filters.ons_id,
          include_descriptions: false,
        }),
      ]);

      el.kpiStrip.classList.remove("is-loading");
      if (overview.methodology && overview.methodology.revision_notice) {
        el.revisionNotice.textContent = overview.methodology.revision_notice;
      }

      if (!overview.has_data) {
        el.overviewEmpty.hidden = false;
        el.kpiGen.textContent = "—";
        el.kpiRef.textContent = "—";
        el.kpiRestricted.textContent = "—";
        el.kpiEnterprises.textContent = "—";
        el.kpiGenMeta.textContent = "Sem registros elegíveis no recorte";
        el.kpiRefMeta.textContent = "Sem referência final";
        el.kpiRestrictedMeta.textContent = "Ausência não vira zero";
        el.kpiEnterprisesMeta.textContent = "0 identificadores observados";
      } else {
        el.overviewEmpty.hidden = true;
        const s = overview.summary;
        el.kpiGen.textContent = formatUnitValue(s.geracao_verificada_mwh, "MWh", 1);
        el.kpiGenMeta.textContent = `${formatNumber(s.intervalos_elegiveis_geracao)} de ${formatNumber(s.total_intervalos)} intervalos elegíveis`;

        el.kpiRef.textContent = formatNumber(s.geracao_referencia_final_mwh, 1);
        el.kpiRefMeta.textContent = `${formatNumber(s.intervalos_elegiveis_referencia_final)} intervalos com referência`;

        el.kpiRestricted.textContent = formatNumber(s.intervalos_com_restricao);
        el.kpiRestrictedMeta.textContent = `${formatUnitValue(s.taxa_intervalos_restricao_pct, "%", 2)} · ${formatUnitValue(s.minutos_restricao_total, "min", 0)}`;

        el.kpiEnterprises.textContent = formatNumber(s.empreendimentos_observados);
        el.kpiEnterprisesMeta.textContent = `${formatNumber(s.empreendimentos_com_restricao)} com restrição no período`;
      }

      state.lastTimeseries = timeseries.items || [];
      renderAreaChartSvg(el.timeseriesChart, state.lastTimeseries, state.chartMetric);

      // Top 5 empreendimentos no Bento inferior
      const topItems = topEnts.items || [];
      if (!topItems.length) {
        el.overviewTopTbody.innerHTML =
          '<tr><td colspan="5">Nenhum empreendimento encontrado no recorte.</td></tr>';
      } else {
        el.overviewTopTbody.innerHTML = topItems
          .map((item) => {
            const isCeg = item.tipo_identificador === "usina_com_ceg";
            const badgeClass = isCeg ? "badge badge--ceg" : "badge badge--conjunto";
            const badgeLabel = isCeg ? "Usina com CEG" : "Conjunto (-)";
            return `
              <tr class="is-clickable" tabindex="0" data-open-enterprise="${escapeHtml(item.ons_id)}" data-usina-nome="${escapeHtml(item.usina_nome)}">
                <td>
                  <span class="ent-name">${escapeHtml(item.usina_nome)}</span>
                  <span class="ent-code">${escapeHtml(item.ons_id)}</span>
                </td>
                <td><span class="${badgeClass}">${badgeLabel}</span></td>
                <td class="num">${formatNumber(item.intervalos_com_restricao)}</td>
                <td class="num">${formatUnitValue(item.taxa_intervalos_restricao_pct, "%", 2)}</td>
                <td class="num">${formatNumber(item.geracao_verificada_mwh, 1)}</td>
              </tr>`;
          })
          .join("");
      }

      // Mini-barras douradas no card escuro
      const byReason = reasons.by_reason || [];
      const maxR = Math.max(...byReason.map((r) => Number(r.intervalos_com_restricao) || 0), 1);
      el.overviewReasonsMini.innerHTML = byReason
        .map((r) => {
          const count = Number(r.intervalos_com_restricao) || 0;
          const pctWidth = count > 0 ? Math.max(4, (count / maxR) * 100) : 0;
          return `
            <div class="mini-reason-row">
              <div class="mini-reason-head">
                <span>${escapeHtml(r.restricao_razao_codigo)}</span>
                <span>${formatNumber(count)} int. (${formatUnitValue(r.participacao_restricoes_pct, "%", 1)})</span>
              </div>
              <div class="mini-reason-track">
                <div class="mini-reason-fill" style="width:${pctWidth.toFixed(1)}%"></div>
              </div>
            </div>`;
        })
        .join("");
    } catch (err) {
      el.kpiStrip.classList.remove("is-loading");
      setGlobalError(err.message);
      el.timeseriesChart.innerHTML = "";
    }
  }

  async function loadEnterprises() {
    setGlobalError(null);
    el.entTbody.innerHTML = '<tr><td colspan="7">Carregando empreendimentos…</td></tr>';

    try {
      const data = await apiGet("/api/enterprises", {
        state: state.filters.state,
        start_date: state.filters.start_date,
        end_date: state.filters.end_date,
        reason: state.filters.reason,
        origin: state.filters.origin,
        ons_id: state.filters.ons_id,
        search: state.enterpriseSearch,
        limit: state.enterpriseLimit,
        offset: state.enterpriseOffset,
      });

      const items = data.items || [];
      state.lastEnterprises = items;
      const total = data.pagination ? data.pagination.total : 0;

      if (!items.length) {
        el.entEmpty.hidden = false;
        el.entTableWrap.hidden = true;
      } else {
        el.entEmpty.hidden = true;
        el.entTableWrap.hidden = false;
        el.entTbody.innerHTML = items
          .map((item) => {
            const isCeg = item.tipo_identificador === "usina_com_ceg";
            const badgeClass = isCeg ? "badge badge--ceg" : "badge badge--conjunto";
            const badgeLabel = isCeg ? "Usina com CEG" : "Conjunto sem CEG (-)";
            const selectedClass =
              state.selectedEnterprise === item.ons_id ? " is-selected" : "";

            return `
              <tr class="is-clickable${selectedClass}" tabindex="0" data-ons-id="${escapeHtml(item.ons_id)}" data-usina-nome="${escapeHtml(item.usina_nome)}">
                <td>
                  <span class="ent-name">${escapeHtml(item.usina_nome)}</span>
                  <span class="ent-code">${escapeHtml(item.ons_id)} · CEG: ${escapeHtml(item.ceg)}</span>
                </td>
                <td><span class="${badgeClass}">${badgeLabel}</span></td>
                <td class="num">${formatNumber(item.intervalos_com_restricao)} / ${formatNumber(item.total_intervalos)}</td>
                <td class="num">${formatUnitValue(item.taxa_intervalos_restricao_pct, "%", 2)}</td>
                <td class="num">${formatNumber(item.geracao_verificada_mwh, 1)}</td>
                <td class="num">${formatNumber(item.geracao_referencia_final_mwh, 1)}</td>
                <td class="num">${formatNumber(item.minutos_restricao_total, 0)}</td>
              </tr>`;
          })
          .join("");
      }

      const startIdx = total === 0 ? 0 : state.enterpriseOffset + 1;
      const endIdx = Math.min(state.enterpriseOffset + items.length, total);
      el.entPaginationInfo.textContent =
        total === 0
          ? "0 empreendimentos/conjuntos"
          : `Exibindo ${startIdx}–${endIdx} de ${formatNumber(total)} empreendimentos/conjuntos`;

      el.btnEntPrev.disabled = state.enterpriseOffset <= 0;
      el.btnEntNext.disabled = state.enterpriseOffset + state.enterpriseLimit >= total;
    } catch (err) {
      setGlobalError(err.message);
      el.entTbody.innerHTML = "";
    }
  }

  async function openEnterpriseDetail(onsId, usinaNome) {
    state.selectedEnterprise = onsId;
    el.entDetailSection.hidden = false;
    el.entDetailTitle.textContent = `${usinaNome} (${onsId})`;
    el.entDetailSubtitle.textContent = "Série diária individual de intervalos com restrição (contagem).";
    el.entDetailChart.innerHTML = '<div class="skeleton-chart"></div>';

    el.entTbody.querySelectorAll("tr").forEach((tr) => {
      tr.classList.toggle("is-selected", tr.dataset.onsId === onsId);
    });

    try {
      const data = await apiGet("/api/timeseries", {
        ...state.filters,
        ons_id: onsId,
        granularity: "daily",
      });
      renderAreaChartSvg(el.entDetailChart, data.items || [], "intervalos_com_restricao");
      el.entDetailSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (err) {
      el.entDetailChart.innerHTML = `<p class="inline-alert inline-alert--error">${escapeHtml(err.message)}</p>`;
    }
  }

  function renderHorizontalBars(container, rows, codeKey, labelsMap, tone) {
    if (!rows || !rows.length) {
      container.innerHTML = "<p>Sem dados disponíveis.</p>";
      return;
    }
    const maxCount = Math.max(...rows.map((r) => Number(r.intervalos_com_restricao) || 0), 1);

    container.innerHTML = rows
      .map((row) => {
        const code = row[codeKey] ?? "—";
        const label = labelsMap[code] || code;
        const count = Number(row.intervalos_com_restricao) || 0;
        const widthPct = count > 0 ? Math.max(2, (count / maxCount) * 100) : 0;
        const fillClass =
          count === 0
            ? "bar-fill bar-fill--zero"
            : tone === "gold"
              ? "bar-fill bar-fill--gold"
              : "bar-fill";
        const energyText =
          row.geracao_verificada_mwh === null || row.geracao_verificada_mwh === undefined
            ? "energia: —"
            : `${formatNumber(row.geracao_verificada_mwh, 1)} MWh`;

        return `
          <div class="bar-row">
            <div class="bar-row__head">
              <span class="bar-row__label">${escapeHtml(label)}</span>
              <span class="bar-row__stats">${formatNumber(count)} int. (${formatUnitValue(row.participacao_restricoes_pct, "%", 2)}) · ${escapeHtml(energyText)}</span>
            </div>
            <div class="bar-track" aria-hidden="true">
              <div class="${fillClass}" style="width: ${widthPct.toFixed(1)}%"></div>
            </div>
          </div>`;
      })
      .join("");
  }

  async function loadReasons() {
    setGlobalError(null);
    el.reasonsBars.innerHTML = '<div class="skeleton-chart" style="height:140px"></div>';
    el.originsBars.innerHTML = '<div class="skeleton-chart" style="height:140px"></div>';

    try {
      const data = await apiGet("/api/reasons", {
        state: state.filters.state,
        start_date: state.filters.start_date,
        end_date: state.filters.end_date,
        ons_id: state.filters.ons_id,
      });

      renderHorizontalBars(
        el.reasonsBars,
        data.by_reason || [],
        "restricao_razao_codigo",
        REASON_LABELS,
        "gold"
      );
      renderHorizontalBars(
        el.originsBars,
        data.by_origin || [],
        "restricao_origem_codigo",
        ORIGIN_LABELS,
        "teal"
      );

      const items = data.items || [];
      state.lastReasons = items;

      if (!data.has_data) {
        el.reasonsEmpty.hidden = false;
        el.reasonsTableWrap.hidden = true;
      } else {
        el.reasonsEmpty.hidden = true;
        el.reasonsTableWrap.hidden = false;
        el.reasonsTbody.innerHTML = items
          .map(
            (item) => `
              <tr>
                <td><span class="badge badge--code">${escapeHtml(item.restricao_razao_codigo ?? "—")}</span></td>
                <td><span class="badge badge--code">${escapeHtml(item.restricao_origem_codigo ?? "—")}</span></td>
                <td class="num">${formatNumber(item.intervalos_com_restricao)}</td>
                <td class="num">${formatUnitValue(item.participacao_restricoes_pct, "%", 2)}</td>
                <td class="num">${formatNumber(item.empreendimentos_afetados)}</td>
                <td class="num">${formatNumber(item.geracao_verificada_mwh, 1)}</td>
                <td class="num">${formatNumber(item.geracao_referencia_final_mwh, 1)}</td>
                <td class="num">${formatNumber(item.minutos_restricao_total, 0)}</td>
              </tr>`
          )
          .join("");
      }

      const descs = data.top_descriptions || [];
      if (!descs.length) {
        el.descriptionsContainer.innerHTML =
          '<p class="surface-subtitle">Nenhuma descrição textual (<code>dsc_restricao</code>) preenchida pelo ONS neste recorte.</p>';
      } else {
        el.descriptionsContainer.innerHTML = `<ul class="methodology-list">${descs
          .map(
            (d) =>
              `<li><strong>${escapeHtml(d.restricao_razao_codigo)}/${escapeHtml(d.restricao_origem_codigo)}</strong> (${formatNumber(d.intervalos_com_restricao)} int.): ${escapeHtml(d.restricao_descricao)}</li>`
          )
          .join("")}</ul>`;
      }
    } catch (err) {
      setGlobalError(err.message);
      el.reasonsBars.innerHTML = "";
      el.originsBars.innerHTML = "";
    }
  }

  async function loadQuality() {
    setGlobalError(null);
    try {
      const data = await apiGet("/api/quality", {
        state: state.filters.state,
        start_date: state.filters.start_date,
        end_date: state.filters.end_date,
      });

      if (data.last_loaded_at_utc) {
        el.lastUpdate.textContent = `Carga: ${formatUtcTimestamp(data.last_loaded_at_utc)}`;
      }

      const cov = data.coverage || {};
      if (!data.has_data) {
        el.qEligGen.textContent = "—";
        el.qCovRef.textContent = "—";
        el.qCovGnra.textContent = "—";
        el.qCegSplit.textContent = "—";
      } else {
        el.qEligGen.textContent = formatNumber(cov.elegivel_geracao_verificada);
        el.qEligGenMeta.textContent = `de ${formatNumber(cov.total_intervalos)} intervalos no recorte`;

        el.qCovRef.textContent = formatUnitValue(cov.taxa_cobertura_referencia_final_pct, "%", 2);
        el.qCovRefMeta.textContent = `${formatNumber(cov.sem_referencia_final)} sem referência final`;

        el.qCovGnra.textContent = formatUnitValue(cov.taxa_cobertura_gnra_pct, "%", 2);
        el.qCovGnraMeta.textContent = `${formatNumber(cov.elegivel_gnra)} intervalos · unidade pendente`;

        el.qCegSplit.textContent = `${formatNumber(cov.empreendimentos_com_ceg)} / ${formatNumber(cov.conjuntos_sem_ceg)}`;
      }

      const executions = data.executions || [];
      state.lastQualityExecutions = executions;
      if (!executions.length) {
        el.executionsTbody.innerHTML =
          '<tr><td colspan="6">Nenhuma execução concluída em <code>etl_execucoes</code>.</td></tr>';
      } else {
        el.executionsTbody.innerHTML = executions
          .map(
            (ex) => `
              <tr>
                <td><code>${escapeHtml(ex.estado_sigla)} ${String(ex.ano_referencia).padStart(4, "0")}-${String(ex.mes_referencia).padStart(2, "0")}</code></td>
                <td>${escapeHtml(ex.arquivo_bruto_nome)}</td>
                <td><code title="${escapeHtml(ex.arquivo_bruto_sha256)}">${escapeHtml(String(ex.arquivo_bruto_sha256).slice(0, 12))}…</code></td>
                <td class="num">${formatNumber(ex.linhas_entrada)} → ${formatNumber(ex.linhas_carregadas)}</td>
                <td>${escapeHtml(formatUtcTimestamp(ex.carregado_em_utc))}</td>
                <td><code>${escapeHtml(ex.metodologia_versao)}</code></td>
              </tr>`
          )
          .join("");
      }
    } catch (err) {
      setGlobalError(err.message);
    }
  }

  function exportTimeseriesCsv() {
    downloadCsv(
      `serie_temporal_${state.filters.state}_${state.granularity}.csv`,
      [
        "periodo_referencia",
        "total_intervalos",
        "intervalos_com_restricao",
        "taxa_intervalos_restricao_pct",
        "geracao_verificada_mwh",
        "geracao_referencia_final_mwh",
        "minutos_restricao_total",
      ],
      state.lastTimeseries.map((i) => [
        i.periodo_referencia,
        i.total_intervalos,
        i.intervalos_com_restricao,
        i.taxa_intervalos_restricao_pct,
        i.geracao_verificada_mwh,
        i.geracao_referencia_final_mwh,
        i.minutos_restricao_total,
      ])
    );
  }

  function exportEnterprisesCsv() {
    downloadCsv(
      `empreendimentos_${state.filters.state}.csv`,
      [
        "ons_id",
        "usina_nome",
        "ceg",
        "tipo_identificador",
        "total_intervalos",
        "intervalos_com_restricao",
        "taxa_intervalos_restricao_pct",
        "geracao_verificada_mwh",
        "geracao_referencia_final_mwh",
        "minutos_restricao_total",
      ],
      state.lastEnterprises.map((i) => [
        i.ons_id,
        i.usina_nome,
        i.ceg,
        i.tipo_identificador,
        i.total_intervalos,
        i.intervalos_com_restricao,
        i.taxa_intervalos_restricao_pct,
        i.geracao_verificada_mwh,
        i.geracao_referencia_final_mwh,
        i.minutos_restricao_total,
      ])
    );
  }

  function exportReasonsCsv() {
    downloadCsv(
      `motivos_restricao_${state.filters.state}.csv`,
      [
        "restricao_razao_codigo",
        "restricao_origem_codigo",
        "intervalos_com_restricao",
        "participacao_restricoes_pct",
        "empreendimentos_afetados",
        "geracao_verificada_mwh",
        "geracao_referencia_final_mwh",
        "minutos_restricao_total",
      ],
      state.lastReasons.map((i) => [
        i.restricao_razao_codigo,
        i.restricao_origem_codigo,
        i.intervalos_com_restricao,
        i.participacao_restricoes_pct,
        i.empreendimentos_afetados,
        i.geracao_verificada_mwh,
        i.geracao_referencia_final_mwh,
        i.minutos_restricao_total,
      ])
    );
  }

  function exportQualityCsv() {
    downloadCsv(
      `qualidade_execucoes_${state.filters.state}.csv`,
      [
        "estado_sigla",
        "ano_referencia",
        "mes_referencia",
        "arquivo_bruto_nome",
        "arquivo_bruto_sha256",
        "linhas_entrada",
        "linhas_carregadas",
        "carregado_em_utc",
        "metodologia_versao",
      ],
      state.lastQualityExecutions.map((execution) => [
        execution.estado_sigla,
        execution.ano_referencia,
        execution.mes_referencia,
        execution.arquivo_bruto_nome,
        execution.arquivo_bruto_sha256,
        execution.linhas_entrada,
        execution.linhas_carregadas,
        execution.carregado_em_utc,
        execution.metodologia_versao,
      ])
    );
  }

  async function refreshActiveTab() {
    if (state.activeTab === "overview") {
      await loadOverview();
    } else if (state.activeTab === "enterprises") {
      await loadEnterprises();
    } else if (state.activeTab === "reasons") {
      await loadReasons();
    } else if (state.activeTab === "quality") {
      await loadQuality();
    }
  }

  function switchTab(tabName) {
    state.activeTab = tabName;
    if (el.workspaceHeading) {
      el.workspaceHeading.textContent = TAB_TITLES[tabName] || "Visão geral";
    }
    el.navButtons.forEach((btn) => {
      const active = btn.dataset.tab === tabName;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-selected", String(active));
      btn.tabIndex = active ? 0 : -1;
    });
    el.tabPanels.forEach((panel) => {
      const active = panel.id === `panel-${tabName}`;
      panel.hidden = !active;
      panel.classList.toggle("is-active", active);
    });
    hideTooltip();
    refreshActiveTab();
  }

  function bindEvents() {
    el.navButtons.forEach((btn, idx) => {
      btn.addEventListener("click", () => switchTab(btn.dataset.tab));
      btn.addEventListener("keydown", (evt) => {
        let nextIdx = null;
        if (evt.key === "ArrowDown" || evt.key === "ArrowRight") {
          nextIdx = (idx + 1) % el.navButtons.length;
        } else if (evt.key === "ArrowUp" || evt.key === "ArrowLeft") {
          nextIdx = (idx - 1 + el.navButtons.length) % el.navButtons.length;
        } else if (evt.key === "Home") {
          nextIdx = 0;
        } else if (evt.key === "End") {
          nextIdx = el.navButtons.length - 1;
        }

        if (nextIdx !== null) {
          evt.preventDefault();
          el.navButtons[nextIdx].focus();
          switchTab(el.navButtons[nextIdx].dataset.tab);
        }
      });
    });

    document.querySelectorAll("[data-goto-tab]").forEach((btn) => {
      btn.addEventListener("click", () => switchTab(btn.dataset.gotoTab));
    });

    el.btnExportActive.addEventListener("click", () => {
      if (state.activeTab === "enterprises") exportEnterprisesCsv();
      else if (state.activeTab === "reasons") exportReasonsCsv();
      else if (state.activeTab === "quality") exportQualityCsv();
      else exportTimeseriesCsv();
    });
    el.btnExportEnterprises.addEventListener("click", exportEnterprisesCsv);
    el.btnExportReasons.addEventListener("click", exportReasonsCsv);

    el.filtersForm.addEventListener("submit", (evt) => {
      evt.preventDefault();
      const start = el.filterStart.value;
      const end = el.filterEnd.value;
      if (start && end && start > end) {
        el.filterError.textContent = "A data inicial não pode ser posterior à data final.";
        el.filterError.hidden = false;
        return;
      }
      el.filterError.hidden = true;
      state.filters = {
        state: el.filterState.value || "CE",
        start_date: start,
        end_date: end,
        reason: el.filterReason.value,
        origin: el.filterOrigin.value,
        ons_id: el.filterOnsId.value.trim(),
      };
      state.enterpriseOffset = 0;
      state.selectedEnterprise = null;
      el.entDetailSection.hidden = true;
      state.cache.clear();
      updateHeaderPeriodChip();
      refreshActiveTab();
    });

    const resetAllFilters = () => {
      el.filterState.value = DEFAULT_FILTERS.state;
      el.filterStart.value = DEFAULT_FILTERS.start_date;
      el.filterEnd.value = DEFAULT_FILTERS.end_date;
      el.filterReason.value = DEFAULT_FILTERS.reason;
      el.filterOrigin.value = DEFAULT_FILTERS.origin;
      el.filterOnsId.value = DEFAULT_FILTERS.ons_id;
      el.filterError.hidden = true;
      state.filters = { ...DEFAULT_FILTERS };
      state.enterpriseSearch = "";
      el.entSearch.value = "";
      state.enterpriseOffset = 0;
      state.selectedEnterprise = null;
      el.entDetailSection.hidden = true;
      state.cache.clear();
      updateHeaderPeriodChip();
      refreshActiveTab();
    };

    el.btnResetFilters.addEventListener("click", resetAllFilters);
    document
      .querySelectorAll('[data-action="reset-filters"]')
      .forEach((btn) => btn.addEventListener("click", resetAllFilters));

    el.btnRetryGlobal.addEventListener("click", () => {
      state.cache.clear();
      loadHealth();
      refreshActiveTab();
    });

    el.granularityButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        state.granularity = btn.dataset.granularity;
        el.granularityButtons.forEach((b) => {
          const active = b.dataset.granularity === state.granularity;
          b.classList.toggle("is-active", active);
          b.setAttribute("aria-pressed", String(active));
        });
        loadOverview();
      });
    });

    el.chartMetricSelect.addEventListener("change", () => {
      state.chartMetric = el.chartMetricSelect.value;
      renderAreaChartSvg(el.timeseriesChart, state.lastTimeseries, state.chartMetric);
    });

    // Clique no Top 5 da Visão geral abre o detalhe na aba Empreendimentos
    el.overviewTopTbody.addEventListener("click", (evt) => {
      const tr = evt.target.closest("tr[data-open-enterprise]");
      if (tr) {
        const onsId = tr.dataset.openEnterprise;
        const nome = tr.dataset.usinaNome;
        switchTab("enterprises");
        openEnterpriseDetail(onsId, nome);
      }
    });

    let searchTimer = null;
    el.entSearch.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        state.enterpriseSearch = el.entSearch.value.trim();
        state.enterpriseOffset = 0;
        loadEnterprises();
      }, 250);
    });

    el.btnEntPrev.addEventListener("click", () => {
      state.enterpriseOffset = Math.max(0, state.enterpriseOffset - state.enterpriseLimit);
      loadEnterprises();
    });

    el.btnEntNext.addEventListener("click", () => {
      state.enterpriseOffset += state.enterpriseLimit;
      loadEnterprises();
    });

    el.entTbody.addEventListener("click", (evt) => {
      const tr = evt.target.closest("tr[data-ons-id]");
      if (tr) openEnterpriseDetail(tr.dataset.onsId, tr.dataset.usinaNome);
    });

    el.entTbody.addEventListener("keydown", (evt) => {
      if (evt.key === "Enter" || evt.key === " ") {
        const tr = evt.target.closest("tr[data-ons-id]");
        if (tr) {
          evt.preventDefault();
          openEnterpriseDetail(tr.dataset.onsId, tr.dataset.usinaNome);
        }
      }
    });

    el.btnCloseEnterpriseDetail.addEventListener("click", () => {
      state.selectedEnterprise = null;
      el.entDetailSection.hidden = true;
      el.entTbody.querySelectorAll("tr").forEach((tr) => tr.classList.remove("is-selected"));
    });

    el.btnFilterByEnterprise.addEventListener("click", () => {
      if (!state.selectedEnterprise) return;
      el.filterOnsId.value = state.selectedEnterprise;
      state.filters.ons_id = state.selectedEnterprise;
      state.cache.clear();
      updateHeaderPeriodChip();
      switchTab("overview");
    });
  }

  /* ========================================================================
     Inicialização
     ======================================================================== */

  if (el.year) {
    el.year.textContent = `© ${new Date().getFullYear()}`;
  }

  updateHeaderPeriodChip();
  bindEvents();
  loadHealth();
  loadOverview();

  apiGet("/api/quality", { state: state.filters.state })
    .then((q) => {
      if (q && q.last_loaded_at_utc && el.lastUpdate) {
        el.lastUpdate.textContent = `Carga: ${formatUtcTimestamp(q.last_loaded_at_utc)}`;
      }
    })
    .catch(() => {
      // Auxiliar da sidebar; erros reais aparecem na aba Qualidade.
    });
})();
