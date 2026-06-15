from __future__ import annotations

"""Professional live dashboard served at GET /dashboard (Bonus: dashboard đẹp).

Self-contained HTML + Chart.js (CDN). It polls the same-origin `/metrics`
endpoint every few seconds, accumulates a time series client-side, and renders
the 6 required Layer-2 panels as real charts with units, legends, and visible
SLO threshold lines. Same origin as the API, so no CORS setup is needed.
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Day 13 — Observability Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root { --bg:#0e1117; --card:#161b22; --line:#30363d; --txt:#e6edf3; --muted:#8b949e;
          --green:#3fb950; --red:#f85149; --amber:#d29922; --blue:#58a6ff; --violet:#bc8cff; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--txt);
         font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif; }
  header { display:flex; align-items:center; justify-content:space-between;
           padding:16px 24px; border-bottom:1px solid var(--line); }
  header h1 { font-size:18px; margin:0; font-weight:600; }
  header .meta { font-size:13px; color:var(--muted); display:flex; gap:16px; align-items:center; }
  .dot { width:9px; height:9px; border-radius:50%; background:var(--green); display:inline-block;
         margin-right:6px; box-shadow:0 0 8px var(--green); }
  .grid { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; padding:20px 24px; }
  @media (max-width:1100px){ .grid{ grid-template-columns:repeat(2,1fr);} }
  @media (max-width:720px){ .grid{ grid-template-columns:1fr;} }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px;
          min-height:230px; display:flex; flex-direction:column; }
  .card h2 { font-size:13px; margin:0 0 4px; font-weight:600; color:var(--txt); }
  .card .sub { font-size:11px; color:var(--muted); margin-bottom:10px; }
  .card .big { font-size:30px; font-weight:700; }
  .card .pill { font-size:11px; padding:2px 8px; border-radius:20px; font-weight:600; }
  .ok { color:var(--green); background:rgba(63,185,80,.12);}
  .breach { color:var(--red); background:rgba(248,81,73,.12);}
  .canwrap { position:relative; flex:1; min-height:140px; }
  .kv { display:flex; justify-content:space-between; font-size:12px; color:var(--muted); padding:2px 0; }
  .kv b { color:var(--txt); }
  footer { padding:10px 24px 24px; color:var(--muted); font-size:12px; }
</style>
</head>
<body>
<header>
  <h1>🛰️ Day 13 — Observability Dashboard</h1>
  <div class="meta">
    <span><span class="dot"></span><span id="status">connecting…</span></span>
    <span>refresh: <b id="every">5s</b></span>
    <span>window: <b>live (last 1h)</b></span>
    <span id="clock"></span>
  </div>
</header>

<div class="grid">
  <div class="card">
    <h2>1 · Latency P50 / P95 / P99</h2><div class="sub">milliseconds · SLO P95 &lt; 3000ms (dashed)</div>
    <div class="canwrap"><canvas id="cLatency"></canvas></div>
  </div>
  <div class="card">
    <h2>2 · Traffic</h2><div class="sub">cumulative requests</div>
    <div class="canwrap"><canvas id="cTraffic"></canvas></div>
  </div>
  <div class="card">
    <h2>3 · Error rate</h2><div class="sub">percent · SLO &lt; 2%</div>
    <div style="display:flex;align-items:baseline;gap:10px;margin-bottom:6px;">
      <span class="big" id="errPct">0%</span><span class="pill ok" id="errPill">OK</span>
    </div>
    <div id="errBreak" style="margin-top:auto"></div>
  </div>
  <div class="card">
    <h2>4 · Cost</h2><div class="sub">USD · daily budget $2.5</div>
    <div class="canwrap"><canvas id="cCost"></canvas></div>
  </div>
  <div class="card">
    <h2>5 · Tokens in / out</h2><div class="sub">tokens (cumulative)</div>
    <div class="canwrap"><canvas id="cTokens"></canvas></div>
  </div>
  <div class="card">
    <h2>6 · Quality proxy</h2><div class="sub">heuristic 0–1 · SLO ≥ 0.75</div>
    <div style="display:flex;align-items:baseline;gap:10px;">
      <span class="big" id="qVal">0.00</span><span class="pill ok" id="qPill">OK</span>
    </div>
    <div class="canwrap"><canvas id="cQuality"></canvas></div>
  </div>
</div>
<footer>Source: same-origin <code>/metrics</code> · auto-generated live view · SLO lines mirror <code>config/slo.yaml</code></footer>

<script>
const SLO = { latency_p95: 3000, error_pct: 2.0, daily_cost: 2.5, quality: 0.75 };
const REFRESH_MS = 5000;
const MAX_POINTS = 720; // ~1h at 5s
Chart.defaults.color = '#8b949e';
Chart.defaults.borderColor = '#30363d';
Chart.defaults.font.size = 11;

function mkLine(id, datasets){
  return new Chart(document.getElementById(id), {
    type:'line',
    data:{ labels:[], datasets },
    options:{ responsive:true, maintainAspectRatio:false, animation:false,
      interaction:{intersect:false,mode:'index'},
      plugins:{ legend:{ labels:{ boxWidth:10 } } },
      scales:{ x:{ ticks:{ maxTicksLimit:6 } }, y:{ beginAtZero:true } } }
  });
}
const sloLine = (label,val,color)=>({ label, data:[], borderColor:color, borderDash:[6,4],
  borderWidth:1.5, pointRadius:0, fill:false });

const latency = mkLine('cLatency',[
  {label:'P50',data:[],borderColor:'#58a6ff',backgroundColor:'#58a6ff22',tension:.3,pointRadius:0,fill:true},
  {label:'P95',data:[],borderColor:'#d29922',tension:.3,pointRadius:0},
  {label:'P99',data:[],borderColor:'#f85149',tension:.3,pointRadius:0},
  sloLine('SLO 3000ms',SLO.latency_p95,'#8b949e'),
]);
const traffic = mkLine('cTraffic',[
  {label:'requests',data:[],borderColor:'#3fb950',backgroundColor:'#3fb95022',tension:.3,pointRadius:0,fill:true},
]);
const cost = mkLine('cCost',[
  {label:'total $',data:[],borderColor:'#bc8cff',backgroundColor:'#bc8cff22',tension:.3,pointRadius:0,fill:true},
]);
const tokens = mkLine('cTokens',[
  {label:'tokens_in',data:[],borderColor:'#58a6ff',tension:.3,pointRadius:0},
  {label:'tokens_out',data:[],borderColor:'#d29922',tension:.3,pointRadius:0},
]);
const quality = mkLine('cQuality',[
  {label:'quality',data:[],borderColor:'#3fb950',backgroundColor:'#3fb95022',tension:.3,pointRadius:0,fill:true},
  sloLine('SLO 0.75',SLO.quality,'#8b949e'),
]);

function push(chart, label, values){
  chart.data.labels.push(label);
  values.forEach((v,i)=> chart.data.datasets[i].data.push(v));
  if(chart.data.labels.length>MAX_POINTS){
    chart.data.labels.shift();
    chart.data.datasets.forEach(d=>d.data.shift());
  }
  chart.update('none');
}

async function poll(){
  try{
    const m = await (await fetch('/metrics',{cache:'no-store'})).json();
    const t = new Date().toLocaleTimeString();
    document.getElementById('status').textContent = 'live · '+m.traffic+' req';
    document.getElementById('clock').textContent = t;

    push(latency, t, [m.latency_p50, m.latency_p95, m.latency_p99, SLO.latency_p95]);
    push(traffic, t, [m.traffic]);
    push(cost, t, [m.total_cost_usd]);
    push(tokens, t, [m.tokens_in_total, m.tokens_out_total]);
    push(quality, t, [m.quality_avg, SLO.quality]);

    const errs = m.error_breakdown || {};
    const totalErr = Object.values(errs).reduce((a,b)=>a+b,0);
    const pct = m.traffic ? (totalErr/m.traffic*100) : 0;
    const breach = pct > SLO.error_pct;
    document.getElementById('errPct').textContent = pct.toFixed(2)+'%';
    const ep = document.getElementById('errPill');
    ep.textContent = breach?'BREACH':'OK'; ep.className = 'pill '+(breach?'breach':'ok');
    document.getElementById('errBreak').innerHTML =
      Object.keys(errs).length ? Object.entries(errs).map(([k,v])=>`<div class="kv"><span>${k}</span><b>${v}</b></div>`).join('')
      : '<div class="kv"><span>no errors</span><b>0</b></div>';

    const q = m.quality_avg||0, qBreach = q < SLO.quality;
    document.getElementById('qVal').textContent = q.toFixed(3);
    const qp = document.getElementById('qPill');
    qp.textContent = qBreach?'BREACH':'OK'; qp.className='pill '+(qBreach?'breach':'ok');
  }catch(e){
    document.getElementById('status').textContent = 'server offline — start uvicorn';
  }
}
document.getElementById('every').textContent = (REFRESH_MS/1000)+'s';
poll();
setInterval(poll, REFRESH_MS);
</script>
</body>
</html>
"""
