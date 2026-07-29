/* SCARA Web Control - logika GUI. */

const $ = id => document.getElementById(id);
let robotStatus = {};
let points = [];
let editorSteps = [];
let connected = false;

// ------------------------------------------------------------------ HTTP
async function api(path, method = "GET", body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body !== null) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = typeof j.detail === "object"
        ? `${j.detail.code}: ${j.detail.message}` : (j.detail || detail);
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

function toast(msg, ok = false) {
  const el = $("toast");
  el.textContent = msg;
  el.className = ok ? "ok" : "";
  el.style.display = "block";
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.style.display = "none"; }, 3500);
}

async function guarded(fn) {
  try { await fn(); } catch (e) { toast(e.message); }
}

// ------------------------------------------------------------- websocket
function connectWS() {
  const ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onmessage = ev => handleEvent(JSON.parse(ev.data));
  ws.onclose = () => setTimeout(connectWS, 1500);
}

function handleEvent(ev) {
  if (ev.type === "status") {
    robotStatus = ev.data;
    updateReadouts();
    VIZ.draw(robotStatus, points);
  } else if (ev.type === "log") {
    logLine(ev.direction, ev.line);
  } else if (ev.type === "connection") {
    connected = ev.connected;
    updateConnBadge();
    if (!ev.connected && ev.detail) toast(ev.detail);
  } else if (ev.type === "points_changed") {
    loadPoints();
  } else if (ev.type === "programs_changed") {
    loadPrograms();
  } else if (ev.type === "program") {
    updateProgramStatus(ev);
  } else if (ev.type === "alarm") {
    toast(ev.detail);
  } else if (ev.type === "linear") {
    if (ev.state === "error") toast("Ruch liniowy: " + ev.detail);
  }
}

// ------------------------------------------------------------------- UI
function updateConnBadge() {
  $("badge-conn").textContent = connected ? "POŁĄCZONY" : "ROZŁĄCZONY";
  $("badge-conn").className = "badge" + (connected ? " on" : "");
  $("btn-connect").textContent = connected ? "Rozłącz" : "Połącz";
  $("btn-connect").className = connected ? "" : "primary";
}

function fmt(v, digits = 1) {
  return v === undefined ? "—" : Number(v).toFixed(digits);
}

function updateReadouts() {
  const s = robotStatus;
  $("val-j1").textContent = fmt(s.j1) + "°";
  $("val-j2").textContent = fmt(s.j2) + "°";
  $("val-z").textContent = fmt(s.z) + " mm";
  $("val-tool").textContent = fmt(s.tool) + "°";
  $("val-x").textContent = fmt(s.x) + " mm";
  $("val-y").textContent = fmt(s.y) + " mm";
  $("ro-x").textContent = fmt(s.x, 2); $("ro-y").textContent = fmt(s.y, 2);
  $("ro-z").textContent = fmt(s.z, 2); $("ro-j1").textContent = fmt(s.j1, 2);
  $("ro-j2").textContent = fmt(s.j2, 2); $("ro-tool").textContent = fmt(s.tool, 2);
  $("badge-homed").textContent = "HOMED: " + (s.homed ? "TAK" : "NIE");
  $("badge-homed").className = "badge" + (s.homed ? " on" : " warn");
  $("badge-state").textContent = s.state || "—";
  $("badge-state").className = "badge" + (s.state === "MOVING" ? " warn" : "");
  $("badge-grip").textContent = "GRIPPER: " + (s.grip ? "ZAMKNIĘTY" : "OTWARTY");
  if (s.speed !== undefined && document.activeElement !== $("speed-slider")) {
    $("speed-slider").value = s.speed;
    $("speed-value").textContent = s.speed + "%";
  }
}

function logLine(direction, line) {
  const log = $("console-log");
  const div = document.createElement("div");
  div.className = line.startsWith("ERR") ? "err" : direction;
  div.textContent = (direction === "tx" ? "> " : "< ") + line;
  log.appendChild(div);
  while (log.children.length > 400) log.removeChild(log.firstChild);
  log.scrollTop = log.scrollHeight;
}

// ------------------------------------------------------------ polaczenie
async function refreshPorts() {
  const ports = await api("/api/ports");
  const sel = $("port-select");
  sel.innerHTML = "";
  ports.forEach(p => {
    const o = document.createElement("option");
    o.value = p.device;
    o.textContent = `${p.device} — ${p.description}`;
    sel.appendChild(o);
  });
}

$("btn-refresh-ports").onclick = () => guarded(refreshPorts);
$("btn-connect").onclick = () => guarded(async () => {
  if (connected) { await api("/api/disconnect", "POST"); }
  else {
    await api("/api/connect", "POST", { port: $("port-select").value });
    VIZ.clearTrail();
  }
});

// ------------------------------------------------------------------- jog
let jointStep = 1, cartStep = 5;
document.querySelectorAll("#joint-steps button").forEach(b => b.onclick = () => {
  jointStep = parseFloat(b.dataset.step);
  document.querySelectorAll("#joint-steps button").forEach(x => x.classList.remove("sel"));
  b.classList.add("sel");
});
document.querySelectorAll("#cart-steps button").forEach(b => b.onclick = () => {
  cartStep = parseFloat(b.dataset.step);
  document.querySelectorAll("#cart-steps button").forEach(x => x.classList.remove("sel"));
  b.classList.add("sel");
});

// Jog osiowy jest WZGLEDNY (JOGR) - dziala takze przed homingiem,
// co umozliwia reczne dojechanie do pozycji krancowych (homing reczny).
document.querySelectorAll("[data-jog]").forEach(b => b.onclick = () => guarded(async () => {
  const axis = b.dataset.jog;
  const delta = jointStep * parseFloat(b.dataset.dir);
  await api("/api/jog_relative", "POST", { axis, delta });
}));

document.querySelectorAll("[data-cart]").forEach(b => b.onclick = () => guarded(async () => {
  if (robotStatus.x === undefined) throw new Error("brak pozycji robota");
  const dx = b.dataset.cart === "x" ? cartStep * parseFloat(b.dataset.dir) : 0;
  const dy = b.dataset.cart === "y" ? cartStep * parseFloat(b.dataset.dir) : 0;
  await api("/api/move", "POST", {
    x: robotStatus.x + dx, y: robotStatus.y + dy,
    elbow_up: $("elbow-up").checked, linear: false,
  });
}));

$("btn-home").onclick = () => guarded(async () => {
  toast("Homing w toku…", true);
  await api("/api/home", "POST", {});
  toast("Homing zakończony", true);
  VIZ.clearTrail();
});
$("btn-stop").onclick = () => guarded(() => api("/api/stop", "POST"));
$("btn-estop").onclick = () => guarded(async () => {
  await api("/api/estop", "POST");
  toast("E-STOP: sterowniki odłączone, wymagany HOME");
});
$("btn-grip-open").onclick = () => guarded(() => api("/api/grip", "POST", { closed: false }));
$("btn-grip-close").onclick = () => guarded(() => api("/api/grip", "POST", { closed: true }));

$("btn-sethome-all").onclick = () => guarded(async () => {
  await api("/api/sethome", "POST", {});
  toast("HOME ustawiony ręcznie (wszystkie osie)", true);
  VIZ.clearTrail();
});
document.querySelectorAll("[data-sethome]").forEach(b => b.onclick = () => guarded(async () => {
  await api("/api/sethome", "POST", { axis: b.dataset.sethome });
  toast(`HOME osi ${b.dataset.sethome} ustawiony ręcznie`, true);
}));

$("speed-slider").oninput = () => {
  $("speed-value").textContent = $("speed-slider").value + "%";
};
$("speed-slider").onchange = () => guarded(() =>
  api("/api/speed", "POST", { percent: parseInt($("speed-slider").value) }));

// ---------------------------------------------------------------- punkty
async function loadPoints() {
  points = await api("/api/points");
  const list = $("points-list");
  list.innerHTML = "";
  points.forEach(p => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="grow"><b>${p.name}</b>
      <small>(${p.x.toFixed(1)}, ${p.y.toFixed(1)}, Z${p.z.toFixed(1)})</small></span>`;
    const go = document.createElement("button");
    go.textContent = "Go";
    go.title = "Ruch joint do punktu";
    go.onclick = () => guarded(() => api(`/api/points/${encodeURIComponent(p.name)}/goto`, "POST"));
    const gol = document.createElement("button");
    gol.textContent = "Go⎯";
    gol.title = "Ruch liniowy do punktu";
    gol.onclick = () => guarded(() => api(`/api/points/${encodeURIComponent(p.name)}/goto?linear=true`, "POST"));
    const del = document.createElement("button");
    del.textContent = "✕";
    del.onclick = () => guarded(() => api(`/api/points/${encodeURIComponent(p.name)}`, "DELETE"));
    li.append(go, gol, del);
    list.appendChild(li);
  });
  updateStepPointSelect();
}

$("btn-teach").onclick = () => guarded(async () => {
  const name = $("teach-name").value.trim();
  if (!name) throw new Error("podaj nazwę punktu");
  await api(`/api/points/teach/${encodeURIComponent(name)}`, "POST");
  $("teach-name").value = "";
  toast(`Punkt "${name}" zapisany`, true);
});

// -------------------------------------------------------------- programy
const STEP_LABELS = {
  move_joint: p => `Ruch do "${p.point}" (joint)`,
  move_linear: p => `Ruch liniowy do "${p.point}"`,
  move_z: p => `Z do ${p.value} mm`,
  tool: p => `TOOL do ${p.value}°`,
  grip: p => p.value ? "Gripper: zamknij" : "Gripper: otwórz",
  wait: p => `Czekaj ${p.value} s`,
};

function updateStepPointSelect() {
  const sel = $("step-point");
  sel.innerHTML = "";
  points.forEach(p => {
    const o = document.createElement("option");
    o.value = p.name; o.textContent = p.name;
    sel.appendChild(o);
  });
}

$("step-type").onchange = () => {
  const t = $("step-type").value;
  $("step-point").style.display = (t === "move_joint" || t === "move_linear") ? "" : "none";
  $("step-value").style.display = (t === "move_z" || t === "tool" || t === "wait") ? "" : "none";
};

$("btn-add-step").onclick = () => {
  let t = $("step-type").value;
  const step = { type: t, point: null, value: null };
  if (t === "grip_close") { step.type = "grip"; step.value = 1; }
  else if (t === "grip_open") { step.type = "grip"; step.value = 0; }
  else if (t === "move_joint" || t === "move_linear") {
    step.point = $("step-point").value;
    if (!step.point) { toast("najpierw zapisz jakiś punkt (Teach)"); return; }
  } else {
    step.value = parseFloat($("step-value").value || "0");
  }
  editorSteps.push(step);
  renderSteps();
};

function renderSteps(activeIndex = null) {
  const list = $("steps-list");
  list.innerHTML = "";
  editorSteps.forEach((s, i) => {
    const li = document.createElement("li");
    if (i === activeIndex) li.classList.add("active-step");
    li.innerHTML = `<span class="grow">${i + 1}. ${STEP_LABELS[s.type](s)}</span>`;
    const up = document.createElement("button");
    up.textContent = "↑";
    up.onclick = () => {
      if (i > 0) { [editorSteps[i - 1], editorSteps[i]] = [editorSteps[i], editorSteps[i - 1]]; renderSteps(); }
    };
    const down = document.createElement("button");
    down.textContent = "↓";
    down.onclick = () => {
      if (i < editorSteps.length - 1) { [editorSteps[i + 1], editorSteps[i]] = [editorSteps[i], editorSteps[i + 1]]; renderSteps(); }
    };
    const del = document.createElement("button");
    del.textContent = "✕";
    del.onclick = () => { editorSteps.splice(i, 1); renderSteps(); };
    li.append(up, down, del);
    list.appendChild(li);
  });
}

$("btn-save-prog").onclick = () => guarded(async () => {
  const name = $("prog-name").value.trim();
  if (!name) throw new Error("podaj nazwę programu");
  if (editorSteps.length === 0) throw new Error("program nie ma kroków");
  await api("/api/programs", "POST", {
    name, steps: editorSteps,
    repeat: parseInt($("prog-repeat").value || "1"),
  });
  toast(`Program "${name}" zapisany`, true);
});

async function loadPrograms() {
  const programs = await api("/api/programs");
  const sel = $("prog-select");
  const prev = sel.value;
  sel.innerHTML = "";
  programs.forEach(p => {
    const o = document.createElement("option");
    o.value = p.name;
    o.textContent = `${p.name} (${p.steps.length} kroków, x${p.repeat})`;
    sel.appendChild(o);
  });
  if (prev) sel.value = prev;
  window._programs = programs;
}

$("btn-load-prog").onclick = () => {
  const prog = (window._programs || []).find(p => p.name === $("prog-select").value);
  if (!prog) return;
  $("prog-name").value = prog.name;
  $("prog-repeat").value = prog.repeat;
  editorSteps = JSON.parse(JSON.stringify(prog.steps));
  renderSteps();
};

$("btn-del-prog").onclick = () => guarded(async () => {
  const name = $("prog-select").value;
  if (!name) return;
  await api(`/api/programs/${encodeURIComponent(name)}`, "DELETE");
});

$("btn-run").onclick = () => guarded(async () => {
  const name = $("prog-select").value;
  if (!name) throw new Error("wybierz program");
  await api(`/api/programs/${encodeURIComponent(name)}/run`, "POST");
});
$("btn-pause").onclick = () => guarded(() => api("/api/programs/pause", "POST"));
$("btn-resume").onclick = () => guarded(() => api("/api/programs/resume", "POST"));
$("btn-stop-prog").onclick = () => guarded(() => api("/api/programs/stop", "POST"));

function updateProgramStatus(ev) {
  const el = $("prog-status");
  const stepInfo = ev.step !== null && ev.step !== undefined ? `, krok ${ev.step + 1}` : "";
  const labels = {
    running: `▶ ${ev.program}: cykl ${ev.cycle}${stepInfo}`,
    paused: `⏸ ${ev.program}: pauza${stepInfo}`,
    finished: `✔ ${ev.program}: zakończony (${ev.cycle} cykli)`,
    stopped: `■ ${ev.program}: zatrzymany`,
    error: `✖ ${ev.program}: BŁĄD — ${ev.detail}`,
  };
  el.textContent = labels[ev.state] || "";
  el.style.color = ev.state === "error" ? "var(--err)"
    : ev.state === "finished" ? "var(--ok)" : "var(--muted)";
  // Podswietlenie kroku w edytorze, jesli edytowany program == uruchomiony.
  if ($("prog-name").value === ev.program && ev.state === "running") {
    renderSteps(ev.step);
  }
}

// ----------------------------------------------------------------- start
$("btn-send-raw").onclick = () => guarded(async () => {
  const cmd = $("raw-cmd").value.trim();
  if (!cmd) return;
  await api("/api/command", "POST", { command: cmd });
  $("raw-cmd").value = "";
});
$("raw-cmd").addEventListener("keydown", e => {
  if (e.key === "Enter") $("btn-send-raw").click();
});

(async function init() {
  connectWS();
  await guarded(refreshPorts);
  await guarded(loadPoints);
  await guarded(loadPrograms);
  $("step-type").onchange();
  const st = await api("/api/status");
  connected = st.connected;
  robotStatus = st.robot || {};
  updateConnBadge();
  updateReadouts();
  VIZ.draw(robotStatus, points);
})();
