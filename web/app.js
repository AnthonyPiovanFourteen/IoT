(() => {
  "use strict";
  const C = window.APP_CONFIG;
  const $ = (id) => document.getElementById(id);
  const qs = `device_id=${encodeURIComponent(C.DEVICE_ID)}&grandeza=${encodeURIComponent(C.GRANDEZA)}`;
  const STALE_MS = C.INTERVALO_COLETA_S * C.STALE_FATOR * 1000;
  const fmt = (n, d = 1) => Number(n).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });
  const hhmmss = (iso) => new Date(iso).toLocaleTimeString("pt-BR");

  // geometria da cena (coincide com o SVG do index.html)
  const Y_BOTTOM = 340, Y_TOP = 216, Y_PELLET_START = 122;
  const clamp01 = (x) => Math.min(1, Math.max(0, x));
  const levelY = (g) => Y_BOTTOM - clamp01(g / C.CAPACIDADE_G) * (Y_BOTTOM - Y_TOP);

  const S = { latest: null, hist: [], online: true, pourUntil: 0, prevId: null, prevValor: null };

  /* ---------- tema ---------- */
  const root = document.documentElement;
  try { const t = localStorage.getItem("tema"); if (t) root.setAttribute("data-theme", t); } catch (_) { /* sem storage */ }
  $("theme").addEventListener("click", () => {
    const dark = root.getAttribute("data-theme") === "dark" ||
      (!root.getAttribute("data-theme") && matchMedia("(prefers-color-scheme: dark)").matches);
    const novo = dark ? "light" : "dark";
    root.setAttribute("data-theme", novo);
    try { localStorage.setItem("tema", novo); } catch (_) { /* ignora */ }
    paintChartColors(); chart.update("none");
  });

  /* ---------- cena ---------- */
  const NS = "http://www.w3.org/2000/svg";
  const pellets = $("pellets");
  const fills = ["var(--kibble-1)", "var(--kibble-2)", "var(--kibble-3)"];
  [-12, 4, -4, 10, -8, 2, 8, -2, 12].forEach((dx, i) => {
    const c = document.createElementNS(NS, "circle");
    c.setAttribute("class", "pellet");
    c.setAttribute("cx", 200 + dx); c.setAttribute("cy", Y_PELLET_START); c.setAttribute("r", 6);
    c.style.fill = fills[i % 3]; c.style.stroke = "rgba(0,0,0,.25)"; c.style.strokeWidth = ".8";
    c.style.animationDelay = (i * 0.12).toFixed(2) + "s";
    pellets.appendChild(c);
  });
  const yLim = levelY(C.LIMITE_ALERTA_G);
  $("limitLine").setAttribute("y1", yLim); $("limitLine").setAttribute("y2", yLim);
  $("limitTag").setAttribute("y", yLim + 4);
  $("legLimit").textContent = `limite ${C.LIMITE_ALERTA_G} g`;
  $("legCap").textContent = `${C.CAPACIDADE_G} g`;
  $("stLim").textContent = C.LIMITE_ALERTA_G;
  $("meterLimit").style.left = (C.LIMITE_ALERTA_G / C.CAPACIDADE_G * 100) + "%";

  /* ---------- gráfico ---------- */
  const cssv = (n) => getComputedStyle(root).getPropertyValue(n).trim();
  const chart = new Chart($("chart"), {
    type: "line",
    data: {
      labels: [],
      datasets: [
        { label: "Peso (g)", data: [], fill: true, tension: 0.3, borderWidth: 3, pointRadius: 3, pointHoverRadius: 6, pointBackgroundColor: [] },
        { label: `Limite de alerta (${C.LIMITE_ALERTA_G} g)`, data: [], borderDash: [7, 6], borderWidth: 2, pointRadius: 0, fill: false },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { labels: { usePointStyle: true, boxWidth: 8 } } },
      scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 7 } }, y: { beginAtZero: true, grace: "8%" } },
    },
  });
  function paintChartColors() {
    const ink = cssv("--muted");
    chart.data.datasets[0].borderColor = cssv("--chart-line");
    chart.data.datasets[0].backgroundColor = cssv("--chart-fill");
    chart.data.datasets[1].borderColor = cssv("--bad");
    chart.options.scales.x.ticks.color = ink; chart.options.scales.y.ticks.color = ink;
    chart.options.scales.y.grid.color = cssv("--chart-grid");
    chart.options.plugins.legend.labels.color = ink;
  }
  paintChartColors();

  /* ---------- linha do tempo ---------- */
  function buildEvents(h) {
    const ev = [];
    let run = null;
    const flush = () => {
      if (!run) return;
      const d = run.to - run.from;
      if (Math.abs(d) >= 60 && Math.abs(d) <= C.CAPACIDADE_G * 1.2) {
        ev.push(d > 0
          ? { t: run.t, ic: "📈", cls: "ok", txt: `Peso aumentou: +${fmt(d, 0)} g` }
          : { t: run.t, ic: "📉", cls: "", txt: `Peso diminuiu: −${fmt(-d, 0)} g` });
      }
      run = null;
    };
    for (let i = 1; i < h.length; i++) {
      const a = h[i - 1], b = h[i];
      const gap = (new Date(b.recebido_em) - new Date(a.recebido_em)) / 1000;
      if (gap * 1000 > STALE_MS) ev.push({ t: b.recebido_em, ic: "📡", cls: "warn", txt: `Transmissão retomada após ${Math.round(gap)} s` });
      if (!a.alerta && b.alerta) ev.push({ t: b.recebido_em, ic: "🚨", cls: "bad", txt: `Alerta: ração em ${fmt(b.valor, 0)} g (abaixo de ${C.LIMITE_ALERTA_G} g)` });
      else if (a.alerta && !b.alerta) ev.push({ t: b.recebido_em, ic: "✅", cls: "ok", txt: `Nível normalizado: ${fmt(b.valor, 0)} g` });
      const d = b.valor - a.valor, dir = d >= 10 ? 1 : d <= -10 ? -1 : 0;
      if (run && dir === run.dir) { run.to = b.valor; run.t = b.recebido_em; }
      else { flush(); if (dir) run = { dir, from: a.valor, to: b.valor, t: b.recebido_em }; }
    }
    flush();
    return ev.sort((x, y) => (x.t < y.t ? 1 : -1)).slice(0, 12);
  }
  function renderEvents(h) {
    const ul = $("events");
    const ev = buildEvents(h);
    if (!ev.length) { ul.innerHTML = '<li class="empty">Sem eventos no período.</li>'; return; }
    ul.innerHTML = "";
    ev.forEach((e) => {
      const li = document.createElement("li");
      const ic = document.createElement("span"); ic.className = "ic " + e.cls; ic.textContent = e.ic;
      const tx = document.createElement("span"); tx.textContent = e.txt;
      const tm = document.createElement("time"); tm.dateTime = e.t; tm.textContent = hhmmss(e.t);
      li.append(ic, tx, tm); ul.appendChild(li);
    });
  }

  /* ---------- estado → tela ---------- */
  const TXT = {
    ok: { pill: "Online · tudo certo", chip: "● Nível OK", face: "🐶" },
    alerta: { pill: "Alerta · ração baixa", chip: "● Ração baixa", face: "🥺" },
    stale: { pill: "Dados desatualizados", chip: "● Sem sinal", face: "😴" },
    erro: { pill: "Sem conexão com a API", chip: "● Sem conexão", face: "😴" },
  };
  function bubbleText(st, pouring, pct) {
    if (st === "erro") return "Sem conexão com a API.";
    if (st === "stale") return "Sem sinal do sensor.";
    if (pouring && st === "alerta") return "Ração baixa: comporta aberta.";
    if (pouring) return "Peso aumentando…";
    if (st === "alerta") return "Ração baixa!";
    return pct > 0.6 ? "Pote bem abastecido." : "Nível OK.";
  }
  const ageText = (ms) => { const s = Math.max(0, Math.round(ms / 1000)); return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${s % 60} s`; };

  function render() {
    const l = S.latest;
    if (!l) return;
    const age = Date.now() - new Date(l.recebido_em).getTime();
    const st = !S.online ? "erro" : age > STALE_MS ? "stale" : l.alerta ? "alerta" : "ok";
    const pouring = (st === "alerta" || Date.now() < S.pourUntil) && st !== "stale" && st !== "erro";
    const pct = clamp01(l.valor / C.CAPACIDADE_G);

    const box = $("sceneBox");
    box.className = `scene-box ${st}${pouring ? " pouring" : ""}${st === "alerta" ? " open" : ""}`;

    const y = levelY(l.valor);
    $("kibble").style.transform = `translateY(${y}px)`;
    $("pellets").style.setProperty("--fall", Math.max(24, y - Y_PELLET_START - 6) + "px");
    $("petFace").textContent = TXT[st].face;
    $("bubble").textContent = bubbleText(st, pouring, pct);

    $("valor").textContent = fmt(l.valor, 1);
    $("unidade").textContent = l.unidade;
    $("grandezaLbl").textContent = "Ração no pote · " + l.grandeza;
    $("big").className = "big" + (st === "alerta" ? " alerta" : "");
    $("meter").className = "meter" + (st === "alerta" ? " alerta" : "");
    $("meterFill").style.width = pct * 100 + "%";
    $("meter").setAttribute("aria-valuenow", Math.round(pct * 100));

    const conn = $("conn");
    conn.className = "pill " + (st === "ok" ? "" : st);
    $("connTxt").textContent = TXT[st].pill;
    const cs = $("chipState"); cs.textContent = TXT[st].chip; cs.className = "chip " + (st === "ok" ? "on" : st === "alerta" ? "warn" : "");
    const cg = $("chipGate"); cg.textContent = st === "alerta" ? "⚙️ Comporta aberta" : "⚙️ Comporta fechada"; cg.className = "chip " + (st === "alerta" ? "on" : "");

    $("hint").hidden = st !== "alerta";
    $("hora").textContent = new Date(l.recebido_em).toLocaleString("pt-BR");
    $("dev").textContent = l.device_id;
    $("stPct").textContent = fmt(pct * 100, 0);
    $("stAge").textContent = ageText(age);
  }

  function renderHistory() {
    const h = S.hist;
    if (!h.length) return;
    const vals = h.map((x) => x.valor);
    $("stAvg").textContent = fmt(vals.reduce((a, b) => a + b, 0) / vals.length, 0);
    $("stMin").textContent = fmt(Math.min(...vals), 0);
    $("stMax").textContent = fmt(Math.max(...vals), 0);
    $("stN").textContent = h.length;
    $("stAl").textContent = h.filter((x) => x.alerta).length;

    const ds = chart.data.datasets;
    chart.data.labels = h.map((x) => hhmmss(x.recebido_em));
    ds[0].data = vals;
    ds[0].pointBackgroundColor = h.map((x) => (x.alerta ? cssv("--bad") : cssv("--chart-line")));
    ds[1].data = h.map(() => C.LIMITE_ALERTA_G);
    chart.update("none");
    renderEvents(h);
  }

  /* ---------- modo demonstração (opcional: ?demo=alerta|ok|cheio|enchendo|stale) ---------- */
  const DEMO = new URLSearchParams(location.search).get("demo");
  const demoT0 = Date.now();
  function demoData() {
    const now = Date.now(), k = Math.floor((now - demoT0) / C.POLL_MS);
    const mk = (i, valor, ageMs) => ({ id: i, device_id: C.DEVICE_ID, grandeza: C.GRANDEZA, valor, unidade: "g", alerta: valor < C.LIMITE_ALERTA_G, recebido_em: new Date(now - ageMs).toISOString() });
    const n = 30;
    const vals = Array.from({ length: n }, (_, i) => {
      if (DEMO === "alerta") return Math.max(120, 520 - i * 25);
      if (DEMO === "cheio") return Math.min(590, 100 + i * 25);
      if (DEMO === "stale") return 300;
      if (DEMO === "enchendo") return 140 + ((((k - (n - 1 - i)) % 8) + 8) % 8) * 60;
      return Math.min(480, 90 + i * 20); // ok
    });
    const stale = DEMO === "stale" ? 90000 : 0;
    const h = vals.map((v, i) => mk(DEMO === "enchendo" ? k - (n - 1 - i) : i + 1, v, stale + (n - 1 - i) * C.INTERVALO_COLETA_S * 1000));
    return [h[h.length - 1], h];
  }
  if (DEMO) {
    const b = document.createElement("div");
    b.className = "card"; b.style.cssText = "text-align:center;font-weight:800;background:var(--warn-soft);color:var(--warn);padding:10px";
    b.textContent = "MODO DEMONSTRAÇÃO — dados simulados no navegador, não vêm do sensor";
    document.querySelector(".wrap").prepend(b);
  }

  /* ---------- consulta à API ---------- */
  async function tick() {
    try {
      const [l, h] = DEMO ? demoData() : await Promise.all([
        fetch(`${C.API_URL}/latest?${qs}`).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }),
        fetch(`${C.API_URL}/history?${qs}&limit=60`).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }),
      ]);
      S.online = true;
      if (l) {
        // ração subindo entre duas leituras => animação de ração caindo
        if (S.prevId !== null && l.id !== S.prevId && l.valor - S.prevValor >= 15) S.pourUntil = Date.now() + 7000;
        S.prevId = l.id; S.prevValor = l.valor;
        S.latest = l; S.hist = h;
        renderHistory();
      }
    } catch (_) {
      S.online = false;
    }
    if (S.latest) render();
    else { $("connTxt").textContent = S.online ? "Aguardando a primeira leitura…" : "Sem conexão com a API"; $("conn").className = "pill " + (S.online ? "stale" : "erro"); }
  }

  tick();
  setInterval(tick, C.POLL_MS);
  setInterval(render, 1000); // relógio local: "há X s" e detecção de dados desatualizados sem esperar a rede
})();
