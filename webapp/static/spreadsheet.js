"use strict";

/*
 * Read-only virtualized spreadsheet viewer. Scroll position covers every row
 * in the selected filter; only visible rows are rendered in the DOM.
 * /api/rows remains stateless, so each new 50-row block re-sends the file
 * to the local backend. No dataset is persisted on the server.
 */
(function () {
  const PAGE_SIZE = 50;
  const ROW_HEIGHT = 50;
  const HEADER_HEIGHT = 48;
  const OVERSCAN = 5;
  const CACHE_LIMIT = 24;
  const MAX_IN_FLIGHT = 4;
  const NUMBER_WIDTH = 94;
  const CELL_WIDTH = 185;

  const el = id => document.getElementById(id);
  const view = el("gridViewport");
  const canvas = el("gridCanvas");
  const headers = el("gridColumns");
  const layer = el("gridRows");
  const filterSelect = el("gridFilter");
  const status = el("gridCount");
  const range = el("gridVisibleRange");

  let state = {
    epoch: 0,
    file: null,
    filter: "all",
    count: 0,
    totalRows: 0,
    flaggedRows: 0,
    columns: [],
    columnProfiles: [],
    labels: {},
    cache: new Map(),
    loading: new Set(),
    pendingFrame: false,
    error: "",
    failed: new Set(),
  };

  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== null && text !== undefined) node.textContent = String(text);
    if (className) node.className = className;
    return node;
  }

  function gridWidth() {
    return NUMBER_WIDTH + state.columns.length * CELL_WIDTH;
  }

  function createHeader() {
    const fragment = document.createDocumentFragment();
    const rowNumber = element("div", "Data row", "sheet-header-cell sheet-number");
    rowNumber.setAttribute("role", "columnheader");
    fragment.append(rowNumber);
    state.columns.forEach((colName, index) => {
      const col = element("div", colName, "sheet-header-cell");
      col.setAttribute("role", "columnheader");
      col.title = colName;
      if (state.columnProfiles[index] && state.columnProfiles[index].constant) {
        col.append(element("small", "Constant column", "constant-head"));
      }
      fragment.append(col);
    });
    headers.replaceChildren(fragment);
    headers.style.width = gridWidth() + "px";
    headers.style.gridTemplateColumns =
      NUMBER_WIDTH + "px repeat(" + state.columns.length + ", " + CELL_WIDTH + "px)";
    canvas.style.width = gridWidth() + "px";
    canvas.setAttribute("aria-colcount", String(state.columns.length + 1));
  }

  function rowElement(row, filteredIndex) {
    const gridRow = element("div", null, "sheet-row");
    gridRow.style.top = (HEADER_HEIGHT + filteredIndex * ROW_HEIGHT) + "px";
    gridRow.style.width = gridWidth() + "px";
    gridRow.style.gridTemplateColumns =
      NUMBER_WIDTH + "px repeat(" + state.columns.length + ", " + CELL_WIDTH + "px)";
    gridRow.setAttribute("role", "row");
    gridRow.setAttribute("aria-rowindex", String(filteredIndex + 2));

    const number = element("div", row ? row.row_number : "…", "sheet-cell sheet-number");
    number.setAttribute("role", "rowheader");
    if (row && row.row_flags.includes("duplicate")) {
      number.classList.add("sheet-duplicate");
      number.title = "Duplicate group: identical values on multiple rows";
      number.append(element("small", "Duplicate", "duplicate-tag"));
    } else if (!row) {
      number.classList.add("sheet-placeholder");
    }
    gridRow.append(number);

    for (let c = 0; c < state.columns.length; c++) {
      const value = row ? row.values[c] : null;
      const flags = row ? row.cell_flags[c] : [];
      const text = row ? (value === null ? "(blank)" : value) : "";
      const cell = element("div", null, "sheet-cell");
      cell.setAttribute("role", "gridcell");
      if (flags && flags.length) {
        cell.classList.add("cell-" + flags[0]);
        cell.title = flags.map(f => state.labels[f] || f).join("; ");
      }
      const displayed = element("span", text, "sheet-value");
      if (value === null && row) displayed.classList.add("data-missing");
      cell.append(displayed);
      if (flags && flags.length) {
        cell.append(element("small", flags.map(f => state.labels[f] || f).join(" · "), "cell-note"));
      }
      if (!row) cell.classList.add("sheet-placeholder");
      gridRow.append(cell);
    }
    return gridRow;
  }

  function cachePage(page, payload) {
    // Map insertion order is LRU. Keep the most recently used blocks.
    state.cache.delete(page);
    state.cache.set(page, payload);
    while (state.cache.size > CACHE_LIMIT) {
      const oldest = state.cache.keys().next().value;
      state.cache.delete(oldest);
    }
  }

  function requestPage(page) {
    if (!state.file || page < 1 || state.cache.has(page) ||
        state.loading.has(page) || state.failed.has(page) ||
        state.loading.size >= MAX_IN_FLIGHT) return;
    const epoch = state.epoch;
    const file = state.file;
    const selectedFilter = state.filter;
    state.loading.add(page);

    const body = new FormData();
    body.append("file", file);
    body.append("page", String(page));
    body.append("issue", selectedFilter);

    fetch("/api/rows", {method: "POST", body: body, cache: "no-store"})
      .then(async response => {
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(typeof payload.detail === "string" ? payload.detail : "Could not load rows.");
        }
        return payload;
      })
      .then(payload => {
        if (epoch !== state.epoch) return;
        if (payload.filter !== state.filter) return;
        cachePage(page, payload);
        state.error = "";
        schedulePaint();
      })
      .catch(error => {
        if (epoch !== state.epoch) return;
        state.failed.add(page);
        state.error = "Unable to load some rows: " + (error.message || "Unknown error");
        updateStatus();
      })
      .finally(() => {
        if (epoch !== state.epoch) return;
        state.loading.delete(page);
        schedulePaint();
      });
  }

  function updateStatus(start, end) {
    if (state.error) {
      status.textContent = state.error;
      status.classList.add("error");
    } else {
      status.classList.remove("error");
      status.textContent = state.count.toLocaleString() + " matching rows · " +
        state.flaggedRows.toLocaleString() + " flagged rows · " +
        state.totalRows.toLocaleString() + " total";
    }
    if (typeof start === "number" && typeof end === "number") {
      range.textContent = state.count
        ? "Viewing rows " + (start + 1).toLocaleString() + "–" + end.toLocaleString() +
          " of " + state.count.toLocaleString()
        : "No matching rows";
    }
  }

  function paint() {
    state.pendingFrame = false;
    if (!state.file) return;
    const scrollTop = Math.max(0, view.scrollTop);
    const available = Math.max(1, view.clientHeight - HEADER_HEIGHT);
    const start = Math.min(state.count, Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN));
    const end = Math.min(state.count,
      Math.ceil((scrollTop + available) / ROW_HEIGHT) + OVERSCAN);
    const content = document.createDocumentFragment();
    const pagesNeeded = new Set();

    for (let pos = start; pos < end; pos++) {
      const page = Math.floor(pos / PAGE_SIZE) + 1;
      const cached = state.cache.get(page);
      const row = cached ? cached.rows[pos % PAGE_SIZE] : null;
      if (!cached) pagesNeeded.add(page);
      content.append(rowElement(row, pos));
    }
    if (state.count === 0) {
      const empty = element("div", "No rows match this filter.", "sheet-empty");
      empty.style.top = HEADER_HEIGHT + "px";
      content.append(empty);
    }
    layer.replaceChildren(content);
    updateStatus(start, end);
    // Prefetch nearby pages to reduce visible loading gaps on ordinary scrolling.
    if (end > start) {
      const ahead = Math.floor(end / PAGE_SIZE) + 1;
      if (ahead <= Math.ceil(state.count / PAGE_SIZE)) pagesNeeded.add(ahead);
    }
    for (const page of pagesNeeded) requestPage(page);
  }

  function schedulePaint() {
    if (state.pendingFrame) return;
    state.pendingFrame = true;
    requestAnimationFrame(paint);
  }

  function resetCanvas() {
    canvas.style.height = (HEADER_HEIGHT + state.count * ROW_HEIGHT) + "px";
    canvas.setAttribute("aria-rowcount", String(state.count + 1));
    view.scrollTop = 0;
    view.scrollLeft = 0;
    schedulePaint();
  }

  async function setFilter(value) {
    if (!state.file || state.filter === value) return;
    const epoch = ++state.epoch;
    state.filter = value;
    state.loading = new Set();
    state.failed = new Set();
    state.cache = new Map();
    state.count = 0;
    state.error = "";
    filterSelect.disabled = true;
    status.textContent = "Loading selected rows…";
    const body = new FormData();
    body.append("file", state.file);
    body.append("issue", value);
    body.append("page", "1");
    try {
      const response = await fetch("/api/rows", {method: "POST", body, cache: "no-store"});
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(typeof payload.detail === "string" ? payload.detail : "Could not filter rows.");
      }
      if (epoch !== state.epoch) return;
      state.count = payload.total_matching_rows;
      state.flaggedRows = payload.flagged_rows;
      state.totalRows = payload.total_rows;
      cachePage(1, payload);
      resetCanvas();
    } catch (error) {
      if (epoch === state.epoch) {
        state.error = "Unable to filter rows: " + (error.message || "Unknown error");
        updateStatus();
      }
    } finally {
      if (epoch === state.epoch) filterSelect.disabled = false;
    }
  }

  function start(file, snapshot, profiles) {
    if (!file || !snapshot) return;
    state.epoch++;
    state.file = file;
    state.filter = "all";
    state.count = snapshot.total_matching_rows;
    state.totalRows = snapshot.total_rows;
    state.flaggedRows = snapshot.flagged_rows;
    state.columns = snapshot.columns;
    state.columnProfiles = profiles || [];
    state.labels = snapshot.filter_labels;
    state.cache = new Map();
    state.loading = new Set();
    state.failed = new Set();
    state.error = "";
    filterSelect.value = "all";
    filterSelect.disabled = false;
    cachePage(1, snapshot);
    createHeader();
    resetCanvas();
  }

  function stop() {
    state.epoch++;
    state.file = null;
    state.cache.clear();
    state.loading.clear();
    state.failed.clear();
    layer.replaceChildren();
  }

  filterSelect.addEventListener("change", () => setFilter(filterSelect.value));
  view.addEventListener("scroll", schedulePaint, {passive: true});
  window.DQDSpreadsheet = {start, stop};
})();
