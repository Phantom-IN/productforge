// ProductForge observe-mode control panel: polls /api/status, sends pause · resume · stop · label.
"use strict";

const token = new URLSearchParams(location.search).get("t") || "";
const $ = (id) => document.getElementById(id);
const COUNTS = [
  ["events", "events"], ["screens", "screens"], ["requests", "API calls"],
  ["ws_frames", "realtime msgs"], ["shots", "screenshots"], ["dropped", "not recorded"],
];
const STATES = {
  starting: "Starting…", recording: "Recording", paused: "Paused — nothing is captured",
  stopping: "Stopping…", stopped: "Stopped — you can close this window",
};

async function api(path, body) {
  const init = { headers: { "X-PF-Token": token } };
  if (body !== undefined) {
    init.method = "POST";
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  const res = await fetch(path, init);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

function elapsed(seconds) {
  const s = Math.max(0, Math.floor(seconds || 0));
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}

function render(st) {
  const card = $("status-card");
  card.className = `card ${st.status}`;
  $("state").textContent = STATES[st.status] || st.status;
  $("elapsed").textContent = st.elapsed_s != null ? elapsed(st.elapsed_s) : "";
  const live = st.status === "recording" || st.status === "paused";
  $("pause").disabled = st.status !== "recording";
  $("resume").disabled = st.status !== "paused";
  $("stop").disabled = !live;
  $("set-label").disabled = !live;
  $("current-label").textContent = st.label ? `Current step: ${st.label}` : "No step named yet.";
  const counts = st.counts || {};
  $("counts").replaceChildren(...COUNTS.map(([key, text]) => {
    const el = document.createElement("div");
    el.className = "count";
    const b = document.createElement("b");
    b.textContent = counts[key] ?? 0;
    const span = document.createElement("span");
    span.textContent = text;
    el.append(b, span);
    return el;
  }));
}

async function poll() {
  try {
    const st = await api("/api/status");
    render(st);
    $("error").textContent = "";
    if (st.status === "stopped") return;
  } catch (err) {
    $("error").textContent = "The recorder is not answering. It may have stopped.";
  }
  setTimeout(poll, 1000);
}

async function send(name, body) {
  try {
    await api(`/api/${name}`, body ?? {});
  } catch (err) {
    $("error").textContent = `Could not ${name}: ${err.message}`;
  }
}

$("pause").addEventListener("click", () => send("pause"));
$("resume").addEventListener("click", () => send("resume"));
$("stop").addEventListener("click", () => {
  if (confirm("Stop this session? The browser window will close.")) send("stop");
});
function setLabel() {
  const value = $("label-input").value.trim();
  if (!value) return;
  send("label", { label: value });
  $("label-input").value = "";
}
$("set-label").addEventListener("click", setLabel);
$("label-input").addEventListener("keydown", (ev) => { if (ev.key === "Enter") setLabel(); });

poll();
