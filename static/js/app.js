/**
 * OSINT Username Finder — Frontend
 * Connects to Flask REST API for search, history, stats, and exports.
 */

const API = {
  health: "/api/health",
  stats: "/api/stats",
  history: "/api/history",
  search: "/api/search",
  exportJson: "/api/export/json",
  exportPdf: "/api/export/pdf",
  sitesCount: "/api/sites/count",
};

let currentResults = [];
let currentUsername = "";
let currentSearchId = null;
let resultsChart = null;
let responseChart = null;
let activeFilter = "all";

// --- DOM refs ---
const els = {
  sidebar: document.getElementById("sidebar"),
  menuToggle: document.getElementById("menuToggle"),
  navLinks: document.querySelectorAll(".nav-link"),
  sections: document.querySelectorAll(".section"),
  searchForm: document.getElementById("searchForm"),
  usernameInput: document.getElementById("usernameInput"),
  screenshotsCheck: document.getElementById("screenshotsCheck"),
  searchBtn: document.getElementById("searchBtn"),
  loader: document.getElementById("loader"),
  loaderProgress: document.getElementById("loaderProgress"),
  resultsGrid: document.getElementById("resultsGrid"),
  resultsUsername: document.getElementById("resultsUsername"),
  exportJsonBtn: document.getElementById("exportJsonBtn"),
  exportPdfBtn: document.getElementById("exportPdfBtn"),
  historyBody: document.getElementById("historyBody"),
  apiStatus: document.getElementById("apiStatus"),
  sitesCount: document.getElementById("sitesCount"),
  statSearches: document.getElementById("statSearches"),
  statFound: document.getElementById("statFound"),
  statUsernames: document.getElementById("statUsernames"),
  statAvgMs: document.getElementById("statAvgMs"),
  toastContainer: document.getElementById("toastContainer"),
  filterBtns: document.querySelectorAll(".filter-btn"),
};

// --- Navigation ---
function showSection(name) {
  els.sections.forEach((s) => s.classList.toggle("active", s.id === name));
  els.navLinks.forEach((l) =>
    l.classList.toggle("active", l.dataset.section === name)
  );
  if (window.innerWidth <= 768) els.sidebar.classList.remove("open");
}

els.navLinks.forEach((link) => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    showSection(link.dataset.section);
  });
});

els.menuToggle?.addEventListener("click", () => {
  els.sidebar.classList.toggle("open");
});

// --- Toast notifications ---
function toast(message, type = "success") {
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.textContent = message;
  els.toastContainer.appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

// --- API helpers ---
async function apiGet(url) {
  const res = await fetch(url);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

async function apiPost(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

// --- Init: health, stats, site count ---
async function initApp() {
  try {
    await apiGet(API.health);
    els.apiStatus.classList.add("online");
  } catch {
    els.apiStatus.classList.remove("online");
    toast("API offline — start the Flask server", "error");
  }

  try {
    const { count } = await apiGet(API.sitesCount);
    els.sitesCount.textContent = `${count} sites`;
  } catch {
    els.sitesCount.textContent = "50+ sites";
  }

  await loadStats();
  await loadHistory();
}

async function loadStats() {
  try {
    const s = await apiGet(API.stats);
    els.statSearches.textContent = s.total_searches;
    els.statFound.textContent = s.total_profiles_found;
    els.statUsernames.textContent = s.unique_usernames;
    els.statAvgMs.textContent = s.avg_response_ms;
  } catch {
    /* ignore */
  }
}

async function loadHistory() {
  try {
    const { history } = await apiGet(API.history);
    if (!history.length) {
      els.historyBody.innerHTML =
        '<tr><td colspan="6" class="empty-state">No history yet.</td></tr>';
      return;
    }
    els.historyBody.innerHTML = history
      .map(
        (h) => `
      <tr>
        <td>${escapeHtml(h.username)}</td>
        <td class="accent">${h.found_count}</td>
        <td>${h.total_sites}</td>
        <td>${h.avg_response_ms ?? "—"}</td>
        <td>${formatDate(h.created_at)}</td>
        <td><button class="btn-link" data-id="${h.id}">View</button></td>
      </tr>`
      )
      .join("");

    els.historyBody.querySelectorAll(".btn-link").forEach((btn) => {
      btn.addEventListener("click", () => loadHistoryDetail(btn.dataset.id));
    });
  } catch (e) {
    toast(e.message, "error");
  }
}

async function loadHistoryDetail(id) {
  try {
    const data = await apiGet(`${API.history}/${id}`);
    currentUsername = data.search.username;
    currentSearchId = data.search.id;
    currentResults = data.results.map((r) => ({
      site_name: r.site_name,
      url: r.url,
      status: r.status,
      response_time_ms: r.response_time_ms,
      screenshot_path: r.screenshot_path,
      category: "other",
    }));
    renderResults();
    updateCharts();
    showSection("results");
    enableExport(true);
  } catch (e) {
    toast(e.message, "error");
  }
}

// --- Search ---
els.searchForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = els.usernameInput.value.trim();
  if (!username) return;

  els.searchBtn.disabled = true;
  els.loader.classList.remove("hidden");
  simulateProgress();

  try {
    const data = await apiPost(API.search, {
      username,
      screenshots: els.screenshotsCheck.checked,
    });

    currentUsername = data.username;
    currentSearchId = data.search_id;
    currentResults = data.results;

    renderResults();
    updateCharts();
    enableExport(true);
    await loadStats();
    await loadHistory();

    showSection("results");
    toast(
      `Scan complete: ${data.summary.found} profiles found on ${data.summary.total} sites`
    );
  } catch (err) {
    toast(err.message, "error");
  } finally {
    els.searchBtn.disabled = false;
    els.loader.classList.add("hidden");
    clearInterval(progressTimer);
    els.loaderProgress.textContent = "0";
  }
});

let progressTimer;
function simulateProgress() {
  let p = 0;
  clearInterval(progressTimer);
  progressTimer = setInterval(() => {
    p = Math.min(p + Math.random() * 12, 92);
    els.loaderProgress.textContent = Math.floor(p);
  }, 400);
}

// --- Render results ---
function renderResults() {
  els.resultsUsername.textContent = currentUsername
    ? `@${currentUsername}`
    : "";

  const filtered =
    activeFilter === "all"
      ? currentResults
      : currentResults.filter((r) => r.status === activeFilter);

  if (!filtered.length) {
    els.resultsGrid.innerHTML =
      '<p class="empty-state">No results for this filter.</p>';
    return;
  }

  els.resultsGrid.innerHTML = filtered
    .map((r, i) => buildResultCard(r, i))
    .join("");

  els.resultsGrid.querySelectorAll(".btn-copy").forEach((btn) => {
    btn.addEventListener("click", () => {
      navigator.clipboard.writeText(btn.dataset.url).then(() => {
        toast("Link copied to clipboard");
      });
    });
  });
}

function buildResultCard(r, index) {
  const statusLabel =
    r.status === "found"
      ? "Found"
      : r.status === "not_found"
        ? "Not Found"
        : "Error";
  const screenshot = r.screenshot_path
    ? `<img class="result-screenshot" src="${r.screenshot_path}" alt="Screenshot" loading="lazy">`
    : "";

  const actions =
    r.status === "found" && r.url
      ? `<div class="result-actions">
          <button type="button" class="btn-copy" data-url="${escapeAttr(r.url)}">Copy Link</button>
          <a class="btn-visit" href="${escapeAttr(r.url)}" target="_blank" rel="noopener">Visit</a>
        </div>`
      : "";

  return `
    <article class="result-card glass ${r.status}" style="animation-delay:${index * 0.03}s">
      <div class="result-header">
        <span class="result-site">${escapeHtml(r.site_name)}</span>
        <span class="badge ${r.status}">${statusLabel}</span>
      </div>
      <p class="result-meta">${r.response_time_ms ?? "—"} ms · ${escapeHtml(r.category || "other")}</p>
      ${r.url ? `<a class="result-link" href="${escapeAttr(r.url)}" target="_blank" rel="noopener">${escapeHtml(r.url)}</a>` : ""}
      ${r.error_message ? `<p class="result-meta">${escapeHtml(r.error_message)}</p>` : ""}
      ${actions}
      ${screenshot}
    </article>`;
}

els.filterBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    els.filterBtns.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    activeFilter = btn.dataset.filter;
    renderResults();
  });
});

function enableExport(on) {
  els.exportJsonBtn.disabled = !on;
  els.exportPdfBtn.disabled = !on;
}

// --- Export ---
els.exportJsonBtn.addEventListener("click", async () => {
  try {
    const meta = await apiPost(API.exportJson, {
      username: currentUsername,
      results: currentResults,
      search_id: currentSearchId,
    });
    window.location.href = meta.download_url;
    toast("JSON report ready");
  } catch (e) {
    toast(e.message, "error");
  }
});

els.exportPdfBtn.addEventListener("click", async () => {
  try {
    const meta = await apiPost(API.exportPdf, {
      username: currentUsername,
      results: currentResults,
      search_id: currentSearchId,
    });
    window.location.href = meta.download_url;
    toast("PDF report ready");
  } catch (e) {
    toast(e.message, "error");
  }
});

// --- Charts (Chart.js) ---
function updateCharts() {
  const found = currentResults.filter((r) => r.status === "found").length;
  const notFound = currentResults.filter((r) => r.status === "not_found").length;
  const errors = currentResults.filter((r) => r.status === "error").length;

  const pieCtx = document.getElementById("resultsChart");
  if (resultsChart) resultsChart.destroy();
  resultsChart = new Chart(pieCtx, {
    type: "doughnut",
    data: {
      labels: ["Found", "Not Found", "Errors"],
      datasets: [
        {
          data: [found, notFound, errors],
          backgroundColor: ["#00ff88", "#475569", "#ff4757"],
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: "#94a3b8" } },
      },
    },
  });

  const top = [...currentResults]
    .filter((r) => r.response_time_ms)
    .sort((a, b) => a.response_time_ms - b.response_time_ms)
    .slice(0, 10);

  const barCtx = document.getElementById("responseChart");
  if (responseChart) responseChart.destroy();
  responseChart = new Chart(barCtx, {
    type: "bar",
    data: {
      labels: top.map((r) => r.site_name),
      datasets: [
        {
          label: "ms",
          data: top.map((r) => r.response_time_ms),
          backgroundColor: "rgba(0, 255, 136, 0.5)",
          borderColor: "#00ff88",
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        x: { ticks: { color: "#94a3b8", maxRotation: 45 } },
        y: { ticks: { color: "#94a3b8" } },
      },
      plugins: { legend: { display: false } },
    },
  });
}

// --- Utils ---
function escapeHtml(str) {
  const d = document.createElement("span");
  d.textContent = str ?? "";
  return d.innerHTML;
}

function escapeAttr(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;");
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

document.addEventListener("DOMContentLoaded", initApp);
