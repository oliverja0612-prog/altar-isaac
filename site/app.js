// Altar site: tabs, latest-release download, mod library, submissions and the admin board.
// Everything is static: mods come from registry/index.json (built on deploy), the rest from
// GitHub's public API.
const REPO = "oliverja0612-prog/altar-isaac";
const API = `https://api.github.com/repos/${REPO}`;
const $ = (s, el = document) => el.querySelector(s);

const FEATURES = [
  ["🎛️", "In-game menu", "Press F2 for a full menu: items, hearts, warps, bosses, characters, curses."],
  ["⌨️", "Command console", "F4 opens a terminal with autocomplete, history and ; chaining."],
  ["✨", "40 new items", "Animated items with real VFX, plus 14 combos that break the game."],
  ["🌑", "OBLIVION", "A secret final boss with a story, four forms and a fight in deep space."],
  ["📦", "Mod Manager", "Enable, disable, profiles, conflict checker, one-click Play."],
  ["🧲", "Mod library", "Browse approved mods and install in one click. They auto-update."],
  ["🛡️", "Safe mode", "Runs played with mods don't touch your real save files."],
  ["🔄", "Auto-updates", "Altar keeps itself up to date from GitHub releases."],
];

// ---------- paper helpers ----------
const rnd = (a, b) => a + Math.random() * (b - a);
function torn(el) {
  // a jagged top and bottom edge, different on every scrap
  const pts = [];
  const n = 14;
  for (let i = 0; i <= n; i++) pts.push(`${(i / n) * 100}% ${rnd(0, 2.2).toFixed(2)}%`);
  pts.push(`${rnd(99.2, 100)}% 50%`);
  for (let i = n; i >= 0; i--) pts.push(`${(i / n) * 100}% ${(100 - rnd(0, 2.2)).toFixed(2)}%`);
  pts.push(`${rnd(0, .8)}% 50%`);
  el.style.setProperty("--torn", `polygon(${pts.join(",")})`);
}
function scrap(html, { cls = "", deco = "pin", i = 0, tag = "div" } = {}) {
  const wrap = document.createElement(tag);
  wrap.className = `scrap-wrap drop ${cls}`;
  wrap.style.setProperty("--i", i);
  wrap.style.setProperty("--rot", `${rnd(-1.8, 1.8).toFixed(2)}deg`);
  const inner = document.createElement("div");
  inner.className = "scrap" + (Math.random() < .4 ? " note" : "");
  inner.innerHTML = html;
  torn(inner);
  wrap.appendChild(inner);
  if (deco) {
    const d = document.createElement("span");
    d.className = deco;
    if (deco === "tape") d.style.transform = `rotate(${rnd(-7, 7).toFixed(1)}deg)`;
    else d.style.left = `${rnd(30, 70).toFixed(0)}%`;
    wrap.appendChild(d);
  }
  return wrap;
}
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const mb = (b) => (b / 1e6).toFixed(b < 1e7 ? 1 : 0) + " MB";
const ago = (iso) => {
  const s = (Date.now() - new Date(iso)) / 1000;
  if (s < 3600) return `${Math.max(1, Math.round(s / 60))} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} days ago`;
};
async function getJSON(url) {
  const r = await fetch(url, { headers: { Accept: "application/vnd.github+json" } });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

// ---------- tabs ----------
const loaded = {};
function show() {
  const tab = (location.hash || "#home").slice(1);
  const page = document.getElementById(tab) ? tab : "home";
  document.querySelectorAll(".page").forEach((p) => (p.hidden = p.id !== page));
  document.querySelectorAll(".tabs a").forEach((a) => a.classList.toggle("on", a.dataset.tab === page));
  const fresh = document.getElementById(page);
  fresh.style.animation = "none"; void fresh.offsetWidth; fresh.style.animation = "";
  if (!loaded[page]) { loaded[page] = true; ({ mods: loadMods, submit: loadSubs, admin: loadAdmin }[page] || (() => {}))(); }
}
addEventListener("hashchange", () => { show(); scrollTo({ top: 0, behavior: "smooth" }); });

// ---------- home ----------
function renderFeatures() {
  const box = $("#features");
  FEATURES.forEach(([e, t, d], i) => {
    const s = scrap(`<span class="emoji">${e}</span><h3>${t}</h3><p>${d}</p>`, { cls: "feature card", deco: i % 2 ? "tape" : "pin", i });
    box.appendChild(s);
  });
}
async function loadRelease() {
  try {
    const rel = await getJSON(`${API}/releases/latest`);
    const exe = rel.assets.find((a) => /\.exe$/i.test(a.name));
    if (exe) {
      $("#dl").href = exe.browser_download_url;
      $("#dl-label").textContent = `Download Altar ${rel.tag_name}`;
      $("#dl-meta").textContent = `${exe.name} · ${mb(exe.size)} · Windows`;
    }
  } catch { /* the button already points at the releases page */ }
}

// ---------- mods ----------
let MODS = [], INDEX = null;
async function getIndex() {
  if (!INDEX) INDEX = await fetch("registry/index.json", { cache: "no-cache" }).then((r) => r.json());
  return INDEX;
}
async function loadMods() {
  const grid = $("#mod-grid");
  grid.innerHTML = '<div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>';
  try { MODS = (await getIndex()).mods; } catch { MODS = []; }
  renderMods("");
  $("#q").addEventListener("input", (e) => renderMods(e.target.value));
}
function renderMods(q) {
  const grid = $("#mod-grid");
  grid.innerHTML = "";
  q = q.trim().toLowerCase();
  const list = MODS.filter((m) => !q || `${m.name} ${m.author} ${m.description}`.toLowerCase().includes(q));
  if (!list.length) {
    const s = scrap(MODS.length
      ? `<h3>Nothing found</h3><p>No mod matches "${esc(q)}".</p>`
      : `<h3>The shelf is empty</h3><p>No mods yet. Be the first!</p><a class="btn" href="#submit">Upload a mod</a>`,
      { cls: "empty", deco: "tape" });
    grid.appendChild(s);
    return;
  }
  list.forEach((m, i) => {
    const s = scrap(`
      <h3>${esc(m.name)}</h3>
      <div class="by">v${esc(m.version)} · by ${esc(m.author)}</div>
      <p>${esc(m.description || "No description.")}</p>
      <div class="tags">
        <span class="tag ok">✓ checked</span>
        <span class="tag">${mb(m.size)}</span>
        ${m.warnings ? `<span class="tag warn">${m.warnings} note${m.warnings > 1 ? "s" : ""}</span>` : ""}
      </div>`, { cls: "mod card", deco: i % 3 ? "pin" : "tape", i });
    s.tabIndex = 0;
    s.onclick = () => openMod(m);
    s.onkeydown = (e) => { if (e.key === "Enter") openMod(m); };
    grid.appendChild(s);
  });
}
function openMod(m) {
  const src = `https://github.com/${m.repo}/tree/${m.commit}${m.path ? "/" + m.path : ""}`;
  $("#m-body").innerHTML = `
    <h3 id="m-title" style="font-size:34px">${esc(m.name)}</h3>
    <div class="tags"><span class="tag blood">v${esc(m.version)}</span><span class="tag ok">✓ safety check passed</span>
    ${m.warnings ? `<span class="tag warn">${m.warnings} admin note${m.warnings > 1 ? "s" : ""}</span>` : ""}</div>
    <p>${esc(m.description || "No description.")}</p>
    <dl class="kv">
      <dt>Author</dt><dd><a href="https://github.com/${esc(m.author)}" target="_blank" rel="noopener">${esc(m.author)}</a></dd>
      <dt>Folder</dt><dd><code>mods/${esc(m.folder)}</code></dd>
      <dt>Size</dt><dd>${mb(m.size)} download · ${m.files} files</dd>
      <dt>Commit</dt><dd><code>${esc(m.commit.slice(0, 12))}</code></dd>
      <dt>sha256</dt><dd><code>${esc(m.sha256)}</code></dd>
      <dt>Added</dt><dd>${new Date(m.submitted).toLocaleDateString()} (<a href="https://github.com/${REPO}/issues/${m.issue}" target="_blank" rel="noopener">#${m.issue}</a>)</dd>
    </dl>
    <p class="small"><b>Install:</b> open the Altar app → <b>Browse</b> → <b>${esc(m.name)}</b> → Install. It updates by itself.</p>
    <div class="cta"><a class="btn" href="${src}" target="_blank" rel="noopener">View source</a>
    <a class="btn ghost" href="#home" data-close>Get the Altar app</a></div>`;
  openModal();
}
function openModal() {
  const m = $("#modal");
  m.hidden = false;
  torn($(".modal-card", m));
  $(".x", m).focus();
}
function closeModal() { $("#modal").hidden = true; }
document.addEventListener("click", (e) => { if (e.target.closest("[data-close]")) closeModal(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

// ---------- submissions ----------
function statusOf(issue) {
  const labels = issue.labels.map((l) => l.name);
  if (issue.state === "closed") return labels.includes("rejected") ? ["rejected", "blood"] : ["published", "ok"];
  if (labels.includes("needs-fixes")) return ["needs fixes", "blood"];
  if (labels.includes("safety-passed")) return ["waiting for admins", "warn"];
  return ["checking…", ""];
}
async function loadSubs() {
  const box = $("#subs");
  box.innerHTML = '<div class="skeleton" style="height:60px"></div>';
  try {
    const issues = await getJSON(`${API}/issues?labels=mod-submission&state=all&per_page=15`);
    box.innerHTML = "";
    if (!issues.length) { box.appendChild(scrap("<p>No submissions yet.</p>", { deco: "tape" })); return; }
    issues.forEach((it, i) => {
      const [st, cls] = statusOf(it);
      const s = scrap(`<div class="row"><div class="grow"><div class="t">${esc(it.title.replace(/^Mod:\s*/, ""))}</div>
        <div class="s">#${it.number} · by ${esc(it.user.login)} · ${ago(it.created_at)}</div></div>
        <span class="tag ${cls}">${st}</span>
        <a class="btn ghost" href="${it.html_url}" target="_blank" rel="noopener">Open</a></div>`, { deco: null, i });
      s.firstChild.style.padding = "4px";
      box.appendChild(s);
    });
  } catch {
    box.innerHTML = "";
    box.appendChild(scrap(`<p>Couldn't reach GitHub right now. <a href="https://github.com/${REPO}/issues?q=label%3Amod-submission" target="_blank" rel="noopener">See them on GitHub</a>.</p>`, { deco: "tape" }));
  }
}

// ---------- admins ----------
async function loadAdmin() {
  const team = $("#team");
  let idx = { admins: [{ github: "oliverja0612-prog", role: "owner" }], roles: {}, approvals_required: 1 };
  try { idx = await getIndex(); } catch { /* fallback above */ }
  idx.admins.forEach((a, i) => {
    team.appendChild(scrap(`<img src="https://github.com/${esc(a.github)}.png?size=168" alt="" loading="lazy">
      <h3>${esc(a.github)}</h3><span class="tag blood role">${esc(a.role)}</span>
      <p class="small muted">${esc((idx.roles || {})[a.role] || "")}</p>`, { cls: "admin card", deco: "pin", i }));
  });
  if (idx.admins.length < 2) {
    team.appendChild(scrap(`<div style="font-size:60px;line-height:1">?</div><h3>Open seat</h3>
      <span class="tag role">reviewer</span><p class="small muted">A second admin joins soon. Then every mod needs two approvals.</p>`,
      { cls: "admin card open", deco: "tape", i: idx.admins.length }));
  }
  const need = idx.approvals_required || 1;
  $("#need").textContent = `A mod goes live after ${need} admin approval${need > 1 ? "s" : ""}.`;

  const box = $("#pending");
  box.innerHTML = '<div class="skeleton" style="height:60px"></div>';
  try {
    const prs = (await getJSON(`${API}/pulls?state=open&per_page=30`)).filter((p) => p.head.ref.startsWith("submission/"));
    box.innerHTML = "";
    if (!prs.length) { box.appendChild(scrap("<p>Nothing waiting. 🎉</p>", { deco: "tape" })); return; }
    prs.forEach((p, i) => {
      const s = scrap(`<div class="row"><div class="grow"><div class="t">${esc(p.title.replace(/^Mod:\s*/, ""))}</div>
        <div class="s">opened ${ago(p.created_at)} · from issue #${esc(p.head.ref.split("/")[1])}</div></div>
        <span class="tag warn">needs review</span>
        <a class="btn" style="font-size:19px;padding:6px 14px 8px" href="${p.html_url}/files" target="_blank" rel="noopener">Review</a></div>`, { deco: null, i });
      s.firstChild.style.padding = "4px";
      box.appendChild(s);
    });
  } catch {
    box.innerHTML = "";
    box.appendChild(scrap(`<p><a href="https://github.com/${REPO}/pulls" target="_blank" rel="noopener">Open reviews on GitHub</a></p>`, { deco: "tape" }));
  }
}

// ---------- start ----------
document.querySelectorAll(".page .scrap").forEach(torn);
renderFeatures();
loadRelease();
show();
