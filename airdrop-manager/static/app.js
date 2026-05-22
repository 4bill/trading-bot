// Airdrop manager dashboard logic.
// Talks to the FastAPI JSON API. No build step, no framework.

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const CATEGORY_LABEL = {
  testnet: "Testnet",
  bridge_swap: "Bridge/Swap",
  daily_claim: "Daily Claim",
  other: "Other",
};

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

// ----- tabs -----
$$(".tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    $$(".tabs button").forEach((b) => b.classList.remove("on"));
    btn.classList.add("on");
    const tab = btn.dataset.tab;
    $$("section[data-pane]").forEach((s) => (s.hidden = s.dataset.pane !== tab));
  });
});

// ----- dashboard -----
async function loadDashboard() {
  const [summary, tasks, projects] = await Promise.all([
    api("/api/summary"),
    api("/api/tasks"),
    api("/api/projects"),
  ]);

  // progress
  const total = summary.total || 0;
  const done = summary.done || 0;
  const pct = total ? Math.round((done / total) * 100) : 0;
  $("#progress-bar").style.width = pct + "%";

  // stats
  const grid = $("#summary-grid");
  grid.innerHTML = "";
  grid.appendChild(stat(`${done}/${total}`, `Done today (${pct}%)`));
  grid.appendChild(stat(summary.pending, "Pending"));
  for (const c of summary.per_category || []) {
    const label = CATEGORY_LABEL[c.category] || c.category;
    grid.appendChild(stat(`${c.done || 0}/${(c.done || 0) + (c.pending || 0)}`, label));
  }

  // tasks by project
  const tasksByProject = {};
  for (const t of tasks) {
    (tasksByProject[t.project_id] = tasksByProject[t.project_id] || []).push(t);
  }

  const wrap = $("#dashboard-projects");
  wrap.innerHTML = "";
  if (!projects.length) {
    wrap.innerHTML = `<p class="muted">No projects yet — add some on the <b>Projects</b> tab.</p>`;
    return;
  }

  for (const p of projects) {
    const ts = tasksByProject[p.id] || [];
    const pDone = ts.filter((t) => t.status === "done").length;
    const card = document.createElement("div");
    card.className = `card priority-${p.priority || 2}`;
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap">
        <div>
          <b>${escapeHtml(p.name)}</b>
          <span class="pill ${p.category}">${CATEGORY_LABEL[p.category] || p.category}</span>
          ${p.chain ? `<span class="muted"> · ${escapeHtml(p.chain)}</span>` : ""}
        </div>
        <span class="muted">${pDone}/${ts.length} done</span>
      </div>
      ${p.url ? `<div class="muted" style="margin-top:4px"><a href="${p.url}" target="_blank" rel="noopener" style="color:var(--accent)">${escapeHtml(p.url)}</a></div>` : ""}
      <div class="task-list" style="margin-top:8px"></div>
      ${ts.length ? "" : `<p class="muted" style="margin:6px 0 0">No tasks yet for this project.</p>`}
    `;
    const list = card.querySelector(".task-list");
    for (const t of ts) {
      list.appendChild(taskRow(t));
    }
    wrap.appendChild(card);
  }
}

function stat(value, label) {
  const el = document.createElement("div");
  el.className = "stat";
  el.innerHTML = `<b>${value}</b><div class="muted">${escapeHtml(label)}</div>`;
  return el;
}

function taskRow(t) {
  const row = document.createElement("div");
  row.className = `task-row ${t.status === "done" ? "done" : ""}`;
  const walletLabel = t.wallet_label ? ` · ${escapeHtml(t.wallet_label)}` : "";
  row.innerHTML = `
    <div class="left">
      <button class="checkbox ${t.status === "done" ? "done" : ""}" title="Toggle">${t.status === "done" ? "✓" : ""}</button>
      <div class="title">
        ${escapeHtml(t.title)}
        <span class="muted">· ${t.cadence}${walletLabel}</span>
      </div>
    </div>
    <button class="btn danger sm" data-act="del">Delete</button>
  `;
  row.querySelector(".checkbox").addEventListener("click", async () => {
    if (t.status === "done") {
      await api(`/api/tasks/${t.id}/undo`, { method: "POST" });
    } else {
      await api(`/api/tasks/${t.id}/done`, { method: "POST", body: "{}" });
    }
    await refreshAll();
  });
  row.querySelector('[data-act="del"]').addEventListener("click", async () => {
    if (!confirm(`Delete task "${t.title}"?`)) return;
    await api(`/api/tasks/${t.id}`, { method: "DELETE" });
    await refreshAll();
  });
  return row;
}

// ----- projects -----
async function loadProjects() {
  const [projects, wallets] = await Promise.all([api("/api/projects"), api("/api/wallets")]);

  // dropdowns for "Add task"
  const tProj = $("#t-project");
  tProj.innerHTML = projects
    .map((p) => `<option value="${p.id}">${escapeHtml(p.name)}</option>`)
    .join("");
  const tWal = $("#t-wallet");
  tWal.innerHTML =
    `<option value="">— none —</option>` +
    wallets.map((w) => `<option value="${w.id}">${escapeHtml(w.label)}</option>`).join("");

  // list
  const wrap = $("#projects-list");
  wrap.innerHTML = "";
  if (!projects.length) {
    wrap.innerHTML = `<p class="muted">No projects yet.</p>`;
    return;
  }
  for (const p of projects) {
    const card = document.createElement("div");
    card.className = `card priority-${p.priority || 2}`;
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap">
        <div>
          <b>${escapeHtml(p.name)}</b>
          <span class="pill ${p.category}">${CATEGORY_LABEL[p.category] || p.category}</span>
          ${p.chain ? `<span class="muted"> · ${escapeHtml(p.chain)}</span>` : ""}
        </div>
        <button class="btn danger sm" data-act="del">Delete</button>
      </div>
      ${p.notes ? `<p class="muted" style="margin:6px 0 0;white-space:pre-wrap">${escapeHtml(p.notes)}</p>` : ""}
      ${p.url ? `<div class="muted" style="margin-top:4px"><a href="${p.url}" target="_blank" rel="noopener" style="color:var(--accent)">${escapeHtml(p.url)}</a></div>` : ""}
    `;
    card.querySelector('[data-act="del"]').addEventListener("click", async () => {
      if (!confirm(`Delete "${p.name}" and all its tasks?`)) return;
      await api(`/api/projects/${p.id}`, { method: "DELETE" });
      await refreshAll();
    });
    wrap.appendChild(card);
  }
}

// ----- wallets -----
async function loadWallets() {
  const wallets = await api("/api/wallets");
  const wrap = $("#wallets-list");
  wrap.innerHTML = "";
  if (!wallets.length) {
    wrap.innerHTML = `<p class="muted">No wallets yet.</p>`;
    return;
  }
  for (const w of wallets) {
    const card = document.createElement("div");
    card.className = "card";
    const short = w.address.length > 14 ? `${w.address.slice(0, 6)}…${w.address.slice(-4)}` : w.address;
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;align-items:center">
        <div>
          <b>${escapeHtml(w.label)}</b>
          ${w.chain ? `<span class="muted"> · ${escapeHtml(w.chain)}</span>` : ""}
          <div class="muted" title="${escapeHtml(w.address)}">${escapeHtml(short)}</div>
        </div>
        <button class="btn danger sm" data-act="del">Delete</button>
      </div>
    `;
    card.querySelector('[data-act="del"]').addEventListener("click", async () => {
      if (!confirm(`Delete wallet "${w.label}"?`)) return;
      await api(`/api/wallets/${w.id}`, { method: "DELETE" });
      await refreshAll();
    });
    wrap.appendChild(card);
  }
}

// ----- form submits -----
$("#p-add").addEventListener("click", async () => {
  const payload = {
    name: $("#p-name").value.trim(),
    category: $("#p-category").value,
    chain: $("#p-chain").value.trim() || null,
    url: $("#p-url").value.trim() || null,
    notes: $("#p-notes").value.trim() || null,
    priority: parseInt($("#p-priority").value, 10),
  };
  if (!payload.name) return alert("Name is required");
  await api("/api/projects", { method: "POST", body: JSON.stringify(payload) });
  ["p-name", "p-chain", "p-url", "p-notes"].forEach((id) => ($(`#${id}`).value = ""));
  await refreshAll();
});

$("#t-add").addEventListener("click", async () => {
  const payload = {
    project_id: parseInt($("#t-project").value, 10),
    title: $("#t-title").value.trim(),
    cadence: $("#t-cadence").value,
    wallet_id: $("#t-wallet").value ? parseInt($("#t-wallet").value, 10) : null,
  };
  if (!payload.project_id) return alert("Add a project first");
  if (!payload.title) return alert("Task title is required");
  await api("/api/tasks", { method: "POST", body: JSON.stringify(payload) });
  $("#t-title").value = "";
  await refreshAll();
});

$("#w-add").addEventListener("click", async () => {
  const payload = {
    label: $("#w-label").value.trim(),
    address: $("#w-address").value.trim(),
    chain: $("#w-chain").value.trim() || null,
    notes: $("#w-notes").value.trim() || null,
  };
  if (!payload.label || !payload.address) return alert("Label and address are required");
  try {
    await api("/api/wallets", { method: "POST", body: JSON.stringify(payload) });
  } catch (e) {
    return alert("Could not add wallet (duplicate address?)");
  }
  ["w-label", "w-address", "w-chain", "w-notes"].forEach((id) => ($(`#${id}`).value = ""));
  await refreshAll();
});

// ----- settings -----
$("#notify-test").addEventListener("click", async () => {
  const out = $("#notify-out");
  out.textContent = "Sending...";
  try {
    const res = await api("/api/notify/test", { method: "POST" });
    out.textContent = (res.sent ? "✓ Sent\n\n" : "(Telegram disabled — preview only)\n\n") + res.preview;
  } catch (e) {
    out.textContent = String(e);
  }
});

$("#reset-daily").addEventListener("click", async () => {
  if (!confirm("Reset all daily tasks to pending?")) return;
  const res = await api("/api/admin/reset-daily", { method: "POST" });
  alert(`Reset ${res.reset} task(s) to pending.`);
  await refreshAll();
});

$("#refresh-btn").addEventListener("click", () => refreshAll());

// ----- helpers -----
function escapeHtml(s) {
  if (s == null) return "";
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

async function refreshAll() {
  try {
    await Promise.all([loadDashboard(), loadProjects(), loadWallets()]);
  } catch (e) {
    console.error(e);
  }
}

refreshAll();
