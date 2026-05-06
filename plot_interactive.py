"""
plot_interactive.py — Generate an interactive HTML S-parameter viewer.

Usage:
    python plot_interactive.py path/to/result.s3p [--out path/to/out.html] [--title "My Design"]

Produces a self-contained HTML file with:
  - Draggable vertical cursor showing S11/S21/S31 at any frequency
  - Claude-style colour scheme (warm white + orange accent)
  - Metrics panel with pass/fail indicators
"""
import argparse
import json
import math
import sys
from pathlib import Path


# ── S3P parser (identical to diplexer.py) ────────────────────────────────────

def parse_s3p(path):
    recs, fmt, buf = [], "MA", []
    for line in Path(path).read_text(errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("!"): continue
        if s.startswith("#"):
            fmt = "DB" if "DB" in s.upper() else ("RI" if "RI" in s.upper() else "MA")
            continue
        if line[0] in (" ", "\t"):
            buf.extend(float(x) for x in s.split())
        else:
            if buf: recs.append(buf)
            buf = [float(x) for x in s.split()]
    if buf: recs.append(buf)

    db = lambda v: 20 * math.log10(v) if v > 0 else -100.0
    fr, s11, s21, s31 = [], [], [], []
    for r in recs:
        if len(r) < 19: continue
        f = r[0] / 1e9 if r[0] > 1e7 else r[0]
        fr.append(f)
        if fmt == "DB":
            s11.append(r[1]);  s21.append(r[7]);  s31.append(r[13])
        elif fmt == "MA":
            s11.append(db(r[1]));  s21.append(db(r[7]));  s31.append(db(r[13]))
        else:
            s11.append(db(math.hypot(r[1],  r[2])))
            s21.append(db(math.hypot(r[7],  r[8])))
            s31.append(db(math.hypot(r[13], r[14])))
    return fr, s11, s21, s31


def at(fr, vals, f):
    return vals[min(range(len(fr)), key=lambda i: abs(fr[i] - f))]


def crossing_freq(fr, s21, s31):
    for i in range(len(fr) - 1):
        d0, d1 = s21[i] - s31[i], s21[i+1] - s31[i+1]
        if d0 * d1 <= 0:
            t = d0 / (d0 - d1) if abs(d0 - d1) > 1e-9 else 0.5
            return fr[i] + t * (fr[i+1] - fr[i])
    return None


def compute_metrics(fr, s11, s21, s31):
    fc    = crossing_freq(fr, s21, s31)
    s19   = at(fr, s31, 19.0)
    s20   = at(fr, s31, 20.0)
    pb    = [at(fr, s21, f) for f in [20, 21, 22, 23, 25]]
    rip25 = max(pb) - min(pb)
    il20  = min(pb)
    s11w  = max(at(fr, s11, f) for f in [19, 20, 21, 22, 25])
    return {
        "crossing_GHz":          round(fc, 4) if fc else None,
        "S31_at_19GHz_dB":       round(s19,  2),
        "S31_at_20GHz_dB":       round(s20,  2),
        "ripple_20_25GHz_dB":    round(rip25, 2),
        "min_IL_20plus_dB":      round(il20,  2),
        "S11_worst_19_25GHz_dB": round(s11w,  2),
        "targets_met": {
            "crossing_ge_18p5GHz":    bool(fc and fc >= 18.5),
            "S31_at_19_le_neg10dB":   s19  <= -10.0,
            "S31_at_20_le_neg10dB":   s20  <= -10.0,
            "ripple_20_25GHz_le_1dB": rip25 <= 1.0,
        },
    }


# ── HTML generator ────────────────────────────────────────────────────────────

def build_html(fr, s11, s21, s31, metrics, title):
    data_json = json.dumps({
        "fr":  [round(v, 5) for v in fr],
        "s11": [round(v, 3) for v in s11],
        "s21": [round(v, 3) for v in s21],
        "s31": [round(v, 3) for v in s31],
    })
    m  = metrics
    fc = m["crossing_GHz"]
    tm = m["targets_met"]

    def badge(ok, text):
        cls = "badge-pass" if ok else "badge-fail"
        sym = "✓" if ok else "✗"
        return f'<span class="badge {cls}">{sym} {text}</span>'

    metrics_html = f"""
      {badge(tm["crossing_ge_18p5GHz"],    f'Cross {fc:.3f} GHz' if fc else 'Cross n/a')}
      {badge(tm["S31_at_19_le_neg10dB"],   f'S31@19 = {m["S31_at_19GHz_dB"]:.1f} dB')}
      {badge(tm["S31_at_20_le_neg10dB"],   f'S31@20 = {m["S31_at_20GHz_dB"]:.1f} dB')}
      {badge(tm["ripple_20_25GHz_le_1dB"], f'Ripple {m["ripple_20_25GHz_dB"]:.2f} dB')}
      <span class="badge badge-info">IL {m["min_IL_20plus_dB"]:.1f} dB</span>
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --bg:        #FAF9F6;
    --bg-panel:  #FFFFFF;
    --border:    #E8E5DF;
    --grid:      #EAE8E3;
    --text:      #1A1916;
    --text-muted:#7A786F;
    --orange:    #E8670A;
    --orange-lt: #FDF0E6;
    --s21:       #2C2C2C;
    --s31:       #E8670A;
    --s11:       #9E9B94;
    --pass:      #2D6A4F;
    --pass-bg:   #D8F3DC;
    --fail:      #C0392B;
    --fail-bg:   #FDECEA;
    --info-bg:   #EEF1F6;
    --info:      #2F4A7A;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Inter', 'SF Pro Display', -apple-system, 'Segoe UI', 'Helvetica Neue', sans-serif;
    background: var(--bg);
    color: var(--text);
    height: 100dvh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}

  /* ── Header ── */
  header {{
    padding: 12px 20px 10px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-panel);
    display: flex;
    align-items: baseline;
    gap: 12px;
    flex-shrink: 0;
  }}
  header h1 {{
    font-size: 16px;
    font-weight: 650;
    letter-spacing: -0.3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  header .sub {{
    font-size: 13px;
    font-weight: 600;
    color: var(--text-muted);
    white-space: nowrap;
  }}

  /* ── Metrics bar ── */
  .metrics-bar {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 8px 20px;
    background: var(--bg-panel);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }}
  .badge {{
    font-size: 12.5px;
    font-weight: 700;
    padding: 4px 11px;
    border-radius: 99px;
    letter-spacing: 0.05px;
  }}
  .badge-pass {{ background: var(--pass-bg);  color: var(--pass); }}
  .badge-fail {{ background: var(--fail-bg);  color: var(--fail); }}
  .badge-info {{ background: var(--info-bg);  color: var(--info); }}

  /* ── Chart area ── */
  .chart-wrap {{
    flex: 1;
    position: relative;
    min-height: 0;
    padding: 8px 16px 4px 8px;
  }}
  svg#chart {{
    width: 100%;
    height: 100%;
    cursor: crosshair;
    display: block;
  }}

  /* ── Legend ── */
  .legend {{
    display: flex;
    gap: 20px;
    justify-content: center;
    padding: 6px 0 8px;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-muted);
    flex-shrink: 0;
    border-top: 1px solid var(--border);
    background: var(--bg-panel);
  }}
  .legend-item {{ display: flex; align-items: center; gap: 5px; }}
  .legend-swatch {{
    width: 22px; height: 2.5px; border-radius: 2px; flex-shrink: 0;
  }}
  .legend-swatch.dashed {{
    background: repeating-linear-gradient(
      to right, var(--s11) 0 4px, transparent 4px 7px);
  }}

  /* readout is SVG-native — no CSS needed */
</style>
</head>
<body>

<header>
  <h1>{title}</h1>
  <span class="sub">Drag to inspect · S-Parameters 0–40 GHz</span>
</header>

<div class="metrics-bar">
  {metrics_html}
</div>

<div class="chart-wrap" id="chartWrap">
  <svg id="chart" xmlns="http://www.w3.org/2000/svg"></svg>
</div>

<div class="legend">
  <div class="legend-item">
    <div class="legend-swatch" style="background:var(--s21)"></div>S21 — HPF passband
  </div>
  <div class="legend-item">
    <div class="legend-swatch" style="background:var(--s31)"></div>S31 — LPF arm
  </div>
  <div class="legend-item">
    <div class="legend-swatch dashed"></div>S11 — Return loss
  </div>
</div>

<script>
const DATA = {data_json};
const METRICS = {json.dumps(metrics)};

const FMIN = 0, FMAX = 40, YMIN = -40, YMAX = 5;

const svg    = document.getElementById('chart');
const wrap   = document.getElementById('chartWrap');
let rdGrp = null;

let ML = 58, MR = 16, MT = 12, MB = 40;
let PW, PH, W, H;

function recompute() {{
  const r = svg.getBoundingClientRect();
  W = r.width; H = r.height;
  PW = W - ML - MR;
  PH = H - MT - MB;
}}

const px = f => ML + (f - FMIN) / (FMAX - FMIN) * PW;
const py = y => MT + (YMAX - y) / (YMAX - YMIN) * PH;
const fx = x => FMIN + (x - ML) / PW * (FMAX - FMIN);

function interp(f) {{
  const fr = DATA.fr;
  let lo = 0;
  for (let i = 1; i < fr.length; i++) {{
    if (fr[i] >= f) {{ lo = i - 1; break; }}
    lo = i;
  }}
  const hi = Math.min(lo + 1, fr.length - 1);
  const t = fr[hi] === fr[lo] ? 0 : (f - fr[lo]) / (fr[hi] - fr[lo]);
  const lerp = (a, k) => a[lo] + t * (a[k] - a[lo]);  // unused, using hi
  const lerp2 = arr => arr[lo] + t * (arr[hi] - arr[lo]);
  return {{ s11: lerp2(DATA.s11), s21: lerp2(DATA.s21), s31: lerp2(DATA.s31) }};
}}

function polylinePoints(fArr, yArr) {{
  return fArr.map((f, i) => {{
    const x = px(f), y = Math.max(MT - 2, Math.min(MT + PH + 2, py(yArr[i])));
    return x.toFixed(1) + ',' + y.toFixed(1);
  }}).join(' ');
}}

function mkEl(tag, attrs) {{
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}}

let cursorLine = null;
let isDragging = false;

function build() {{
  recompute();
  svg.innerHTML = '';

  // Background
  svg.appendChild(mkEl('rect', {{x:0, y:0, width:W, height:H, fill:'#FAF9F6'}}));

  // Plot area background
  svg.appendChild(mkEl('rect', {{x:ML, y:MT, width:PW, height:PH, fill:'#FFFFFF',
    rx:2, stroke:'#E8E5DF', 'stroke-width':1}}));

  // Passband shading 18.5–40 GHz
  svg.appendChild(mkEl('rect', {{
    x: px(18.5).toFixed(1), y: MT, width: (px(40)-px(18.5)).toFixed(1), height: PH,
    fill: '#FDF0E6', opacity: 0.5
  }}));

  // Grid & Y axis
  for (let y = YMIN; y <= YMAX; y += 5) {{
    const yp = py(y).toFixed(1);
    const isZero = y === 0;
    svg.appendChild(mkEl('line', {{
      x1:ML, y1:yp, x2:ML+PW, y2:yp,
      stroke: isZero ? '#C8C5BE' : '#EAE8E3',
      'stroke-width': isZero ? 1 : 0.8
    }}));
    const t = mkEl('text', {{
      x: (ML-8).toFixed(1), y: (parseFloat(yp)+4).toFixed(1),
      'text-anchor':'end', fill:'#9E9B94',
      'font-size':12, 'font-weight':700, 'font-family':"'Roboto Mono','Consolas',monospace"
    }});
    t.textContent = y;
    svg.appendChild(t);
  }}

  // Grid & X axis
  for (let f = 0; f <= 40; f += 5) {{
    const xp = px(f).toFixed(1);
    svg.appendChild(mkEl('line', {{
      x1:xp, y1:MT, x2:xp, y2:MT+PH,
      stroke:'#EAE8E3', 'stroke-width':0.8
    }}));
    const t = mkEl('text', {{
      x:xp, y:(MT+PH+20).toFixed(1),
      'text-anchor':'middle', fill:'#9E9B94',
      'font-size':12, 'font-weight':700, 'font-family':"'Roboto Mono','Consolas',monospace"
    }});
    t.textContent = f;
    svg.appendChild(t);
  }}

  // 18.5 GHz reference
  const x185 = px(18.5).toFixed(1);
  svg.appendChild(mkEl('line', {{
    x1:x185, y1:MT, x2:x185, y2:MT+PH,
    stroke:'#E8670A', 'stroke-width':1.2,
    'stroke-dasharray':'6 3', opacity:0.45
  }}));
  const t185 = mkEl('text', {{
    x:(parseFloat(x185)+5).toFixed(1), y:(MT+15).toFixed(1),
    fill:'#E8670A', 'font-size':11.5, 'font-weight':700, 'font-family':"'Roboto Mono','Consolas',monospace", opacity:0.75
  }});
  t185.textContent = '18.5 GHz';
  svg.appendChild(t185);

  // -10 dB reference
  const yn10 = py(-10).toFixed(1);
  svg.appendChild(mkEl('line', {{
    x1:ML, y1:yn10, x2:ML+PW, y2:yn10,
    stroke:'#C8A882', 'stroke-width':1,
    'stroke-dasharray':'4 3', opacity:0.5
  }}));
  const tn10 = mkEl('text', {{
    x:(ML+6).toFixed(1), y:(parseFloat(yn10)-5).toFixed(1),
    fill:'#C8A882', 'font-size':11.5, 'font-weight':700, 'font-family':"'Roboto Mono','Consolas',monospace", opacity:0.8
  }});
  tn10.textContent = '−10 dB';
  svg.appendChild(tn10);

  // -1 dB reference
  const yn1 = py(-1).toFixed(1);
  svg.appendChild(mkEl('line', {{
    x1:ML, y1:yn1, x2:ML+PW, y2:yn1,
    stroke:'#B8B5AE', 'stroke-width':0.8,
    'stroke-dasharray':'3 4', opacity:0.45
  }}));

  // Traces
  // S11 (dashed, light grey)
  const pl11 = mkEl('polyline', {{
    points: polylinePoints(DATA.fr, DATA.s11),
    fill:'none', stroke:'#B8B5AE', 'stroke-width':1.5,
    'stroke-dasharray':'5 3'
  }});
  svg.appendChild(pl11);

  // S31 (orange)
  const pl31 = mkEl('polyline', {{
    points: polylinePoints(DATA.fr, DATA.s31),
    fill:'none', stroke:'#E8670A', 'stroke-width':2.4
  }});
  svg.appendChild(pl31);

  // S21 (dark, primary)
  const pl21 = mkEl('polyline', {{
    points: polylinePoints(DATA.fr, DATA.s21),
    fill:'none', stroke:'#2C2C2C', 'stroke-width':2.4
  }});
  svg.appendChild(pl21);

  // Crossing marker
  const fc = METRICS.crossing_GHz;
  if (fc) {{
    const cx = px(fc), cy = py(interp(fc).s21);
    const circ = mkEl('circle', {{
      cx:cx.toFixed(1), cy:cy.toFixed(1), r:4.5,
      fill:'#FAF9F6', stroke:'#E8670A', 'stroke-width':1.8
    }});
    svg.appendChild(circ);
    const ct = mkEl('text', {{
      x:(cx+8).toFixed(1), y:(cy-7).toFixed(1),
      fill:'#E8670A', 'font-size':12, 'font-family':"'Roboto Mono','Consolas',monospace", 'font-weight':700
    }});
    ct.textContent = fc.toFixed(3) + ' GHz';
    svg.appendChild(ct);
  }}

  // Axis label Y
  const axY = mkEl('text', {{
    x:14, y:(MT+PH/2).toFixed(1),
    'text-anchor':'middle', fill:'#9E9B94', 'font-size':12.5, 'font-weight':700,
    'font-family':"'Inter','Segoe UI',sans-serif",
    transform:`rotate(-90,14,${{(MT+PH/2).toFixed(1)}})`
  }});
  axY.textContent = 'S-parameters (dB)';
  svg.appendChild(axY);

  // Axis label X
  const axX = mkEl('text', {{
    x:(ML+PW/2).toFixed(1), y:(H-6).toFixed(1),
    'text-anchor':'middle', fill:'#9E9B94', 'font-size':12.5, 'font-weight':700,
    'font-family':"'Inter','Segoe UI',sans-serif"
  }});
  axX.textContent = 'Frequency (GHz)';
  svg.appendChild(axX);

  // Cursor line
  cursorLine = mkEl('line', {{
    x1:0, y1:MT, x2:0, y2:MT+PH,
    stroke:'#E8670A', 'stroke-width':1.5, opacity:0,
    'pointer-events':'none'
  }});
  svg.appendChild(cursorLine);

  // SVG-native readout box
  const RD_W2 = 192, RD_H2 = 104;
  const MONO = "'Roboto Mono','Consolas',monospace";
  const SANS = "'Inter','Segoe UI',sans-serif";
  rdGrp = mkEl('g', {{opacity:0, 'pointer-events':'none'}});
  rdGrp.appendChild(mkEl('rect', {{
    x:0, y:0, width:RD_W2, height:RD_H2,
    rx:9, fill:'white', 'fill-opacity':0.45,
    stroke:'#D8D5CF', 'stroke-width':1, 'stroke-opacity':0.8
  }}));
  rdGrp.appendChild(mkEl('line', {{
    x1:10, y1:32, x2:RD_W2-10, y2:32,
    stroke:'#E8E5DF', 'stroke-width':1
  }}));
  const roFreq = mkEl('text', {{
    id:'ro-freq', x:10, y:23,
    fill:'#E8670A', 'font-size':14, 'font-weight':700, 'font-family':MONO
  }});
  roFreq.textContent = '—';
  rdGrp.appendChild(roFreq);
  const rows = [
    {{id:'ro-s21', label:'S21', color:'#2C2C2C', y:54}},
    {{id:'ro-s31', label:'S31', color:'#E8670A', y:74}},
    {{id:'ro-s11', label:'S11', color:'#9E9B94', y:94}},
  ];
  rows.forEach(r => {{
    const lbl = mkEl('text', {{
      x:10, y:r.y, fill:'#9E9B94', 'font-size':12.5, 'font-weight':700, 'font-family':SANS
    }});
    lbl.textContent = r.label;
    const val = mkEl('text', {{
      id:r.id, x:RD_W2-10, y:r.y,
      'text-anchor':'end', fill:r.color,
      'font-size':13.5, 'font-weight':800, 'font-family':MONO
    }});
    val.textContent = '—';
    rdGrp.appendChild(lbl);
    rdGrp.appendChild(val);
  }});
  svg.appendChild(rdGrp);
}}

const RD_W = 192, RD_H = 104, RD_GAP = 14;

function updateCursor(clientX) {{
  if (!rdGrp) return;
  const svgRect = svg.getBoundingClientRect();
  const x = clientX - svgRect.left;
  const f = Math.max(FMIN, Math.min(FMAX, fx(x)));
  const cx = px(f);

  cursorLine.setAttribute('x1', cx.toFixed(1));
  cursorLine.setAttribute('x2', cx.toFixed(1));
  cursorLine.setAttribute('opacity', 0.75);

  // Position readout in SVG coords — flip left when near right edge
  const showLeft = (cx + RD_GAP + RD_W) > (ML + PW - 4);
  const rx = showLeft ? cx - RD_GAP - RD_W : cx + RD_GAP;
  const ry = MT + PH / 2 - RD_H / 2;
  rdGrp.setAttribute('transform', `translate(${{rx.toFixed(1)}},${{ry.toFixed(1)}})`);
  rdGrp.setAttribute('opacity', 1);

  const vals = interp(f);
  rdGrp.querySelector('#ro-freq').textContent = f.toFixed(3) + ' GHz';
  rdGrp.querySelector('#ro-s21').textContent  = vals.s21.toFixed(2) + ' dB';
  rdGrp.querySelector('#ro-s31').textContent  = vals.s31.toFixed(2) + ' dB';
  rdGrp.querySelector('#ro-s11').textContent  = vals.s11.toFixed(2) + ' dB';
}}

svg.addEventListener('mouseenter', () => {{ isDragging = true; }});
svg.addEventListener('mouseleave', () => {{
  isDragging = false;
  if (cursorLine) cursorLine.setAttribute('opacity', 0);
  if (rdGrp) rdGrp.setAttribute('opacity', 0);
}});
svg.addEventListener('mousemove', e => updateCursor(e.clientX));
svg.addEventListener('touchmove', e => {{
  e.preventDefault();
  updateCursor(e.touches[0].clientX);
}}, {{ passive: false }});

// Build on load and on resize
window.addEventListener('resize', () => build());
window.addEventListener('load',   () => build());
</script>
</body>
</html>"""


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Generate interactive HTML S-parameter viewer.")
    p.add_argument("s3p",              help="Path to .s3p file")
    p.add_argument("--out",            help="Output HTML path (default: same dir as s3p)")
    p.add_argument("--title", default="", help="Chart title")
    p.add_argument("--open", action="store_true", help="Open in browser after generating")
    args = p.parse_args()

    s3p_path = Path(args.s3p)
    if not s3p_path.exists():
        sys.exit(f"ERROR: {s3p_path} not found")

    out_path = Path(args.out) if args.out else s3p_path.with_suffix(".html")
    title    = args.title or s3p_path.stem

    fr, s11, s21, s31 = parse_s3p(s3p_path)
    metrics = compute_metrics(fr, s11, s21, s31)
    html    = build_html(fr, s11, s21, s31, metrics, title)
    out_path.write_text(html, encoding="utf-8")
    print(f"Saved: {out_path}")

    if args.open:
        import subprocess
        subprocess.Popen(["explorer", str(out_path)])


if __name__ == "__main__":
    main()
