"use strict";
const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const today = () => new Date().toISOString().slice(0, 10);
let health = {};
let currentMeeting = null;

async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json", "X-Action-Graph": "1" }, ...opts });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error?.message || data.detail?.[0]?.msg || data.detail || `HTTP ${res.status}`);
  return data;
}

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(t._h);
  t._h = setTimeout(() => t.classList.remove("show"), 3500);
}

/* ---------- tabs ---------- */
const loaders = { graph: loadGraph, memory: loadMemory, reminders: loadReminders, digest: loadDigest, score: loadScore };
const tabButtons = [...document.querySelectorAll(".tabs button")];
function selectTab(btn) {
  tabButtons.forEach((b) => b.setAttribute("aria-selected", b === btn));
  document.querySelectorAll(".tab").forEach((s) => s.classList.toggle("active", s.id === `tab-${btn.dataset.tab}`));
  loaders[btn.dataset.tab]?.();
}
tabButtons.forEach((b, i) => {
  b.addEventListener("click", () => selectTab(b));
  b.addEventListener("keydown", (e) => {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
    if (step) { const next = tabButtons[(i + step + tabButtons.length) % tabButtons.length]; next.focus(); selectTab(next); }
  });
});

/* ---------- status ---------- */
async function loadStatus() {
  health = await api("/api/health");
  const s = await api("/api/stats");
  $("#status").innerHTML = `
    <span class="pill ${health.llm ? "on" : "off"}">${health.llm ? "Claude extraction on" : "Rules-only extraction"}</span>
    <span class="pill">Tracker: <a href="https://github.com/${esc(health.repo)}/issues" target="_blank" rel="noopener">${esc(health.repo)}</a></span>
    <span class="pill">${s.meetings} meetings · ${s.conflicts_flagged} conflicts caught</span>`;
}

/* ---------- capture ---------- */
const form = $("#captureForm");
form.date.value = today();
api("/api/samples").then((samples) => {
  const box = $("#samples");
  const sampleDates = ["2026-10-24", "2026-10-31"];
  samples.forEach((s, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = `Load sample: ${s.name.replace(/^\d+_/, "").replace(/_/g, " ")}`;
    b.onclick = () => {
      form.transcript.value = s.text;
      form.title.value = b.textContent.replace("Load sample: ", "").replace(/^\w/, (c) => c.toUpperCase());
      form.date.value = sampleDates[i] || today();
      form.attendees.value = "Priya, Arjun, Meera, Ravi";
    };
    box.append(b);
  });
});

const STEPS = ["Clean speech", "Attribute speakers", "Extract decisions & actions", "Check memory for conflicts", "Awaiting your approval"];
function renderTrace(active, m) {
  const trace = $("#trace");
  trace.innerHTML = STEPS.map((label, i) => {
    let cls = i < active ? "done" : i === active ? "running" : "";
    let text = label;
    if (m) {
      const decisions = m.items.filter((x) => x.kind === "decision").length;
      const conflicts = m.items.filter((x) => x.conflict_with).length;
      const speakers = new Set(m.utterances.map((u) => u.speaker)).size;
      text = [`Cleaned ${m.utterances.length} utterances`, `${speakers} speakers`,
        `${decisions} decisions, ${m.items.length - decisions} actions · ${m.extractor}`,
        conflicts ? `${conflicts} conflict${conflicts > 1 ? "s" : ""} with memory` : "No conflicts with memory",
        "Awaiting your approval"][i];
      cls = i === 3 && conflicts ? "alert" : i < 4 ? "done" : "running";
    }
    return `<li class="${cls}">${esc(text)}</li>`;
  }).join("");
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("#runBtn");
  btn.disabled = true;
  let step = 0;
  renderTrace(step);
  const ticker = setInterval(() => renderTrace(Math.min(++step, 3)), 700);
  try {
    const m = await api("/api/meetings", {
      method: "POST",
      body: JSON.stringify({
        title: form.title.value, date: form.date.value, transcript: form.transcript.value,
        attendees: form.attendees.value.split(",").map((a) => a.trim()).filter(Boolean),
      }),
    });
    currentMeeting = m;
    renderTrace(4, m);
    renderMeeting(m);
    (m.notes || []).forEach(toast);
    loadStatus();
  } catch (err) {
    $("#trace").innerHTML = `<li class="alert">${esc(err.message)}</li>`;
  } finally {
    clearInterval(ticker);
    btn.disabled = false;
  }
});

function renderMeeting(m) {
  $("#cleanBox").hidden = false;
  $("#cleanText").innerHTML = m.utterances.map((u) => `<div class="utt"><b>${esc(u.speaker)}</b><span>${esc(u.text)}</span></div>`).join("");
  const q = $("#queue");
  q.innerHTML = m.items.length ? "" : `<p class="empty">No decisions or actions found in this meeting.</p>`;
  const order = (it) => (it.conflict_with ? 0 : it.kind === "decision" ? 1 : 2);
  [...m.items].sort((a, b) => order(a) - order(b)).forEach((it) => q.append(card(it)));
  updatePostbar();
}

function card(it) {
  const el = document.createElement("article");
  el.className = `card ${it.kind} status-${it.status}${it.conflict_with ? " has-conflict" : ""}`;
  el.dataset.id = it.id;
  const pending = it.status === "pending";
  const field = (name, label, type = "text") =>
    `<label>${label}<input name="${name}" type="${type}" value="${esc(it[name])}" ${pending ? "" : "disabled"}></label>`;
  el.innerHTML = `
    <div class="card-head">
      <span class="badge ${it.kind}">${it.kind}</span>
      <span class="badge state">${it.status}</span>
      ${it.tracker_url ? `<a class="link" href="${esc(it.tracker_url)}" target="_blank" rel="noopener">View issue ↗</a>` : ""}
    </div>
    ${it.conflict_with ? `<div class="conflict"><strong>⚠ Conflicts with an earlier decision</strong>${esc(it.conflict_reason)}
      ${pending ? "<br><small>Approving this supersedes the earlier decision in memory.</small>" : ""}</div>` : ""}
    <label>${it.kind === "decision" ? "Decision" : "Task"}<input name="text" value="${esc(it.text)}" ${pending ? "" : "disabled"}></label>
    <div class="fields">
      ${it.kind === "action" ? field("owner", "Owner") + field("deadline", "Deadline", "date") : field("subject", "About") + field("value", "Decided value")}
    </div>
    ${it.source_quote ? `<p class="quote">“${esc(it.source_quote)}” — ${esc(it.speaker || "unknown")}</p>` : ""}
    <div class="actions">${pending ? `<button class="approve">Approve</button><button class="reject">Reject</button>` : ""}
      ${it.status === "posted" || it.status === "approved" ? (it.kind === "action" ? `<button class="done">Mark done</button>` : "") : ""}</div>`;
  el.querySelector(".approve")?.addEventListener("click", () => decide(el, it, "approve"));
  el.querySelector(".reject")?.addEventListener("click", () => decide(el, it, "reject"));
  el.querySelector(".done")?.addEventListener("click", () => decide(el, it, "done"));
  return el;
}

async function decide(el, it, action) {
  const body = {};
  if (action === "approve") el.querySelectorAll("input").forEach((i) => { if (i.value) body[i.name] = i.value; });
  try {
    const updated = await api(`/api/items/${it.id}/${action}`, { method: "POST", body: JSON.stringify(body) });
    Object.assign(it, updated);
    el.replaceWith(card(it));
    if (action === "approve" && it.conflict_with) toast("Approved. The earlier decision is now marked superseded.");
    updatePostbar();
    loadStatus();
  } catch (err) { toast(err.message); }
}

function approvedIds() {
  return (currentMeeting?.items || []).filter((i) => i.status === "approved").map((i) => i.id);
}
function updatePostbar() {
  const n = approvedIds().length;
  $("#postbar").hidden = n === 0;
  $("#postCount").textContent = `${n} approved item${n === 1 ? "" : "s"} ready for the tracker`;
}

$("#postBtn").addEventListener("click", () => {
  const ids = approvedIds();
  const items = currentMeeting.items.filter((i) => ids.includes(i.id));
  $("#repoName").textContent = health.repo;
  $("#confirmList").innerHTML = items.map((i) => `<li><b>${esc(i.owner || "Decision")}</b>: ${esc(i.text)}${i.deadline ? ` <small>(due ${esc(i.deadline)})</small>` : ""}</li>`).join("");
  $("#confirmDlg").showModal();
});
$("#confirmDlg").addEventListener("close", async () => {
  if ($("#confirmDlg").returnValue !== "ok") return;
  const ids = approvedIds();
  try {
    const results = await api("/api/post", { method: "POST", body: JSON.stringify({ item_ids: ids, confirm: true }) });
    const ok = results.filter((r) => r.url).length;
    const failed = results.filter((r) => r.error);
    toast(failed.length ? `${ok} posted, ${failed.length} failed: ${failed[0].error}` : `Created ${ok} GitHub issue${ok === 1 ? "" : "s"}`);
    currentMeeting = await api(`/api/meetings/${currentMeeting.id}`);
    renderMeeting(currentMeeting);
    loadStatus();
  } catch (err) { toast(err.message); }
});

/* ---------- graph ---------- */
let cy;
async function loadGraph() {
  const g = await api("/api/graph");
  const css = getComputedStyle(document.documentElement);
  const v = (n) => css.getPropertyValue(n).trim();
  const elements = [
    ...g.nodes.map((n) => ({ data: { ...n }, classes: `${n.kind} ${n.status || ""}` })),
    ...g.edges.map((e, i) => ({ data: { id: `e${i}`, ...e }, classes: e.kind })),
  ];
  cy?.destroy();
  cy = cytoscape({
    container: $("#cy"), elements, wheelSensitivity: 0.2,
    layout: { name: "cose", animate: false, nodeRepulsion: 40000, idealEdgeLength: 140, nodeOverlap: 40, gravity: 0.15, padding: 40, randomize: false },
    style: [
      { selector: "node", style: { label: "data(label)", "font-size": 9, "text-wrap": "wrap", "text-max-width": 110, color: v("--ink"), "text-valign": "bottom", "text-margin-y": 4, width: 20, height: 20, "text-background-color": v("--card"), "text-background-opacity": 0.85, "text-background-padding": 2 } },
      { selector: ".meeting", style: { shape: "round-rectangle", "background-color": v("--meeting"), width: 30, height: 30, "font-weight": 600 } },
      { selector: ".person", style: { "background-color": v("--person"), width: 28, height: 28, "font-size": 12, "font-weight": 600 } },
      { selector: ".decision", style: { "background-color": v("--decision"), shape: "diamond" } },
      { selector: ".action", style: { "background-color": v("--action") } },
      { selector: ".pending", style: { "border-width": 2, "border-style": "dashed", "border-color": v("--muted"), "background-opacity": 0.5 } },
      { selector: ".superseded", style: { "background-color": v("--line"), "border-width": 1, "border-style": "dashed", "border-color": v("--muted"), color: v("--muted") } },
      { selector: "edge", style: { width: 1.2, "line-color": v("--line"), "curve-style": "bezier", "target-arrow-shape": "triangle", "target-arrow-color": v("--line"), "arrow-scale": 0.7 } },
      { selector: "edge.conflicts", style: { width: 2.5, "line-color": v("--conflict"), "target-arrow-color": v("--conflict"), "line-style": "dashed", label: "conflicts", "font-size": 9, color: v("--conflict") } },
    ],
  });
}

/* ---------- memory ---------- */
async function loadMemory() {
  const items = (await api("/api/items")).filter((i) => i.kind === "decision" && ["approved", "posted", "done", "superseded"].includes(i.status));
  const groups = {};
  items.forEach((i) => (groups[i.subject || i.text] ||= []).push(i));
  $("#memory").innerHTML = Object.keys(groups).length ? Object.entries(groups).map(([subject, list]) => `
    <div class="subject"><h3>${esc(subject)}</h3><ul class="timeline">
      ${list.map((i) => `<li class="${i.status}"><time>${esc(i.meeting_date)}</time><span>${esc(i.value || i.text)} <small>· ${esc(i.meeting_title)}${i.speaker ? ", " + esc(i.speaker) : ""}${i.status === "superseded" ? " · superseded" : ""}</small></span></li>`).join("")}
    </ul></div>`).join("") : `<p class="empty">No approved decisions yet. Approve decisions in a meeting to build memory.</p>`;
}

/* ---------- reminders ---------- */
async function loadReminders(list) {
  list = list || (await api("/api/reminders"));
  $("#reminders").innerHTML = list.length ? list.map((r) => `
    <li><span>${esc(r.message)}</span>
      ${r.posted_url ? `<a class="link" href="${esc(r.posted_url)}" target="_blank" rel="noopener">Posted ↗</a>`
        : r.tracker_url ? `<button data-rem="${r.id}">Post to issue</button>` : `<small>Not in tracker yet</small>`}</li>`).join("")
    : `<li><span>No reminders. Check deadlines with a date near an approved action's deadline.</span></li>`;
  document.querySelectorAll("[data-rem]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("Post this reminder as a comment on the GitHub issue?")) return;
    try { await api(`/api/reminders/${b.dataset.rem}/post`, { method: "POST" }); toast("Reminder posted"); loadReminders(); }
    catch (err) { toast(err.message); }
  }));
}
$("#remForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  const params = new URLSearchParams({ window_hours: f.window.value });
  if (f.now.value) params.set("now", f.now.value);
  try { loadReminders(await api(`/api/reminders/run?${params}`, { method: "POST" })); } catch (err) { toast(err.message); }
});

/* ---------- digest ---------- */
function mondayOf(d) { const x = new Date(d); x.setDate(x.getDate() - ((x.getDay() + 6) % 7)); return x.toISOString().slice(0, 10); }
$("#digestForm").week.value = mondayOf(new Date());
$("#digestForm").addEventListener("submit", (e) => { e.preventDefault(); loadDigest(); });
function digestMarkdown(p, week) {
  const sec = (title, list, fmt) => list.length ? `\n**${title}**\n${list.map((i) => `- ${fmt(i)}`).join("\n")}\n` : "";
  const act = (i) => `${i.text}${i.deadline ? ` (due ${i.deadline})` : ""}${i.tracker_url ? ` ${i.tracker_url}` : ""}`;
  return `## Weekly digest for ${p.person} (week of ${week})\n` + sec("Overdue", p.overdue, act) + sec("Due this week", p.due_this_week, act)
    + sec("Coming up", p.later, act) + sec("Done", p.done, act) + sec("Decisions you made", p.decisions, (i) => i.text);
}
async function loadDigest() {
  const week = $("#digestForm").week.value;
  const people = await api(`/api/digest?week_start=${week}`);
  const list = (title, items, bad) => items.length ? `<h4 class="${bad ? "bad" : ""}">${title}</h4><ul>${items.map((i) =>
    `<li>${esc(i.text)}${i.deadline ? ` <small>· ${esc(i.deadline)}</small>` : ""}</li>`).join("")}</ul>` : "";
  $("#digest").innerHTML = people.length ? people.map((p, idx) => `
    <article class="person-card"><h3>${esc(p.person)} <button data-copy="${idx}">Copy</button></h3>
      ${list("Overdue", p.overdue, true)}${list("Due this week", p.due_this_week)}${list("Coming up", p.later)}
      ${list("Done", p.done)}${list("Decisions made", p.decisions)}
    </article>`).join("") : `<p class="empty">Nothing approved yet for anyone.</p>`;
  document.querySelectorAll("[data-copy]").forEach((b) => b.addEventListener("click", async () => {
    await navigator.clipboard.writeText(digestMarkdown(people[b.dataset.copy], week));
    toast("Digest copied as Markdown");
  }));
}

/* ---------- scorecard ---------- */
async function loadScore() {
  const s = await api("/api/stats");
  const rate = s.approved ? Math.round((100 * s.approved_without_edits) / s.approved) : 0;
  const tile = (n, label, hero) => `<div class="stat${hero ? " hero" : ""}"><b>${n}</b><span>${label}</span></div>`;
  $("#score").innerHTML = tile(`${rate}%`, "approved without any human edit", true) + tile(s.items_extracted, "items extracted")
    + tile(s.conflicts_flagged, "conflicts flagged") + tile(s.superseded, "decisions superseded") + tile(s.approved, "approved")
    + tile(s.rejected, "rejected") + tile(s.posted, "posted to GitHub") + tile(s.meetings, "meetings ingested");
  const evals = await api("/api/eval");
  $("#score").innerHTML += evals.map((e) => tile(`${Math.round(e.precision * 100)}% / ${Math.round(e.recall * 100)}%`,
    `precision / recall · ${e.set === "holdout" ? "held-out set (never tuned on)" : "dev set (rules tuned on it)"} · ${esc(e.extractor)}`)).join("");
}

loadStatus();
