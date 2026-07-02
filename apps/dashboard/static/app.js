/* ============================================================
   AI Company OS — App JS v3
   Premium UI: toasts · search · counters · drawer · HTMX rendering
   ============================================================ */

"use strict";

/* ── HTML Escape Helper ─────────────────────────────────────── */
function _esc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/* ── Toast Notification System ──────────────────────────────── */
var _toastQueue = [];
var _toastTimer = null;

function showToast(title, message, type, duration) {
  type     = type     || "info";
  duration = duration || 4000;

  var icons = { success: "✓", error: "✕", warning: "⚠", info: "ℹ" };
  var container = document.getElementById("toast-container");
  if (!container) return;

  var toast = document.createElement("div");
  toast.className = "toast toast-" + type;
  toast.innerHTML =
    '<span class="toast-icon">' + (icons[type] || "ℹ") + "</span>" +
    '<div class="toast-body">' +
      '<div class="toast-title">' + _esc(title) + "</div>" +
      (message ? '<div class="toast-message">' + _esc(message) + "</div>" : "") +
    "</div>" +
    '<button class="toast-close" aria-label="Kapat">✕</button>';

  toast.querySelector(".toast-close").addEventListener("click", function () {
    _dismissToast(toast);
  });

  container.appendChild(toast);

  var t = setTimeout(function () { _dismissToast(toast); }, duration);
  toast._dismissTimer = t;
}

function _dismissToast(toast) {
  if (!toast || !toast.parentNode) return;
  clearTimeout(toast._dismissTimer);
  toast.classList.add("toast-leaving");
  setTimeout(function () {
    if (toast.parentNode) toast.parentNode.removeChild(toast);
  }, 280);
}

/* ── Client-side Search / Filter ────────────────────────────── */
function _initSearch(inputId, itemSelector, textSelector) {
  var input = document.getElementById(inputId);
  if (!input) return;

  input.addEventListener("input", function () {
    var q = input.value.trim().toLowerCase();
    var items = document.querySelectorAll(itemSelector);
    var count = 0;
    items.forEach(function (el) {
      var text = textSelector
        ? (el.querySelector(textSelector) || el).textContent.toLowerCase()
        : el.textContent.toLowerCase();
      var visible = !q || text.indexOf(q) !== -1;
      el.style.display = visible ? "" : "none";
      if (visible) count++;
    });
  });
}

/* ── Global Search (navbar) ─────────────────────────────────── */
function _initGlobalSearch() {
  var input = document.getElementById("global-search");
  if (!input) return;

  input.addEventListener("focus", function () {
    // Delegate to current page filter if one exists
    var pageSearch = document.getElementById("page-search");
    if (pageSearch) { pageSearch.focus(); input.blur(); }
  });

  // ⌘K / Ctrl+K shortcut
  document.addEventListener("keydown", function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      var pageSearch = document.getElementById("page-search");
      if (pageSearch) { pageSearch.focus(); }
      else { input.focus(); }
    }
    if (e.key === "Escape") { input.blur(); }
  });
}

/* ── Animated Counters ───────────────────────────────────────── */
function _initCounters() {
  var counters = document.querySelectorAll(".counter-value[data-target]");
  counters.forEach(function (el) {
    var target = parseInt(el.getAttribute("data-target"), 10);
    if (isNaN(target) || target === 0) { el.textContent = target || "0"; return; }
    var duration = 700;
    var startTime = null;
    function step(ts) {
      if (!startTime) startTime = ts;
      var progress = Math.min((ts - startTime) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.round(target * eased);
      if (progress < 1) requestAnimationFrame(step);
      else el.textContent = target;
    }
    requestAnimationFrame(step);
  });
}

/* ── Collapsible Sections ────────────────────────────────────── */
function _initCollapsibles() {
  document.querySelectorAll(".collapsible-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var expanded = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", String(!expanded));
      var bodyId = btn.getAttribute("data-controls");
      var body = bodyId ? document.getElementById(bodyId) : btn.nextElementSibling;
      if (body) body.classList.toggle("open", !expanded);
    });
  });
}

/* ── Skeleton → reveal ───────────────────────────────────────── */
function _revealOnLoad(panel) {
  panel.classList.remove("skeleton-loading");
}

/* ── HTMX poll indicator ────────────────────────────────────── */
document.addEventListener("htmx:beforeRequest", function (evt) {
  var indicators = [
    document.getElementById("poll-status"),
    document.getElementById("events-poll-status"),
    document.getElementById("status-poll-indicator"),
    document.getElementById("agent-poll-status"),
  ];
  indicators.forEach(function (el) {
    if (el) el.textContent = "yenileniyor…";
  });
});

document.addEventListener("htmx:afterRequest", function (evt) {
  var indicator =
    document.getElementById("poll-status") ||
    document.getElementById("events-poll-status");
  if (indicator) {
    var now = new Date();
    var ts = [now.getHours(), now.getMinutes(), now.getSeconds()]
      .map(function (n) { return String(n).padStart(2, "0"); })
      .join(":");
    indicator.textContent = ts;
  }
});

/* ── HTMX JSON Interception (beforeSwap) ───────────────────── */
document.addEventListener("htmx:beforeSwap", function (evt) {
  var target = evt.detail.target;
  if (!target) return;
  var ids = ["event-timeline", "live-event-feed", "agent-status-panel"];
  if (ids.indexOf(target.id) === -1) return;
  try {
    var text   = evt.detail.xhr.responseText;
    var parsed = JSON.parse(text);
    target.setAttribute("data-raw", text);
    evt.detail.shouldSwap = false;
    if (target.id === "event-timeline")    _renderTimeline(target, parsed);
    if (target.id === "live-event-feed")   _renderEventFeed(target, parsed);
    if (target.id === "agent-status-panel") _renderAgentCards(target, parsed);
  } catch (e) { /* not JSON — let HTMX swap normally */ }
});

/* Canlı Durum Panel (afterSwap) */
document.addEventListener("htmx:afterSwap", function (evt) {
  var target = evt.detail.target;
  if (!target) return;
  if (target.id === "canli-durum-panel") {
    try {
      var data = JSON.parse(target.getAttribute("data-json") || "null");
      if (!data) return;
      _renderStatusComponents(target, data.components || []);
    } catch (e) { /* ignore */ }
  }
});

/* ── Renderers ──────────────────────────────────────────────── */

var _CHANNEL_COLORS = {
  "SYSTEM": "system", "PROJECT": "project", "WORKFLOW": "workflow",
  "DISCUSSION": "discussion", "MEMORY": "memory", "DECISION": "decision",
  "RUNTIME": "runtime", "CEO": "ceo",
};

function _channelClass(ch) {
  var key = (ch || "").toUpperCase();
  var slug = _CHANNEL_COLORS[key] || key.toLowerCase();
  return "event-channel event-channel-" + slug;
}

function _renderTimeline(target, events) {
  if (!Array.isArray(events) || events.length === 0) {
    target.innerHTML = '<p class="empty">Henüz olay yok.</p>';
    return;
  }
  target.innerHTML = events.map(function (ev) {
    var ch       = (ev.channel || "").toUpperCase();
    var sentence = ev.sentence || (ev.action || "").replace(/_/g, " ");
    return (
      '<div class="timeline-item">' +
        '<span class="timeline-ts">' + _esc(ev.timestamp_hms || "") + "</span>" +
        '<span class="' + _channelClass(ch) + '">' + ch + "</span>" +
        '<span class="timeline-sentence">' + _esc(sentence) + "</span>" +
      "</div>"
    );
  }).join("");
}

function _renderEventFeed(target, events) {
  if (!Array.isArray(events) || events.length === 0) {
    target.innerHTML = '<p class="empty">Henüz olay yok.</p>';
    return;
  }
  target.innerHTML = events.map(function (ev) {
    var ch       = (ev.channel || "").toUpperCase();
    var sentence = ev.sentence || (ev.action || "").replace(/_/g, " ");
    var ts       = (ev.timestamp || "").substring(11, 19) || ev.timestamp_hms || "";
    return (
      '<div class="timeline-row">' +
        '<span class="event-ts">' + _esc(ts) + "</span>" +
        '<span class="' + _channelClass(ch) + '">' + ch + "</span>" +
        '<span class="timeline-sentence-full">' + _esc(sentence) + "</span>" +
      "</div>"
    );
  }).join("");
}

function _renderAgentCards(target, agents) {
  if (!Array.isArray(agents) || agents.length === 0) {
    target.innerHTML = '<p class="empty">Henüz çalışan yok.</p>';
    return;
  }
  target.innerHTML = agents.map(function (a) {
    var status = (a.status || "ACTIVE").toUpperCase();
    var dotClass = "agent-status-dot-idle";
    var statusLabel = "Bekliyor";
    if (status === "ACTIVE")  { dotClass = "agent-status-dot-active";  statusLabel = "Aktif"; }
    if (status === "WORKING") { dotClass = "agent-status-dot-working"; statusLabel = "Çalışıyor"; }

    var taskHtml = a.current_task
      ? '<div class="agent-card-task">' + _esc(a.current_task.title || "") + "</div>"
      : "";

    var pct = a.workload || 0;

    return (
      '<div class="agent-card">' +
        '<div class="agent-card-name">' + _esc(a.name || "") + "</div>" +
        '<div class="agent-card-role">' + _esc(a.role || "") + "</div>" +
        '<div class="agent-card-status">' +
          '<span class="agent-status-dot ' + dotClass + '"></span>' +
          '<span>' + statusLabel + "</span>" +
        "</div>" +
        taskHtml +
        '<div class="agent-card-workload">' +
          '<div class="agent-card-workload-label">İş Yükü: ' + pct + "%</div>" +
          '<div class="progress-bar">' +
            '<div class="progress-fill progress-fill-animated" style="width:' + pct + '%"></div>' +
          "</div>" +
        "</div>" +
      "</div>"
    );
  }).join("");
}

function _renderStatusComponents(target, components) {
  target.innerHTML = components.map(function (c) {
    var bc = "status-badge-waiting";
    if (c.status === "ACTIVE")    bc = "status-badge-active";
    if (c.status === "RUNNING")   bc = "status-badge-running";
    if (c.status === "COMPLETED") bc = "status-badge-completed";
    if (c.status === "FAILED")    bc = "status-badge-failed";
    return (
      '<div class="status-component">' +
        '<span class="status-badge ' + bc + '"></span>' +
        '<span class="status-component-label">' + _esc(c.label || c.key || "") + "</span>" +
      "</div>"
    );
  }).join("");
}

/* ── CEO Command Form ───────────────────────────────────────── */
function _initCommandForm() {
  var form      = document.getElementById("ceo-command-form");
  if (!form) return;
  var input     = document.getElementById("ceo-command-input");
  var btn       = document.getElementById("ceo-start-btn");
  var spinner   = document.getElementById("command-spinner");
  var statusEl  = document.getElementById("command-status");

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var command = (input ? input.value : "").trim();
    if (command.length < 10) {
      showToast("Hata", "En az 10 karakter girin.", "error");
      return;
    }
    if (btn) btn.disabled = true;
    if (spinner) spinner.style.display = "inline-flex";
    if (statusEl) statusEl.textContent = "gönderiliyor…";

    fetch("/api/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: command }),
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (btn) btn.disabled = false;
        if (spinner) spinner.style.display = "none";
        if (data.success) {
          if (statusEl) statusEl.textContent = "tamamlandı";
          if (input) input.value = "";
          showToast(
            "Komut tamamlandı",
            "Oturum " + (data.session_id || "").slice(0, 8) + "… · " + (data.event_count || 0) + " olay",
            "success"
          );
          _showCommandResult(command, true, null);
          setTimeout(function () { window.location.reload(); }, 1800);
        } else {
          if (statusEl) statusEl.textContent = "hata";
          showToast("Komut başarısız", data.error || "Bilinmeyen hata.", "error");
          _showCommandResult(command, false, data.error);
        }
      })
      .catch(function (err) {
        if (btn) btn.disabled = false;
        if (spinner) spinner.style.display = "none";
        if (statusEl) statusEl.textContent = "bağlantı hatası";
        showToast("Bağlantı hatası", err.toString(), "error");
      });
  });
}

function _showCommandResult(command, success, errorMsg) {
  var form = document.getElementById("ceo-command-form");
  if (!form) return;
  var el = document.getElementById("last-command-result") || document.createElement("div");
  el.id = "last-command-result";
  el.className = "command-result " + (success ? "command-result-success" : "command-result-error");
  el.innerHTML = success
    ? "<span>✓</span><span>" + _esc(command.slice(0, 80)) + (command.length > 80 ? "…" : "") + "</span>"
    : "<span>✕</span><span>" + _esc(errorMsg || "Hata") + "</span>";
  if (!el.parentNode) form.parentNode.appendChild(el);
}

/* ── Employee Drawer ────────────────────────────────────────── */
function _initEmployeeDrawer() {
  document.querySelectorAll(".employee-row").forEach(function (row) {
    row.addEventListener("click", function () {
      openEmpDrawer({
        id:        row.getAttribute("data-emp-id")        || "",
        name:      row.getAttribute("data-emp-name")      || "",
        role:      row.getAttribute("data-emp-role")      || "",
        dept:      row.getAttribute("data-emp-dept")      || "",
        seniority: row.getAttribute("data-emp-seniority") || "",
        status:    row.getAttribute("data-emp-status")    || "",
        skills:    row.getAttribute("data-emp-skills")    || "",
      });
    });
  });
}

function openEmpDrawer(emp) {
  var overlay = document.getElementById("emp-drawer-overlay");
  var drawer  = document.getElementById("emp-drawer");
  if (!drawer) return;

  var nameEl      = document.getElementById("drawer-emp-name");
  var roleEl      = document.getElementById("drawer-emp-role");
  var deptEl      = document.getElementById("drawer-emp-dept");
  var seniorityEl = document.getElementById("drawer-emp-seniority");
  var statusEl    = document.getElementById("drawer-emp-status");
  var skillsEl    = document.getElementById("drawer-emp-skills");

  if (nameEl)      nameEl.textContent      = emp.name      || "Çalışan";
  if (roleEl)      roleEl.textContent      = emp.role      || "—";
  if (deptEl)      deptEl.textContent      = emp.dept      || "—";
  if (seniorityEl) seniorityEl.textContent = emp.seniority || "—";
  if (statusEl)    statusEl.textContent    = emp.status    || "—";

  if (skillsEl) {
    skillsEl.innerHTML = "";
    var skills = (emp.skills || "").split(",").map(function (s) { return s.trim(); }).filter(Boolean);
    skills.forEach(function (skill) {
      var tag = document.createElement("span");
      tag.className = "skill-tag";
      tag.textContent = skill;
      skillsEl.appendChild(tag);
    });
  }

  // Fetch live current task
  var taskDiv = document.getElementById("drawer-current-task");
  if (taskDiv) taskDiv.style.display = "none";

  fetch("/api/agent-status")
    .then(function (r) { return r.json(); })
    .then(function (agents) {
      var agent = agents.find(function (a) { return a.id === emp.id; });
      if (agent && agent.current_task && taskDiv) {
        taskDiv.style.display = "block";
        var t = agent.current_task;
        var el1 = document.getElementById("drawer-task-title");
        var el2 = document.getElementById("drawer-task-status");
        var el3 = document.getElementById("drawer-task-priority");
        if (el1) el1.textContent = t.title    || "";
        if (el2) { el2.textContent = t.status || ""; el2.className = "badge badge-task-" + (t.status || "").toLowerCase(); }
        if (el3) { el3.textContent = t.priority || ""; el3.className = "badge badge-" + (t.priority || "").toLowerCase(); }
      }
    })
    .catch(function () {});

  if (overlay) { overlay.style.display = "block"; }
  drawer.style.display = "flex";
  document.body.style.overflow = "hidden";
}

function closeEmpDrawer() {
  var overlay = document.getElementById("emp-drawer-overlay");
  var drawer  = document.getElementById("emp-drawer");
  if (overlay) overlay.style.display = "none";
  if (drawer)  drawer.style.display  = "none";
  document.body.style.overflow = "";
}

/* ── Progress Bar Reveal ─────────────────────────────────────── */
function _initProgressBars() {
  // Trigger CSS transition by setting a tiny delay
  setTimeout(function () {
    document.querySelectorAll(".progress-fill-animated").forEach(function (el) {
      var w = el.style.width;
      el.style.width = "0%";
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          el.style.width = w;
        });
      });
    });
  }, 80);
}

/* ── Bell / Notification badge ───────────────────────────────── */
function _initNavBell() {
  var btn = document.getElementById("nav-bell-btn");
  if (!btn) return;
  btn.addEventListener("click", function () {
    showToast("Bildirimler", "Yeni bir CEO komutu akışı tamamlandı.", "info");
  });
}

/* ── Keyboard: Escape closes drawer ─────────────────────────── */
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    var drawer = document.getElementById("emp-drawer");
    if (drawer && drawer.style.display !== "none") closeEmpDrawer();
  }
});

/* ── Server-Sent Events (SSE) client ────────────────────────── */
var _sseSource = null;

function _initSSE() {
  if (!window.EventSource) return;

  _sseSource = new EventSource("/api/events/stream");

  _sseSource.onopen = function () { _setSseStatus(true); };
  _sseSource.onerror = function () { _setSseStatus(false); };

  _sseSource.onmessage = function (e) {
    try {
      var data = JSON.parse(e.data);
      if (data.type === "connected") { _setSseStatus(true); return; }
      if (data.type === "event") {
        _appendLiveTimelineRow(data);
        _fetchAndUpdateCounters();
      }
    } catch (ex) {}
  };
}

function _setSseStatus(connected) {
  var dot   = document.getElementById("sse-status-dot");
  var label = document.getElementById("sse-status-label");
  if (dot)   dot.className = "status-dot" + (connected ? " sse-dot-live" : " sse-dot-reconnecting");
  if (label) label.textContent = connected ? "CANLI" : "YENİDEN BAĞLANIYOR";
}

function _appendLiveTimelineRow(ev) {
  var feed = document.getElementById("event-timeline") ||
             document.getElementById("live-event-feed");
  if (!feed) return;
  var ch  = (ev.channel || "").toUpperCase();
  var row = document.createElement("div");
  row.className = "timeline-item sse-new-row";
  row.innerHTML =
    '<span class="timeline-ts">' + _esc(ev.timestamp_hms || "") + "</span>" +
    '<span class="' + _channelClass(ch) + '">' + ch + "</span>" +
    '<span class="timeline-sentence">' + _esc(ev.sentence || ev.action || "") + "</span>";
  feed.insertBefore(row, feed.firstChild);
  requestAnimationFrame(function () { row.classList.add("sse-row-visible"); });
  var rows = feed.querySelectorAll(".timeline-item");
  if (rows.length > 50) rows[rows.length - 1].remove();
}

function _fetchAndUpdateCounters() {
  fetch("/api/stats")
    .then(function (r) { return r.json(); })
    .then(function (d) {
      _animateCounter("#live-counter-projects",  d.total_projects        || 0);
      _animateCounter("#live-counter-employees", d.total_employees       || 0);
      _animateCounter("#live-counter-events",    d.total_events          || 0);
      _animateCounter("#live-counter-memory",    d.total_memory_entries  || 0);
    })
    .catch(function () {});
}

function _animateCounter(selector, newValue) {
  var el = document.querySelector(selector);
  if (!el) return;
  var current = parseInt(el.textContent, 10) || 0;
  if (current === newValue) return;
  var startTime = null;
  var startValue = current;
  var duration = 500;
  function step(ts) {
    if (!startTime) startTime = ts;
    var p = Math.min((ts - startTime) / duration, 1);
    el.textContent = Math.round(startValue + (newValue - startValue) * p);
    if (p < 1) requestAnimationFrame(step);
    else el.textContent = newValue;
  }
  requestAnimationFrame(step);
}

/* ── DOMContentLoaded ────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", function () {
  _initGlobalSearch();
  _initCounters();
  _initCollapsibles();
  _initCommandForm();
  _initEmployeeDrawer();
  _initProgressBars();
  _initNavBell();
  _initSSE();

  // Page-specific searches
  _initSearch("page-search", ".project-card",    ".card-header h2");
  _initSearch("emp-search",  ".employee-row",     ".td-name");
  _initSearch("event-search", ".timeline-row",    ".timeline-sentence-full");
});
