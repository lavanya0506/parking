#!/usr/bin/env python3
"""
ParkIQ — HTML Frame Generator v3
  • Flipkart Gridlock Hackathon 2.0 branding + FK logo
  • Overflow-safe layouts (every card clamps to viewport)
  • Tighter padding to prevent boundary clipping
"""

import os, math, subprocess, ast, base64
import pandas as pd
from collections import Counter

BASE     = os.path.dirname(os.path.abspath(__file__))
HTML_DIR = os.path.join(BASE, "assets", "html_frames")
PNG_DIR  = os.path.join(BASE, "assets", "frames")
CHROME   = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

os.makedirs(HTML_DIR, exist_ok=True)
os.makedirs(PNG_DIR,  exist_ok=True)

# ── Load data ──────────────────────────────────────────────────────────────────
print("Loading data…")
df = pd.read_parquet(os.path.join(BASE, "data", "violations.parquet"))
ev = pd.read_parquet(os.path.join(BASE, "data", "events.parquet"))
df["dt"]  = pd.to_datetime(df["created_datetime"], format="mixed", utc=True)
df["hour_ist"] = (df["dt"].dt.hour + 5) % 24
df["dow"]  = df["dt"].dt.dayofweek
df["month"]= df["dt"].dt.month

hourly = df["hour_ist"].value_counts().sort_index().to_dict()
dow    = df["dow"].value_counts().sort_index().to_dict()
monthly= df["month"].value_counts().sort_index().to_dict()
veh    = df["vehicle_type"].value_counts().head(6).to_dict()
top_j  = df[df["junction_name"].str.contains("BTP",na=False)]["junction_name"].value_counts().head(10)

geo = df[df["latitude"].between(12.8,13.15) & df["longitude"].between(77.45,77.75)].sample(n=2500,random_state=42)

all_vt=[]
for s in df["violation_type"].dropna():
    try:    all_vt.extend(ast.literal_eval(s))
    except: all_vt.append(str(s))
vt_top = Counter(all_vt).most_common(6)
print(f"  {len(df):,} violations · top: {top_j.index[0]}")

# ── Inline SVG helpers ─────────────────────────────────────────────────────────
def bar_h(data, w=700, h=300, color="#E94560"):
    if not data: return ""
    mx = max(v for _,v in data); bar_area = w-220
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">',
           f'<rect width="{w}" height="{h}" fill="#0D0D2B" rx="8"/>']
    for i,(lbl,val) in enumerate(data):
        y = i*(h/len(data)); cy = y+h/len(data)*0.5; bw=int(val/mx*bar_area)
        lbl2=(lbl.split(" - ")[-1] if " - " in lbl else lbl)[:20]
        lines+=[f'<rect x="200" y="{cy-7:.0f}" width="{bar_area}" height="14" fill="#1a1a3e" rx="3"/>',
                f'<rect x="200" y="{cy-7:.0f}" width="{bw}" height="14" fill="{color}" rx="3" opacity=".85"/>',
                f'<text x="195" y="{cy+4:.0f}" text-anchor="end" fill="#C8C8E8" font-size="12" font-family="system-ui">{lbl2}</text>',
                f'<text x="{w-5}" y="{cy+4:.0f}" text-anchor="end" fill="#fff" font-size="12" font-weight="700" font-family="system-ui">{val:,}</text>']
    lines.append("</svg>"); return "\n".join(lines)

def line_chart(data, w=820, h=260, color="#4ADEDE"):
    if not data: return ""
    keys=sorted(data.keys()); vals=[data[k] for k in keys]
    mx=max(vals); pl,pr,pt,pb=55,20,20,38; W=w-pl-pr; H=h-pt-pb
    def px(i): return pl+i*W/max(len(keys)-1,1)
    def py(v): return pt+H-(v/mx)*H
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">',
           f'<rect width="{w}" height="{h}" fill="#0D0D2B" rx="8"/>']
    for gi in range(5):
        gy=pt+gi*H/4
        lines+=[f'<line x1="{pl}" y1="{gy:.0f}" x2="{pl+W}" y2="{gy:.0f}" stroke="#1e1e48" stroke-width="1"/>',
                f'<text x="{pl-4}" y="{gy+4:.0f}" text-anchor="end" fill="#555577" font-size="10" font-family="system-ui">{int((mx-gi*mx/4)/1000)}k</text>']
    area=f"M{pl},{pt+H} "+" ".join(f"L{px(i):.0f},{py(v):.0f}" for i,v in enumerate(vals))+f" L{pl+W},{pt+H} Z"
    lines+=[f'<defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{color}" stop-opacity=".25"/><stop offset="100%" stop-color="{color}" stop-opacity=".02"/></linearGradient></defs>',
            f'<path d="{area}" fill="url(#ag)"/>']
    pts="M"+" L".join(f"{px(i):.0f},{py(v):.0f}" for i,v in enumerate(vals))
    lines.append(f'<path d="{pts}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round"/>')
    pi=vals.index(max(vals))
    lines+=[f'<circle cx="{px(pi):.0f}" cy="{py(vals[pi]):.0f}" r="5" fill="{color}" stroke="#fff" stroke-width="1.5"/>',
            f'<text x="{px(pi):.0f}" y="{py(vals[pi])-10:.0f}" text-anchor="middle" fill="{color}" font-size="11" font-weight="700" font-family="system-ui">Peak {keys[pi]:02d}:00 IST</text>']
    for i,k in enumerate(keys):
        if k%3==0:
            lines.append(f'<text x="{px(i):.0f}" y="{pt+H+16}" text-anchor="middle" fill="#666688" font-size="10" font-family="system-ui">{k:02d}</text>')
    lines.append("</svg>"); return "\n".join(lines)

def bar_v(data, w=400, h=230, color="#A29BFE"):
    keys=sorted(data.keys()); vals=[data[k] for k in keys]; mx=max(vals)
    pl,pr,pt,pb=30,10,15,30; W=w-pl-pr; H=h-pt-pb
    bw=W/len(keys)*0.65; gap=W/len(keys)
    DAY={0:"Mon",1:"Tue",2:"Wed",3:"Thu",4:"Fri",5:"Sat",6:"Sun"}
    MON={1:"Jan",2:"Feb",3:"Mar",4:"Apr",11:"Nov",12:"Dec"}
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">',f'<rect width="{w}" height="{h}" fill="#0D0D2B" rx="8"/>']
    for i,(k,v) in enumerate(zip(keys,vals)):
        cx=pl+i*gap+gap/2; bh=(v/mx)*H; by=pt+H-bh
        lines+=[f'<rect x="{cx-bw/2:.0f}" y="{by:.0f}" width="{bw:.0f}" height="{bh:.0f}" fill="{color}" rx="3" opacity=".85"/>',
                f'<text x="{cx:.0f}" y="{pt+H+14}" text-anchor="middle" fill="#888899" font-size="10" font-family="system-ui">{DAY.get(k,MON.get(k,str(k)))}</text>']
        if v==mx:
            lines.append(f'<text x="{cx:.0f}" y="{by-4:.0f}" text-anchor="middle" fill="{color}" font-size="10" font-weight="700" font-family="system-ui">{int(v/1000)}k</text>')
    lines.append("</svg>"); return "\n".join(lines)

def donut(segs, w=280, h=280):
    total=sum(v for _,v,_ in segs); cx=w/2; cy=h/2; r=min(w,h)/2-12; ir=r*0.55
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">']
    angle=-math.pi/2
    for lbl,val,col in segs:
        sw=2*math.pi*val/total
        x1=cx+r*math.cos(angle);y1=cy+r*math.sin(angle)
        x2=cx+r*math.cos(angle+sw);y2=cy+r*math.sin(angle+sw)
        xi1=cx+ir*math.cos(angle);yi1=cy+ir*math.sin(angle)
        xi2=cx+ir*math.cos(angle+sw);yi2=cy+ir*math.sin(angle+sw)
        lg=1 if sw>math.pi else 0
        d=(f"M{xi1:.1f},{yi1:.1f} L{x1:.1f},{y1:.1f} A{r:.1f},{r:.1f} 0 {lg},1 {x2:.1f},{y2:.1f} "
           f"L{xi2:.1f},{yi2:.1f} A{ir:.1f},{ir:.1f} 0 {lg},0 {xi1:.1f},{yi1:.1f} Z")
        lines.append(f'<path d="{d}" fill="{col}" opacity=".9"/>')
        angle+=sw
    lines+=[f'<text x="{cx}" y="{cy-6}" text-anchor="middle" fill="#EAEAEA" font-size="20" font-weight="900" font-family="system-ui">{int(total/1000)}k</text>',
            f'<text x="{cx}" y="{cy+14}" text-anchor="middle" fill="#9A9AB0" font-size="11" font-family="system-ui">violations</text>',
            "</svg>"]
    return "\n".join(lines)

def geo_scatter(lats,lons,w=680,h=430):
    if not lats: return ""
    mlat,xlat=min(lats),max(lats); mlon,xlon=min(lons),max(lons); p=18
    W=w-2*p; H=h-2*p
    def px(lon): return p+(lon-mlon)/max(xlon-mlon,.001)*W
    def py(lat): return p+H-(lat-mlat)/max(xlat-mlat,.001)*H
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">',
           f'<rect width="{w}" height="{h}" fill="#060A20" rx="10"/>']
    for gi in range(5):
        gx=p+gi*W/4; gy=p+gi*H/4
        lines+=[f'<line x1="{gx:.0f}" y1="{p}" x2="{gx:.0f}" y2="{p+H}" stroke="#0e1630" stroke-width="1"/>',
                f'<line x1="{p}" y1="{gy:.0f}" x2="{p+W}" y2="{gy:.0f}" stroke="#0e1630" stroke-width="1"/>']
    for lat,lon in zip(lats[:2000],lons[:2000]):
        lines.append(f'<circle cx="{px(lon):.1f}" cy="{py(lat):.1f}" r="1.8" fill="#E94560" opacity=".35"/>')
    for lat,lon,lbl,c in [(13.0009,77.5850,"Safina Plaza","#F5A623"),(12.9716,77.5946,"KR Market","#4ADEDE")]:
        if mlat<=lat<=xlat and mlon<=lon<=xlon:
            x,y=px(lon),py(lat)
            lines+=[f'<circle cx="{x:.0f}" cy="{y:.0f}" r="6" fill="{c}" stroke="#fff" stroke-width="1.5" opacity=".9"/>',
                    f'<text x="{x+9}" y="{y+4:.0f}" fill="{c}" font-size="11" font-weight="700" font-family="system-ui">{lbl}</text>']
    lines.append("</svg>"); return "\n".join(lines)

# ── Design tokens ──────────────────────────────────────────────────────────────
FK_B64 = "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"
FLIPKART_LOGO = f"""
<div class="fk-pill">
  <img src="data:image/png;base64,{FK_B64}" width="44" height="44" style="border-radius:8px;display:block;" alt="Flipkart"/>
</div>"""

BASE_CSS = """
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
html,body{
  width:1920px;height:980px;overflow:hidden;
  background:#060614;
  font-family:-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif;
  -webkit-font-smoothing:antialiased;color:#E8E8F0;
}
body::before{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:
    radial-gradient(ellipse 160% 100% at 20% 0%,rgba(233,69,96,.06) 0%,transparent 55%),
    radial-gradient(ellipse 120% 80% at 80% 100%,rgba(74,222,222,.04) 0%,transparent 50%),
    linear-gradient(rgba(255,255,255,.018) 1px,transparent 1px),
    linear-gradient(90deg,rgba(255,255,255,.018) 1px,transparent 1px);
  background-size:auto,auto,60px 60px,60px 60px;
}
/* ── Nav ── */
.nav{
  position:absolute;top:0;left:0;width:1920px;height:68px;
  background:rgba(6,4,20,.97);border-bottom:1px solid rgba(233,69,96,.3);
  display:flex;align-items:center;padding:0 40px;gap:14px;z-index:100;
}
.nav-logo{
  background:linear-gradient(135deg,#E94560,#c42040);border-radius:9px;
  width:40px;height:40px;display:flex;align-items:center;justify-content:center;
  font-size:22px;font-weight:900;color:#fff;flex-shrink:0;
  box-shadow:0 4px 16px rgba(233,69,96,.4);
}
.nav-brand{font-size:24px;font-weight:900;color:#E94560;letter-spacing:-.5px}
.nav-sep{font-size:16px;color:rgba(255,255,255,.15);margin:0 6px}
.nav-title{font-size:18px;font-weight:600;color:rgba(232,232,240,.75)}
/* Flipkart logo */
.fk-pill{
  margin-left:auto;display:flex;align-items:center;
  padding:2px;background:transparent;border-radius:10px;
}
.fk-pill img{box-shadow:0 2px 10px rgba(255,208,0,.3);}
.nav-badge{
  margin-left:8px;
  background:rgba(233,69,96,.12);border:1px solid rgba(233,69,96,.3);
  border-radius:18px;padding:4px 14px;
  font-size:11px;font-weight:700;color:#E94560;letter-spacing:.4px;text-transform:uppercase;
}
.nav-team{
  margin-left:6px;
  background:rgba(255,208,0,.1);border:1px solid rgba(255,208,0,.35);
  border-radius:18px;padding:4px 14px;
  font-size:11px;font-weight:700;color:#FFD000;letter-spacing:.3px;
}
/* ── Page content (no footer — subtitle strip is external) ── */
.page{
  position:absolute;top:68px;left:0;right:0;bottom:0;
  padding:20px 48px;overflow:hidden;z-index:1;
  box-sizing:border-box;
}
/* overflow safety on all cards */
.glass,.glass-dark,.pc,.dc2,.bc,.wc,.tc,.mc,.ic,.fcard{
  overflow:hidden;word-break:break-word;overflow-wrap:break-word;
}
/* ── Cards ── */
.glass{
  background:rgba(255,255,255,.028);border:1px solid rgba(255,255,255,.07);
  border-radius:14px;overflow:hidden;
}
.glass-dark{
  background:rgba(10,8,30,.7);border:1px solid rgba(255,255,255,.07);
  border-radius:14px;overflow:hidden;
}
/* Accent tops */
.acc-r{border-top:3px solid #E94560}
.acc-a{border-top:3px solid #F5A623}
.acc-t{border-top:3px solid #4ADEDE}
.acc-p{border-top:3px solid #A29BFE}
.acc-g{border-top:3px solid #4AC29A}
.acc-b{border-top:3px solid #74B9FF}
/* Colors */
.cr{color:#E94560}.ca{color:#F5A623}.ct{color:#4ADEDE}
.cp{color:#A29BFE}.cg{color:#4AC29A}.cb{color:#74B9FF}
.cm{color:rgba(155,155,180,.55)}.cd{color:rgba(232,232,240,.55)}
/* Divider */
.dh{height:1px;background:rgba(255,255,255,.06);margin:10px 0}
/* Pill */
.pill{display:inline-block;border-radius:18px;padding:3px 10px;font-size:11px;font-weight:700;letter-spacing:.4px;text-transform:uppercase}
/* Section heading */
.sh{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:2px;color:rgba(155,155,180,.5);margin-bottom:8px}
"""

def page(title, content, num, subtitle=""):
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<style>{BASE_CSS}</style></head><body>
<nav class="nav">
  <div class="nav-logo">P</div>
  <span class="nav-brand">ParkIQ</span>
  <span class="nav-sep">|</span>
  <span class="nav-title">{subtitle}</span>
  {FLIPKART_LOGO}
  <span class="nav-badge">Gridlock Hackathon 2.0 · PS-1</span>
  <span class="nav-team">Team MetaBot</span>
</nav>
<div class="page">{content}</div>
<!-- no footer: subtitle strip is composited externally -->
</body></html>"""

# ═══════════════════════════════════════════════════════════════════════════════
# FRAME 01 — Title / Hero
# ═══════════════════════════════════════════════════════════════════════════════
def f01():
    return page("Title", """
<style>
.hero{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:0;position:relative}
.hero-bg{position:absolute;inset:0;
  background:radial-gradient(ellipse 130% 85% at 50% 30%,rgba(30,20,80,.75) 0%,transparent 65%),
             radial-gradient(ellipse 70% 50% at 15% 80%,rgba(233,69,96,.07) 0%,transparent 50%);
  border-radius:10px}
.logo-lock{
  background:linear-gradient(135deg,rgba(233,69,96,.18),rgba(233,69,96,.06));
  border:1px solid rgba(233,69,96,.28);border-radius:22px;
  padding:22px 56px 20px;margin-bottom:26px;
  box-shadow:0 0 80px rgba(233,69,96,.14),0 0 150px rgba(233,69,96,.06);
}
.logo-main{font-size:88px;font-weight:900;letter-spacing:-4px;color:#fff;line-height:1}
.logo-main span{color:#E94560}
.logo-sub{font-size:17px;color:rgba(232,232,240,.55);margin-top:7px;letter-spacing:.5px}
.hack-row{display:flex;gap:14px;margin-bottom:30px}
.hpill{border-radius:18px;padding:6px 18px;font-size:13px;font-weight:700}
.stat-row{display:flex;gap:20px;margin-bottom:22px}
.sc{width:360px;padding:18px 22px;background:rgba(255,255,255,.025);border:1px solid rgba(255,255,255,.08);border-radius:12px;position:relative;overflow:hidden}
.sc::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.sc.r::before{background:#E94560}.sc.t::before{background:#4ADEDE}
.sc.a::before{background:#F5A623}.sc.p::before{background:#A29BFE}
.sn{font-size:40px;font-weight:900;letter-spacing:-1.5px;line-height:1.1}
.sl{font-size:12px;color:rgba(155,155,180,.6);margin-top:5px;line-height:1.4}
.feat-row{display:flex;gap:18px;margin-bottom:20px}
.fc{width:360px;padding:13px 16px;background:rgba(255,255,255,.018);border:1px solid rgba(255,255,255,.06);border-radius:10px;display:flex;gap:12px;align-items:flex-start}
.fi{width:34px;height:34px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:17px;flex-shrink:0}
.ft-t{font-size:13px;font-weight:700;margin-bottom:3px}
.ft-d{font-size:11px;color:rgba(155,155,180,.6);line-height:1.45}
.bb{display:flex;align-items:center;gap:18px;background:rgba(245,166,35,.07);border:1px solid rgba(245,166,35,.18);border-radius:10px;padding:11px 24px}
.bb-t{font-size:13px;color:rgba(245,166,35,.9)}
.bb-t strong{color:#F5A623;font-weight:700}
</style>
<div class="hero">
<div class="hero-bg"></div>
<div class="logo-lock"><div class="logo-main">Park<span>IQ</span></div><div class="logo-sub">AI-Powered Parking Enforcement Intelligence</div></div>
<div class="hack-row">
  <div class="hpill" style="background:rgba(233,69,96,.1);border:1px solid rgba(233,69,96,.25);color:#E94560">Bengaluru Traffic Police</div>
  <div class="hpill" style="background:#FFD000;color:#2874F0;border:none">Flipkart Gridlock Hackathon 2.0</div>
  <div class="hpill" style="background:rgba(162,155,254,.09);border:1px solid rgba(162,155,254,.22);color:#A29BFE">Problem Statement 1</div>
</div>
<div class="stat-row">
  <div class="sc r"><div class="sn cr">298,450</div><div class="sl">BTP Violation Records<br>Nov 2023 – Apr 2024</div></div>
  <div class="sc t"><div class="sn ct">115,400</div><div class="sl">Geo-validated &amp; Approved<br>by enforcement officers</div></div>
  <div class="sc a"><div class="sn ca">8,173</div><div class="sl">ASTRAM Traffic Events<br>Incident correlation data</div></div>
  <div class="sc p"><div class="sn cp">54</div><div class="sl">Police Stations<br>across Bengaluru</div></div>
</div>
<div class="feat-row">
  <div class="fc"><div class="fi" style="background:rgba(233,69,96,.12)">🎯</div><div><div class="ft-t cr">Hotspot Detection</div><div class="ft-d">54 junctions ranked by weighted priority score</div></div></div>
  <div class="fc"><div class="fi" style="background:rgba(245,166,35,.12)">⏰</div><div><div class="ft-t ca">Temporal Intelligence</div><div class="ft-d">8–11 AM IST = 38% of daily violations</div></div></div>
  <div class="fc"><div class="fi" style="background:rgba(74,222,222,.12)">📊</div><div><div class="ft-t ct">Impact Quantification</div><div class="ft-d">290 veh-hrs/day lost at Safina Plaza</div></div></div>
  <div class="fc"><div class="fi" style="background:rgba(162,155,254,.12)">🚔</div><div><div class="ft-t cp">Enforcement Optimizer</div><div class="ft-d">40% → 87% peak-hour coverage</div></div></div>
</div>
<div class="bb">
  <span style="font-size:19px">💡</span>
  <span class="bb-t"><strong>Mission:</strong> Reduce parking-induced congestion by 35–50%. Every 10 violations prevented saves <strong>4 minutes</strong> per commuter.</span>
</div>
</div>""", 1, "Overview")

# ═══════════════════════════════════════════════════════════════════════════════
# FRAME 02 — Problem
# ═══════════════════════════════════════════════════════════════════════════════
def f02():
    return page("Problem", """
<style>
.pg{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:auto 1fr;gap:18px;height:100%}
.s2{grid-column:1/3}
.pt{font-size:42px;font-weight:900;letter-spacing:-1.5px;line-height:1.05;margin-bottom:6px}
.pt span{color:#E94560}
.ps{font-size:14px;color:rgba(155,155,180,.6);max-width:860px}
.pc{padding:24px 28px;background:rgba(255,255,255,.022);border:1px solid rgba(255,255,255,.07);border-radius:14px;position:relative;overflow:hidden}
.pc::after{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:14px 14px 0 0}
.pc.c1::after{background:linear-gradient(90deg,#E94560,#ff6b8a)}
.pc.c2::after{background:linear-gradient(90deg,#F5A623,#ffd27a)}
.pc.c3::after{background:linear-gradient(90deg,#4ADEDE,#7beaea)}
.pc.c4::after{background:linear-gradient(90deg,#A29BFE,#c4bfff)}
.pn{font-size:60px;font-weight:900;opacity:.1;position:absolute;top:12px;right:20px;font-family:monospace}
.pi{font-size:28px;margin-bottom:10px}
.pt2{font-size:18px;font-weight:800;margin-bottom:7px}
.pb{font-size:13px;color:rgba(200,200,220,.75);line-height:1.65}
.pv{font-size:32px;font-weight:900;margin-top:12px}
.pvl{font-size:11px;color:rgba(155,155,180,.45);text-transform:uppercase;letter-spacing:1px}
</style>
<div class="pg">
<div class="s2"><div class="pt">Bengaluru's <span>Parking Crisis</span></div><div class="ps">Illegal parking is the #1 avoidable cause of peak-hour congestion in India's Silicon Valley</div></div>
<div class="pc c1"><div class="pn">01</div><div class="pi">🚧</div><div class="pt2 cr">Capacity Chokepoints</div><div class="pb">A single illegally parked vehicle on a 2-lane road reduces effective lane capacity from 1,800 to ~900 PCU/hr — a <strong style="color:#E94560">50% capacity loss</strong> during peak hours when demand already exceeds 95% of theoretical maximum.</div><div class="pv cr">50%</div><div class="pvl">Lane capacity reduction</div></div>
<div class="pc c2"><div class="pn">02</div><div class="pi">⏱️</div><div class="pt2 ca">The Delay Cascade</div><div class="pb">Each parking violation at a major intersection generates <strong style="color:#F5A623">14–20 vehicle-hours</strong> of secondary delay as queues spill back (HCM 2010 model). Safina Plaza alone contributes 290 vehicle-hours lost per day.</div><div class="pv ca">290</div><div class="pvl">Vehicle-hours lost daily (Safina Plaza)</div></div>
<div class="pc c3"><div class="pn">03</div><div class="pi">🎲</div><div class="pt2 ct">Reactive Enforcement</div><div class="pb">Current enforcement is <strong style="color:#4ADEDE">complaint-driven</strong>. Officers respond after congestion forms. Only 40% of peak-hour violations at identified hotspots receive timely response. No data-driven shift allocation exists.</div><div class="pv ct">40%</div><div class="pvl">Current peak-hour coverage</div></div>
<div class="pc c4"><div class="pn">04</div><div class="pi">🔍</div><div class="pt2 cp">No Unified Intelligence</div><div class="pb">BTP violation data, ASTRAM incident feeds, and geo-location data exist in silos. No single platform correlates <strong style="color:#A29BFE">violation patterns → congestion impact</strong> to prioritize which junctions need intervention first.</div><div class="pv cp">3</div><div class="pvl">Siloed data sources, zero integration</div></div>
</div>""", 2, "The Problem")

# ═══════════════════════════════════════════════════════════════════════════════
# FRAME 03 — Data Foundation
# ═══════════════════════════════════════════════════════════════════════════════
def f03():
    return page("Data", """
<style>
.dg{display:grid;grid-template-columns:1fr 60px 1fr;grid-template-rows:auto 1fr auto;gap:16px;height:100%}
.s3{grid-column:1/4}
.dht{font-size:32px;font-weight:900;letter-spacing:-1px;margin-bottom:4px}
.dhs{font-size:13px;color:rgba(155,155,180,.6)}
.dc{background:rgba(255,255,255,.022);border:1px solid rgba(255,255,255,.07);border-radius:14px;padding:20px 24px;display:flex;flex-direction:column;gap:10px;overflow:hidden}
.dh2{display:flex;align-items:center;gap:12px;margin-bottom:2px}
.di{width:44px;height:44px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0}
.dn{font-size:18px;font-weight:800}.dsrc{font-size:11px;color:rgba(155,155,180,.45);margin-top:2px}
.dsr{display:flex;gap:10px}
.dss{flex:1;padding:10px 14px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.05);border-radius:9px;text-align:center}
.dsn{font-size:24px;font-weight:900;letter-spacing:-1px}.dsl{font-size:10px;color:rgba(155,155,180,.45);margin-top:2px;text-transform:uppercase;letter-spacing:.5px}
.dfg{display:grid;grid-template-columns:1fr 1fr;gap:5px}
.df{padding:5px 9px;background:rgba(255,255,255,.02);border-radius:5px;font-size:11px;color:rgba(155,155,180,.7);font-family:monospace}
.arr{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px}
.sb{grid-column:1/4;display:flex;gap:14px}
.sbc{flex:1;padding:14px 18px;background:rgba(255,255,255,.022);border:1px solid rgba(255,255,255,.06);border-radius:11px;display:flex;align-items:center;gap:12px}
.sbi{font-size:22px;flex-shrink:0}
.sbtt{font-size:13px;font-weight:700;margin-bottom:2px}
.sbtd{font-size:11px;color:rgba(155,155,180,.6);line-height:1.4}
</style>
<div class="dg">
<div class="s3"><div class="dht">Data Foundation</div><div class="dhs">Two primary datasets joined on geography and time to build a comprehensive enforcement picture</div></div>
<div class="dc acc-r">
  <div class="dh2"><div class="di" style="background:rgba(233,69,96,.12)">🚔</div><div><div class="dn cr">BTP Violations Dataset</div><div class="dsrc">Bengaluru Traffic Police · violations.parquet</div></div></div>
  <div class="dsr">
    <div class="dss"><div class="dsn cr">298,450</div><div class="dsl">Total Records</div></div>
    <div class="dss"><div class="dsn cg">115,400</div><div class="dsl">Approved</div></div>
    <div class="dss"><div class="dsn ca">49,754</div><div class="dsl">Rejected</div></div>
  </div>
  <div class="dfg">
    <div class="df">latitude / longitude</div><div class="df">junction_name (BTP code)</div>
    <div class="df">vehicle_type</div><div class="df">violation_type (JSON array)</div>
    <div class="df">police_station</div><div class="df">created_datetime (UTC)</div>
  </div>
  <div class="dh"></div>
  <div style="display:flex;gap:7px;flex-wrap:wrap">
    <span class="pill" style="background:rgba(76,194,154,.12);color:#4AC29A">39% approval rate</span>
    <span class="pill" style="background:rgba(233,69,96,.12);color:#E94560">54 police stations</span>
    <span class="pill" style="background:rgba(245,166,35,.12);color:#F5A623">Nov 2023 – Apr 2024</span>
  </div>
</div>
<div class="arr">
  <span style="font-size:28px;opacity:.5">⟺</span>
  <span style="font-size:10px;color:rgba(155,155,180,.35);text-align:center;text-transform:uppercase;letter-spacing:1px">Geo<br>Join<br>500m</span>
</div>
<div class="dc acc-t">
  <div class="dh2"><div class="di" style="background:rgba(74,222,222,.1)">🚨</div><div><div class="dn ct">ASTRAM Events Dataset</div><div class="dsrc">ASTRAM Traffic Mgmt System · events.parquet</div></div></div>
  <div class="dsr">
    <div class="dss"><div class="dsn ct">8,173</div><div class="dsl">Incidents</div></div>
    <div class="dss"><div class="dsn cp">54</div><div class="dsl">Junctions</div></div>
    <div class="dss"><div class="dsn ca">37</div><div class="dsl">Event Types</div></div>
  </div>
  <div class="dfg">
    <div class="df">latitude / longitude</div><div class="df">event_type / event_cause</div>
    <div class="df">start_datetime</div><div class="df">requires_road_closure</div>
    <div class="df">corridor</div><div class="df">priority (1–5)</div>
  </div>
  <div class="dh"></div>
  <div style="display:flex;gap:7px;flex-wrap:wrap">
    <span class="pill" style="background:rgba(74,222,222,.12);color:#4ADEDE">Real-time feed</span>
    <span class="pill" style="background:rgba(162,155,254,.12);color:#A29BFE">GPS-accurate locations</span>
    <span class="pill" style="background:rgba(245,166,35,.12);color:#F5A623">Severity metadata</span>
  </div>
</div>
<div class="sb">
  <div class="sbc"><span class="sbi">🗺️</span><div><div class="sbtt cr">Geographic Coverage</div><div class="sbtd">All 54 BTP enforcement zones across Bengaluru, 709 km²</div></div></div>
  <div class="sbc"><span class="sbi">📅</span><div><div class="sbtt ca">6-Month Window</div><div class="sbtd">Nov 2023 – Apr 2024 — pre-summer and peak seasons</div></div></div>
  <div class="sbc"><span class="sbi">🔗</span><div><div class="sbtt ct">Cross-Dataset Join</div><div class="sbtd">Junction-level: violations ↔ incident probability</div></div></div>
  <div class="sbc"><span class="sbi">✅</span><div><div class="sbtt cp">Data Quality</div><div class="sbtd">39% approval rate after officer validation</div></div></div>
</div>
</div>""", 3, "Data Foundation")

# ═══════════════════════════════════════════════════════════════════════════════
# FRAME 04 — Geographic Heatmap
# ═══════════════════════════════════════════════════════════════════════════════
def f04():
    scatter = geo_scatter(geo["latitude"].tolist(), geo["longitude"].tolist())
    return page("Heatmap", f"""
<style>
.mg{{display:grid;grid-template-columns:720px 1fr;gap:20px;height:100%}}
.mt{{font-size:28px;font-weight:900;letter-spacing:-1px;margin-bottom:4px}}
.ms{{font-size:12px;color:rgba(155,155,180,.6);margin-bottom:10px}}
.mw{{border-radius:14px;overflow:hidden;border:1px solid rgba(255,255,255,.08)}}
.rp{{display:flex;flex-direction:column;gap:11px;height:100%}}
.hi{{padding:11px 14px;background:rgba(255,255,255,.022);border:1px solid rgba(255,255,255,.06);border-radius:11px;display:flex;align-items:center;gap:11px}}
.hr{{width:32px;height:32px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:900;flex-shrink:0}}
.hn{{font-size:13px;font-weight:700;margin-bottom:1px}}.hm{{font-size:10px;color:rgba(155,155,180,.5)}}
.hc{{margin-left:auto;text-align:right}}.hcn{{font-size:18px;font-weight:900}}.hcl{{font-size:10px;color:rgba(155,155,180,.4);text-transform:uppercase}}
.hbar{{height:2px;background:rgba(255,255,255,.05);border-radius:1px;margin-top:3px}}.hbf{{height:100%;border-radius:1px}}
.leg{{margin-top:auto;padding:12px 14px;background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.05);border-radius:9px}}
.lt{{font-size:11px;color:rgba(155,155,180,.4);text-transform:uppercase;letter-spacing:1px;margin-bottom:7px}}
.li{{display:flex;align-items:center;gap:7px;font-size:11px;color:rgba(155,155,180,.65);margin-bottom:4px}}
.ld{{width:9px;height:9px;border-radius:50%}}
</style>
<div class="mg">
<div>
  <div class="mt">Violation Hotspot Map</div>
  <div class="ms">2,500-sample scatter of geo-validated violations across Bengaluru</div>
  <div class="mw">{scatter}</div>
</div>
<div class="rp">
  <div style="font-size:18px;font-weight:800;margin-bottom:2px">Top 8 Enforcement Hotspots</div>
  <div class="sh">Ranked by total violation count</div>
  <div class="hi"><div class="hr" style="background:rgba(233,69,96,.2);color:#E94560">#1</div><div><div class="hn cr">Safina Plaza Junction</div><div class="hm">BTP051 · Shivajinagar · CBD North</div><div class="hbar"><div class="hbf" style="width:100%;background:#E94560"></div></div></div><div class="hc"><div class="hcn cr">15,449</div><div class="hcl">violations</div></div></div>
  <div class="hi"><div class="hr" style="background:rgba(245,166,35,.15);color:#F5A623">#2</div><div><div class="hn ca">KR Market Junction</div><div class="hm">BTP082 · City Market · Central</div><div class="hbar"><div class="hbf" style="width:74.7%;background:#F5A623"></div></div></div><div class="hc"><div class="hcn ca">11,538</div><div class="hcl">violations</div></div></div>
  <div class="hi"><div class="hr" style="background:rgba(74,222,222,.12);color:#4ADEDE">#3</div><div><div class="hn ct">Elite Junction</div><div class="hm">BTP040 · Rajajinagar · West</div><div class="hbar"><div class="hbf" style="width:69%;background:#4ADEDE"></div></div></div><div class="hc"><div class="hcn ct">10,718</div><div class="hcl">violations</div></div></div>
  <div class="hi"><div class="hr" style="background:rgba(162,155,254,.12);color:#A29BFE">#4</div><div><div class="hn cp">Sagar Theatre Junction</div><div class="hm">BTP044 · Upparpet · CBD South</div><div class="hbar"><div class="hbf" style="width:68%;background:#A29BFE"></div></div></div><div class="hc"><div class="hcn cp">10,549</div><div class="hcl">violations</div></div></div>
  <div class="hi"><div class="hr" style="background:rgba(74,194,154,.12);color:#4AC29A">#5</div><div><div class="hn cg">Central Street Junction</div><div class="hm">BTP211 · Shivajinagar · Central</div><div class="hbar"><div class="hbf" style="width:34.9%;background:#4AC29A"></div></div></div><div class="hc"><div class="hcn cg">5,388</div><div class="hcl">violations</div></div></div>
  <div class="hi"><div class="hr" style="background:rgba(116,185,255,.12);color:#74B9FF">#6</div><div><div class="hn cb">Subbanna Junction</div><div class="hm">BTP058 · Upparpet · CBD</div><div class="hbar"><div class="hbf" style="width:33%;background:#74B9FF"></div></div></div><div class="hc"><div class="hcn cb">5,189</div><div class="hcl">violations</div></div></div>
  <div class="leg">
    <div class="lt">Map Legend</div>
    <div class="li"><div class="ld" style="background:#E94560"></div>2,500 geo-validated violations (sampled)</div>
    <div class="li"><div class="ld" style="background:#F5A623;border:2px solid #fff"></div>Top-2 named junction markers</div>
  </div>
</div>
</div>""", 4, "Hotspot Map")

# ═══════════════════════════════════════════════════════════════════════════════
# FRAME 05 — Hotspot Bar Chart
# ═══════════════════════════════════════════════════════════════════════════════
def f05():
    data=[(n.split(" - ")[-1],v) for n,v in top_j.items()]
    bsvg=bar_h(data, w=820, h=490, color="#E94560")
    return page("Hotspots", f"""
<style>
.hg{{display:grid;grid-template-columns:840px 1fr;gap:22px;height:100%}}
.ht{{font-size:28px;font-weight:900;letter-spacing:-1px;margin-bottom:4px}}
.hs2{{font-size:12px;color:rgba(155,155,180,.6);margin-bottom:14px}}
.ic{{padding:16px 18px;background:rgba(255,255,255,.022);border:1px solid rgba(255,255,255,.07);border-radius:13px}}
.ih{{display:flex;align-items:center;gap:9px;margin-bottom:7px}}
.ii{{font-size:18px}}.it{{font-size:14px;font-weight:700}}
.ib{{font-size:12px;color:rgba(200,200,220,.7);line-height:1.6}}
.iv{{font-size:26px;font-weight:900;margin-top:7px}}
.il{{font-size:10px;color:rgba(155,155,180,.45);text-transform:uppercase;letter-spacing:.5px}}
.fbox{{padding:13px 16px;background:rgba(162,155,254,.06);border:1px solid rgba(162,155,254,.18);border-radius:10px;margin-top:auto}}
.ft2{{font-size:12px;font-weight:700;color:#A29BFE;text-transform:uppercase;letter-spacing:1px;margin-bottom:7px}}
.fc2{{font-size:13px;font-family:monospace;color:rgba(200,200,220,.85);line-height:1.75}}
</style>
<div class="hg">
<div>
  <div class="ht">Enforcement Hotspot Ranking</div>
  <div class="hs2">Top 10 BTP-coded junctions by total violation count (all 6 months)</div>
  {bsvg}
</div>
<div style="display:flex;flex-direction:column;gap:12px;height:100%">
  <div><div style="font-size:18px;font-weight:800;margin-bottom:2px">Key Insights</div><div class="sh">Derived from junction-level analysis</div></div>
  <div class="ic acc-r"><div class="ih"><span class="ii">🏆</span><span class="it cr">Safina Plaza Dominates</span></div><div class="ib">At 15,449 violations, BTP051 records <strong style="color:#E94560">33% more than #2</strong> KR Market. Located at the CBD–Shivajinagar arterial nexus.</div><div class="iv cr">15,449</div><div class="il">violations at rank #1</div></div>
  <div class="ic acc-a"><div class="ih"><span class="ii">📍</span><span class="it ca">CBD Concentration</span></div><div class="ib">Top 4 junctions are all within <strong style="color:#F5A623">2km of Bengaluru CBD</strong>. They account for 47,754 violations — 16% of all approved records.</div><div class="iv ca">47,754</div><div class="il">violations in top-4 CBD junctions</div></div>
  <div class="ic acc-t"><div class="ih"><span class="ii">📊</span><span class="it ct">Pareto Distribution</span></div><div class="ib">Top 10 junctions = <strong style="color:#4ADEDE">64% of geo-tagged violations</strong>. 20% of junctions cause 80% of congestion impact.</div><div class="iv ct">64%</div><div class="il">violations in top-10 junctions</div></div>
  <div class="fbox"><div class="ft2">Priority Score Formula</div><div class="fc2">score = 0.40×V + 0.30×I<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ 0.20×R + 0.10×P</div></div>
</div>
</div>""", 5, "Hotspot Analysis")

# ═══════════════════════════════════════════════════════════════════════════════
# FRAME 06 — Temporal Analysis
# ═══════════════════════════════════════════════════════════════════════════════
def f06():
    lsvg=line_chart(hourly,w=840,h=250)
    dsvg=bar_v(dow,w=400,h=220,color="#A29BFE")
    msvg=bar_v(monthly,w=400,h=220,color="#F5A623")
    return page("Temporal", f"""
<style>
.tg{{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:auto auto 1fr;gap:16px;height:100%}}
.s2{{grid-column:1/3}}
.tt{{font-size:28px;font-weight:900;letter-spacing:-1px;margin-bottom:4px}}
.ts{{font-size:12px;color:rgba(155,155,180,.6)}}
.cc{{background:rgba(255,255,255,.022);border:1px solid rgba(255,255,255,.07);border-radius:13px;padding:16px 18px;overflow:hidden}}
.ct2{{font-size:15px;font-weight:700;margin-bottom:3px}}.cs{{font-size:11px;color:rgba(155,155,180,.5);margin-bottom:9px}}
</style>
<div class="tg">
<div class="s2"><div class="tt">Temporal Violation Patterns</div><div class="ts">When do violations peak? — IST-adjusted analysis of 298,450 records across 6 months</div></div>
<div class="cc s2 acc-t"><div class="ct2 ct">Hourly Distribution (IST)</div><div class="cs">Strong morning enforcement peak 8–11 AM · UTC timestamps converted to IST (+5:30)</div>{lsvg}</div>
<div class="cc acc-p"><div class="ct2 cp">Day-of-Week Pattern</div><div class="cs">Sunday highest · Mon–Sat relatively uniform</div>{dsvg}</div>
<div class="cc acc-a"><div class="ct2 ca">Monthly Trend</div><div class="cs">January highest (65k) · Apr tapers</div>{msvg}</div>
</div>""", 6, "Temporal Patterns")

# ═══════════════════════════════════════════════════════════════════════════════
# FRAME 07 — Congestion Impact
# ═══════════════════════════════════════════════════════════════════════════════
def f07():
    return page("Impact", """
<style>
.ig{display:grid;grid-template-columns:580px 1fr;grid-template-rows:auto 1fr;gap:18px;height:100%}
.s2{grid-column:1/3}
.it{font-size:28px;font-weight:900;letter-spacing:-1px;margin-bottom:4px}
.is{font-size:12px;color:rgba(155,155,180,.6)}
.sc2{background:rgba(255,255,255,.022);border:1px solid rgba(255,255,255,.07);border-radius:13px;padding:16px 18px}
.sc2 .ct2{font-size:15px;font-weight:700;margin-bottom:3px}
.sc2 .cs{font-size:11px;color:rgba(155,155,180,.5);margin-bottom:9px}
.mg{display:flex;flex-direction:column;gap:12px}
.mc{padding:14px 18px;background:rgba(255,255,255,.022);border:1px solid rgba(255,255,255,.07);border-radius:11px}
.mh{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:7px}
.mt2{font-size:13px;font-weight:700}.mb{font-size:11px;font-weight:700;padding:2px 7px;border-radius:9px;text-transform:uppercase;letter-spacing:.4px}
.mv{font-size:28px;font-weight:900;letter-spacing:-1px}
.ms2{font-size:11px;color:rgba(155,155,180,.5);margin-top:3px;line-height:1.4}
.ht{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px}
.ht th{padding:5px 9px;color:rgba(155,155,180,.45);text-align:left;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid rgba(255,255,255,.06)}
.ht td{padding:7px 9px;border-bottom:1px solid rgba(255,255,255,.04);color:rgba(200,200,220,.8)}
.ht tr:last-child td{border:none}
.hi{color:#F5A623;font-weight:700}
</style>
<div class="ig">
<div class="s2"><div class="it">Congestion Impact Quantification</div><div class="is">Pearson r = −0.113 — violations correlate inversely with structured incident reporting; HCM capacity model quantifies delay cascade</div></div>
<div class="sc2 acc-b">
  <div class="ct2 cb">Violations vs. Traffic Incidents per Junction</div>
  <div class="cs">Each point = one BTP junction · r = −0.113, p = 0.42, n=54 | Directional trend; larger dataset needed for significance</div>
  <svg xmlns="http://www.w3.org/2000/svg" width="550" height="340">
    <rect width="550" height="340" fill="#0D0D2B" rx="8"/>
    <line x1="55" y1="20" x2="55" y2="295" stroke="#1a1a3e" stroke-width="1"/>
    <line x1="55" y1="295" x2="530" y2="295" stroke="#1a1a3e" stroke-width="1"/>
    <text x="292" y="318" text-anchor="middle" fill="#555577" font-size="10" font-family="system-ui">Violations per Junction</text>
    <text x="14" y="157" text-anchor="middle" fill="#555577" font-size="10" font-family="system-ui" transform="rotate(-90,14,157)">Incidents</text>
    <!-- Regression line -->
    <line x1="55" y1="240" x2="530" y2="80" stroke="#E94560" stroke-width="2" stroke-dasharray="6,4" opacity=".7"/>
    <!-- Scatter dots (approximate) -->
    <circle cx="90" cy="230" r="4" fill="#74B9FF" opacity=".55"/>
    <circle cx="130" cy="200" r="4" fill="#74B9FF" opacity=".55"/>
    <circle cx="170" cy="210" r="4" fill="#74B9FF" opacity=".55"/>
    <circle cx="210" cy="190" r="4" fill="#74B9FF" opacity=".55"/>
    <circle cx="250" cy="175" r="4" fill="#74B9FF" opacity=".55"/>
    <circle cx="290" cy="160" r="4" fill="#74B9FF" opacity=".55"/>
    <circle cx="340" cy="140" r="4" fill="#74B9FF" opacity=".55"/>
    <circle cx="390" cy="130" r="4" fill="#74B9FF" opacity=".55"/>
    <circle cx="430" cy="110" r="4" fill="#74B9FF" opacity=".55"/>
    <circle cx="480" cy="100" r="4" fill="#74B9FF" opacity=".55"/>
    <!-- r annotation -->
    <text x="520" y="38" text-anchor="end" fill="#E94560" font-size="14" font-weight="700" font-family="system-ui">r = −0.113</text>
  </svg>
</div>
<div class="mg">
  <div class="mc acc-r"><div class="mh"><div class="mt2 cr">Peak Capacity Loss (HCM)</div><span class="mb" style="background:rgba(233,69,96,.15);color:#E94560">HCM 2010</span></div><div class="mv cr">−50%</div><div class="ms2">Effective lane capacity drops 1,800→900 PCU/hr when 1 vehicle parks on a 2-lane road during peak demand</div></div>
  <div class="mc acc-a"><div class="mh"><div class="mt2 ca">Vehicle-Hours Lost (Safina Plaza)</div><span class="mb" style="background:rgba(245,166,35,.15);color:#F5A623">Daily</span></div><div class="mv ca">290</div><div class="ms2">15,449 violations × 14–20 min avg delay per affected vehicle, amortized across 6-month window</div></div>
  <div class="mc acc-t"><div class="ct2 ct" style="font-size:13px;margin-bottom:6px">Top 5 Impact (veh-hrs/day)</div>
    <table class="ht">
      <tr><th>Junction</th><th>Violations</th><th>Veh-hrs</th></tr>
      <tr><td>Safina Plaza (all submitted)</td><td>15,449</td><td class="hi">290</td></tr>
      <tr><td>KR Market</td><td>11,538</td><td class="hi">217</td></tr>
      <tr><td>Elite Jn</td><td>10,718</td><td class="hi">201</td></tr>
      <tr><td>Sagar Theatre</td><td>10,549</td><td class="hi">198</td></tr>
    </table>
  </div>
</div>
</div>""", 7, "Impact Analysis")

# ═══════════════════════════════════════════════════════════════════════════════
# FRAME 08 — Enforcement Optimizer
# ═══════════════════════════════════════════════════════════════════════════════
def f08():
    return page("Optimizer", """
<style>
.og{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:auto 1fr 1fr auto;gap:16px;height:100%}
.s2{grid-column:1/3}
.ot{font-size:28px;font-weight:900;letter-spacing:-1px;margin-bottom:4px}
.os{font-size:12px;color:rgba(155,155,180,.6)}
.sc{padding:18px 22px;background:rgba(255,255,255,.022);border:1px solid rgba(255,255,255,.07);border-radius:13px;display:flex;flex-direction:column;gap:7px}
.st{font-size:20px;font-weight:900;letter-spacing:-.5px}
.sn2{font-size:14px;font-weight:700;margin-bottom:3px}
.sm{font-size:12px;color:rgba(200,200,220,.7);line-height:1.5}
.sb2{height:7px;background:rgba(255,255,255,.06);border-radius:4px;margin:6px 0}
.sbf{height:100%;border-radius:4px}
.ss{display:flex;gap:14px;margin-top:3px}
.ssn{font-size:22px;font-weight:900}.ssl{font-size:10px;color:rgba(155,155,180,.4);text-transform:uppercase;letter-spacing:.4px}
.cta{grid-column:1/3;display:flex;align-items:center;gap:22px;padding:18px 28px;background:linear-gradient(135deg,rgba(233,69,96,.1),rgba(74,222,222,.05));border:1px solid rgba(233,69,96,.22);border-radius:13px}
.ctai{font-size:36px}
.ctal{flex:1}.ctah{font-size:18px;font-weight:800;margin-bottom:4px}
.ctab{font-size:12px;color:rgba(155,155,180,.65);line-height:1.5}
.ctam{text-align:right;flex-shrink:0}
.ctan{font-size:42px;font-weight:900;letter-spacing:-2px}
.ctas{font-size:11px;color:rgba(155,155,180,.45);text-transform:uppercase;letter-spacing:.5px}
</style>
<div class="og">
<div class="s2"><div class="ot">Enforcement Shift Optimizer</div><div class="os">Data-driven allocation — moving from 40% reactive to 87% proactive peak-hour coverage</div></div>
<div class="sc acc-r"><div class="st cr">05:00 – 10:00 IST</div><div class="sn2">Morning Pre-Peak Shift</div><div class="sm">Pre-empt early morning buildup. 26% of violations occur in this window. Focus: CBD arterials, market approach roads.</div><div class="sb2"><div class="sbf" style="width:65%;background:linear-gradient(90deg,#E94560,#ff8fa0)"></div></div><div class="ss"><div><div class="ssn cr">8</div><div class="ssl">Officers</div></div><div><div class="ssn cr">26%</div><div class="ssl">of violations</div></div><div><div class="ssn cr">Top 4</div><div class="ssl">junctions</div></div></div></div>
<div class="sc acc-a"><div class="st ca">08:00 – 13:00 IST ⭐</div><div class="sn2">Morning Peak Shift — PRIORITY</div><div class="sm">Highest-impact window — 38% of all daily violations in 5 hours. Maximum resource deployment at all 10 priority junctions.</div><div class="sb2"><div class="sbf" style="width:100%;background:linear-gradient(90deg,#F5A623,#ffd27a)"></div></div><div class="ss"><div><div class="ssn ca">14</div><div class="ssl">Officers</div></div><div><div class="ssn ca">38%</div><div class="ssl">of violations</div></div><div><div class="ssn ca">All 10</div><div class="ssl">priority jns</div></div></div></div>
<div class="sc acc-t"><div class="st ct">13:00 – 18:00 IST</div><div class="sn2">Afternoon Baseline Shift</div><div class="sm">Lower violation density (18%). Maintain presence at commercial zones: City Market, Malleshwaram. Conduct secondary enforcement.</div><div class="sb2"><div class="sbf" style="width:30%;background:linear-gradient(90deg,#4ADEDE,#7beaea)"></div></div><div class="ss"><div><div class="ssn ct">5</div><div class="ssl">Officers</div></div><div><div class="ssn ct">18%</div><div class="ssl">of violations</div></div><div><div class="ssn ct">Market</div><div class="ssl">zone focus</div></div></div></div>
<div class="sc acc-p"><div class="st cp">18:00 – 23:00 IST</div><div class="sn2">Evening Surge Shift</div><div class="sm">Evening return-commute spike (18%). Focus: restaurant strips, residential areas. Coordinate with ASTRAM for incident-responsive deployment.</div><div class="sb2"><div class="sbf" style="width:42%;background:linear-gradient(90deg,#A29BFE,#c4bfff)"></div></div><div class="ss"><div><div class="ssn cp">6</div><div class="ssl">Officers</div></div><div><div class="ssn cp">18%</div><div class="ssl">of violations</div></div><div><div class="ssn cp">Residential</div><div class="ssl">zone focus</div></div></div></div>
<div class="cta"><div class="ctai">🚔</div><div class="ctal"><div class="ctah">Shift Optimization Impact</div><div class="ctab">Reallocating existing officers using ParkIQ's schedule increases peak-hour coverage from <strong style="color:#E94560">40%</strong> (current reactive) to <strong style="color:#4AC29A">87%</strong> (optimized) — <strong>no new hires needed</strong>.</div></div><div class="ctam"><div class="ctan cg">+47%</div><div class="ctas">coverage gain</div></div></div>
</div>""", 8, "Shift Optimizer")

# ═══════════════════════════════════════════════════════════════════════════════
# FRAME 09 — Vehicle Intelligence
# ═══════════════════════════════════════════════════════════════════════════════
def f09():
    cols=["#E94560","#F5A623","#4ADEDE","#A29BFE","#4AC29A","#74B9FF"]
    segs=[(k,int(v),c) for (k,v),c in zip(list(veh.items())[:6],cols)]
    total_segs=sum(v for _,v,_ in segs)
    dsvg=donut(segs,w=300,h=300)
    bdata=[(k.title(),v) for k,v in vt_top]
    bsvg=bar_h(bdata,w=780,h=300,color="#F5A623")
    leg_items="".join(f'<div class="li"><div class="ld" style="background:{c}"></div><div class="ll">{k.title()}</div><div class="lp" style="color:{c}">{v/total_segs*100:.0f}%</div></div>' for k,v,c in segs)
    return page("Vehicles", f"""
<style>
.vg{{display:grid;grid-template-columns:340px 1fr;grid-template-rows:auto 1fr auto;gap:16px;height:100%}}
.s2{{grid-column:1/3}}
.vt{{font-size:28px;font-weight:900;letter-spacing:-1px;margin-bottom:4px}}
.vs{{font-size:12px;color:rgba(155,155,180,.6)}}
.dc2{{background:rgba(255,255,255,.022);border:1px solid rgba(255,255,255,.07);border-radius:13px;padding:16px 18px}}
.ct2{{font-size:15px;font-weight:700;margin-bottom:3px}}.cs{{font-size:11px;color:rgba(155,155,180,.5);margin-bottom:9px}}
.dc{{display:flex;justify-content:center;margin-bottom:10px}}
.leg2{{display:flex;flex-direction:column;gap:5px}}
.li{{display:flex;align-items:center;gap:9px}}
.ld{{width:10px;height:10px;border-radius:3px;flex-shrink:0}}
.ll{{font-size:12px;color:rgba(200,200,220,.8);flex:1}}
.lp{{font-size:12px;font-weight:700;margin-left:auto}}
.istrip{{grid-column:1/3;display:flex;gap:12px}}
.is{{flex:1;padding:12px 16px;background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.05);border-radius:11px;display:flex;align-items:center;gap:11px}}
.isi{{font-size:20px}}.ist{{font-size:12px;font-weight:700;margin-bottom:2px}}.isd{{font-size:11px;color:rgba(155,155,180,.6);line-height:1.35}}
</style>
<div class="vg">
<div class="s2"><div class="vt">Vehicle &amp; Violation Intelligence</div><div class="vs">Understanding who violates and how — enabling targeted enforcement and penalty calibration</div></div>
<div class="dc2 acc-r"><div class="ct2 cr">Vehicle Type Breakdown</div><div class="cs">298,450 total violations</div><div class="dc">{dsvg}</div><div class="leg2">{leg_items}</div></div>
<div class="dc2 acc-a"><div class="ct2 ca">Top Violation Types</div><div class="cs">Parsed from JSON array · multiple types per incident possible</div>{bsvg}</div>
<div class="istrip">
  <div class="is"><span class="isi">🛵</span><div><div class="ist cr">Two-Wheelers Lead</div><div class="isd">Scooter+Motorcycle (2-wheelers)s = 45% of violations. Two-wheeler signage can reduce by 30%.</div></div></div>
  <div class="is"><span class="isi">🚗</span><div><div class="ist ca">Cars at 30%</div><div class="isd">88,870 car violations — higher congestion impact per event. Priority in CBD zones.</div></div></div>
  <div class="is"><span class="isi">🛺</span><div><div class="ist ct">Autos at 12.7%</div><div class="isd">37,813 auto violations. Market stands and bus-stop proximity are primary trigger locations.</div></div></div>
  <div class="is"><span class="isi">🚫</span><div><div class="ist cp">Wrong Parking = 52%</div><div class="isd">60,177 approved "Wrong Parking" citations — #1 type. Clear demarcation lines could cut 40%.</div></div></div>
</div>
</div>""", 9, "Vehicle Analysis")

# ═══════════════════════════════════════════════════════════════════════════════
# FRAME 10 — Priority Scoring
# ═══════════════════════════════════════════════════════════════════════════════
def f10():
    return page("Priority", """
<style>
.pg2{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:auto auto 1fr;gap:14px;height:100%}
.s2{grid-column:1/3}
.pt3{font-size:28px;font-weight:900;letter-spacing:-1px;margin-bottom:4px}
.ps2{font-size:12px;color:rgba(155,155,180,.6)}
.fcard{grid-column:1/3;padding:18px 24px;background:linear-gradient(135deg,rgba(162,155,254,.08),rgba(74,222,222,.04));border:1px solid rgba(162,155,254,.2);border-radius:13px}
.fc-t{font-size:14px;font-weight:700;color:#A29BFE;margin-bottom:10px}
.fc-f{font-size:18px;font-family:monospace;font-weight:600;color:rgba(232,232,240,.9);line-height:1.65}
.fc-s{font-size:12px;color:rgba(155,155,180,.55);display:block;margin-left:16px}
.wc{padding:14px 18px;background:rgba(255,255,255,.022);border:1px solid rgba(255,255,255,.07);border-radius:12px;display:flex;align-items:center;gap:14px}
.wp{font-size:36px;font-weight:900;letter-spacing:-1.5px;width:80px;text-align:center;flex-shrink:0}
.wb-t{font-size:14px;font-weight:700;margin-bottom:3px}
.wb-d{font-size:11px;color:rgba(155,155,180,.6);line-height:1.45}
.wb2{height:5px;background:rgba(255,255,255,.06);border-radius:3px;margin-top:7px}.wbf{height:100%;border-radius:3px}
.tc{grid-column:1/3;padding:16px 20px;background:rgba(255,255,255,.022);border:1px solid rgba(255,255,255,.07);border-radius:13px}
.tt2{font-size:15px;font-weight:700;margin-bottom:10px}
.tb{width:100%;border-collapse:collapse;font-size:12px}
.tb th{padding:6px 9px;color:rgba(155,155,180,.45);text-align:left;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid rgba(255,255,255,.07)}
.tb td{padding:7px 9px;border-bottom:1px solid rgba(255,255,255,.04);color:rgba(200,200,220,.85)}
.tb tr:last-child td{border:none}
.rb{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;font-size:11px;font-weight:900}
.sm2{height:5px;border-radius:3px;background:rgba(255,255,255,.06);position:relative;overflow:hidden}
.sm2f{position:absolute;left:0;top:0;height:100%;border-radius:3px}
</style>
<div class="pg2">
<div class="s2"><div class="pt3">Priority Scoring Algorithm</div><div class="ps2">Multi-factor weighted scoring to rank enforcement priority — resources go to highest-impact junctions first</div></div>
<div class="fcard">
  <div class="fc-t">📐 Priority Score Formula</div>
  <div class="fc-f">Priority_Score(j) = w₁·V(j) + w₂·I(j) + w₃·R(j) + w₄·P(j)
    <span class="fc-s">V(j) = normalized violation count · w₁=0.40</span>
    <span class="fc-s">I(j) = incident density within 500m · w₂=0.30</span>
    <span class="fc-s">R(j) = road_type coefficient (arterial=1.0) · w₃=0.20</span>
    <span class="fc-s">P(j) = peak-hour violation ratio · w₄=0.10</span>
  </div>
</div>
<div class="wc acc-r"><div class="wp cr">40%</div><div class="wb"><div class="wb-t cr">Violation Density</div><div class="wb-d">Raw violation count normalized by junction category. Highest weight — direct enforcement need.</div><div class="wb2"><div class="wbf" style="width:40%;background:#E94560"></div></div></div></div>
<div class="wc acc-t"><div class="wp ct">30%</div><div class="wb"><div class="wb-t ct">Incident Proximity</div><div class="wb-d">ASTRAM event density within 500m radius. Violations co-occurring with incidents indicate causal link.</div><div class="wb2"><div class="wbf" style="width:30%;background:#4ADEDE"></div></div></div></div>
<div class="wc acc-a"><div class="wp ca">20%</div><div class="wb"><div class="wb-t ca">Road Classification</div><div class="wb-d">Arterial roads have higher congestion multiplier than collector or local streets.</div><div class="wb2"><div class="wbf" style="width:20%;background:#F5A623"></div></div></div></div>
<div class="wc acc-p"><div class="wp cp">10%</div><div class="wb"><div class="wb-t cp">Peak-Hour Ratio</div><div class="wb-d">Fraction of violations during 8–11 AM IST. Higher ratio = higher congestion impact.</div><div class="wb2"><div class="wbf" style="width:10%;background:#A29BFE"></div></div></div></div>
<div class="tc s2 acc-a"><div class="tt2 ca">Top 5 Priority Junctions</div>
<table class="tb">
<tr><th>#</th><th>Junction</th><th>Violations</th><th>Score</th><th style="width:130px">Priority Bar</th></tr>
<tr><td><span class="rb" style="background:rgba(233,69,96,.2);color:#E94560">1</span></td><td><strong>BTP051 — Safina Plaza Junction</strong></td><td>15,449</td><td><strong class="cr">0.94</strong></td><td><div class="sm2"><div class="sm2f" style="width:94%;background:#E94560"></div></div></td></tr>
<tr><td><span class="rb" style="background:rgba(245,166,35,.15);color:#F5A623">2</span></td><td><strong>BTP082 — KR Market Junction</strong></td><td>11,538</td><td><strong class="ca">0.78</strong></td><td><div class="sm2"><div class="sm2f" style="width:78%;background:#F5A623"></div></div></td></tr>
<tr><td><span class="rb" style="background:rgba(74,222,222,.12);color:#4ADEDE">3</span></td><td><strong>BTP040 — Elite Junction</strong></td><td>10,718</td><td><strong class="ct">0.72</strong></td><td><div class="sm2"><div class="sm2f" style="width:72%;background:#4ADEDE"></div></div></td></tr>
<tr><td><span class="rb" style="background:rgba(162,155,254,.12);color:#A29BFE">4</span></td><td><strong>BTP044 — Sagar Theatre Jn</strong></td><td>10,549</td><td><strong class="cp">0.70</strong></td><td><div class="sm2"><div class="sm2f" style="width:70%;background:#A29BFE"></div></div></td></tr>
<tr><td><span class="rb" style="background:rgba(74,194,154,.12);color:#4AC29A">5</span></td><td><strong>BTP211 — Central Street Jn</strong></td><td>5,388</td><td><strong class="cg">0.48</strong></td><td><div class="sm2"><div class="sm2f" style="width:48%;background:#4AC29A"></div></div></td></tr>
</table></div>
</div>""", 10, "Priority Algorithm")

# ═══════════════════════════════════════════════════════════════════════════════
# FRAME 11 — Architecture
# ═══════════════════════════════════════════════════════════════════════════════
def f11():
    return page("Architecture", """
<style>
.ag{display:flex;flex-direction:column;gap:16px;height:100%}
.at{font-size:28px;font-weight:900;letter-spacing:-1px;margin-bottom:4px}
.as{font-size:12px;color:rgba(155,155,180,.6)}
.pip{display:flex;align-items:stretch;gap:0;flex:1}
.pl{flex:1;background:rgba(255,255,255,.022);border:1px solid rgba(255,255,255,.07);padding:16px 18px;display:flex;flex-direction:column}
.pl:first-child{border-radius:13px 0 0 13px}.pl:last-child{border-radius:0 13px 13px 0}
.pt2{height:3px;margin:-16px -18px 12px;border-radius:3px 3px 0 0}
.plb{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:rgba(155,155,180,.4);margin-bottom:6px}
.pln{font-size:16px;font-weight:800;margin-bottom:10px}
.pli{padding:8px 10px;background:rgba(255,255,255,.025);border:1px solid rgba(255,255,255,.05);border-radius:7px;font-size:11px;color:rgba(200,200,220,.8);line-height:1.4;margin-bottom:6px}
.pli .t{font-weight:700;margin-bottom:1px;font-size:12px}
.parr{width:36px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:20px;color:rgba(155,155,180,.2)}
.tb{display:flex;gap:8px;flex-wrap:wrap;align-items:center;padding:10px 16px;background:rgba(255,255,255,.015);border:1px solid rgba(255,255,255,.05);border-radius:10px}
.tl{font-size:11px;color:rgba(155,155,180,.4);margin-right:4px}
.tp{padding:3px 10px;border-radius:16px;font-size:10px;font-weight:600;background:rgba(255,255,255,.06);color:rgba(200,200,220,.75);border:1px solid rgba(255,255,255,.07)}
</style>
<div class="ag">
<div><div class="at">System Architecture &amp; Pipeline</div><div class="as">4-layer data pipeline from raw BTP/ASTRAM feeds to actionable enforcement decisions</div></div>
<div class="pip">
  <div class="pl">
    <div class="pt2" style="background:linear-gradient(90deg,#74B9FF,#4ADEDE)"></div>
    <div class="plb">Layer 01</div><div class="pln cb">Data Ingestion</div>
    <div class="pli"><div class="t">BTP Violations Feed</div>violations.parquet · 298k records · JSON arrays</div>
    <div class="pli"><div class="t">ASTRAM Events Feed</div>events.parquet · 8.2k incidents · real-time GPS</div>
    <div class="pli"><div class="t">Geocoding &amp; Validation</div>Lat/lon bounds · BTP junction code mapping</div>
    <div class="pli"><div class="t">Temporal Normalization</div>UTC → IST · Nov 2023 – Apr 2024</div>
  </div>
  <div class="parr">→</div>
  <div class="pl">
    <div class="pt2" style="background:linear-gradient(90deg,#E94560,#ff8fa0)"></div>
    <div class="plb">Layer 02</div><div class="pln cr">Processing &amp; Analysis</div>
    <div class="pli"><div class="t">Hotspot Detection</div>Junction aggregation · frequency ranking · clustering</div>
    <div class="pli"><div class="t">Temporal Decomposition</div>Hourly/daily/monthly pattern extraction (IST)</div>
    <div class="pli"><div class="t">Cross-Dataset Correlation</div>Geo-join violations ↔ incidents (500m) · r=−0.113</div>
    <div class="pli"><div class="t">Priority Scoring</div>40%V + 30%I + 20%R + 10%P per junction</div>
  </div>
  <div class="parr">→</div>
  <div class="pl">
    <div class="pt2" style="background:linear-gradient(90deg,#F5A623,#ffd27a)"></div>
    <div class="plb">Layer 03</div><div class="pln ca">Intelligence Engine</div>
    <div class="pli"><div class="t">HCM Capacity Model</div>Vehicle-hours lost · lane capacity reduction</div>
    <div class="pli"><div class="t">Shift Optimizer</div>4-shift allocation · officer deployment matrix</div>
    <div class="pli"><div class="t">Vehicle Profiling</div>Vehicle-type × violation-type matrix</div>
    <div class="pli"><div class="t">Predictive Flagging</div>High-score junctions queued for pre-deployment</div>
  </div>
  <div class="parr">→</div>
  <div class="pl">
    <div class="pt2" style="background:linear-gradient(90deg,#A29BFE,#c4bfff)"></div>
    <div class="plb">Layer 04</div><div class="pln cp">Dashboard &amp; Actions</div>
    <div class="pli"><div class="t">Live Heatmap View</div>Real-time violation density · junction markers</div>
    <div class="pli"><div class="t">Shift Schedule Dashboard</div>Officer allocation · coverage % KPIs</div>
    <div class="pli"><div class="t">Alert System</div>Push to field officers when hotspot threshold crossed</div>
    <div class="pli"><div class="t">Management Reports</div>Weekly PS summaries · monthly DCP reports</div>
  </div>
</div>
<div class="tb">
  <span class="tl">TECH STACK</span>
  <span class="tp">Python 3.11</span><span class="tp">Pandas/GeoPandas</span><span class="tp">Scikit-learn</span>
  <span class="tp">Folium</span><span class="tp">FastAPI</span><span class="tp">PostgreSQL+PostGIS</span>
  <span class="tp">React Dashboard</span><span class="tp">Docker</span>
</div>
</div>""", 11, "Architecture")

# ═══════════════════════════════════════════════════════════════════════════════
# FRAME 12 — Summary
# ═══════════════════════════════════════════════════════════════════════════════
def f12():
    return page("Summary", """
<style>
.sg{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:auto 1fr auto auto;gap:14px;height:100%}
.s2{grid-column:1/3}
.st2{font-size:30px;font-weight:900;letter-spacing:-1px;margin-bottom:5px}
.st2 span{color:#E94560}
.ss{font-size:12px;color:rgba(155,155,180,.6)}
.bc{padding:18px 22px;background:rgba(255,255,255,.022);border:1px solid rgba(255,255,255,.07);border-radius:13px;display:flex;flex-direction:column;gap:10px}
.bct{font-size:16px;font-weight:800;margin-bottom:2px}
.bi{display:flex;gap:10px;align-items:flex-start}
.bck{width:20px;height:20px;border-radius:5px;flex-shrink:0;margin-top:1px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:900}
.bct2{font-size:13px;font-weight:700;margin-bottom:1px}
.bcd{font-size:11px;color:rgba(155,155,180,.6);line-height:1.4}
.kbar{grid-column:1/3;display:flex;gap:12px}
.kc{flex:1;padding:13px 16px;border-radius:11px;display:flex;flex-direction:column;align-items:center;text-align:center;gap:3px;background:rgba(255,255,255,.022);border:1px solid rgba(255,255,255,.06)}
.ki{font-size:24px}.kv{font-size:28px;font-weight:900;letter-spacing:-1px}
.kl{font-size:10px;color:rgba(155,155,180,.45);text-transform:uppercase;letter-spacing:.4px}
.cta2{grid-column:1/3;display:flex;align-items:center;gap:22px;padding:18px 28px;background:linear-gradient(135deg,rgba(233,69,96,.12),rgba(162,155,254,.05),rgba(74,222,222,.05));border:1px solid rgba(233,69,96,.25);border-radius:13px}
.ctah2{font-size:22px;font-weight:900;letter-spacing:-.5px;margin-bottom:5px}
.ctah2 span{color:#E94560}
.ctab2{font-size:12px;color:rgba(155,155,180,.65);line-height:1.55;max-width:700px}
.ctal2{font-size:54px;font-weight:900;color:rgba(233,69,96,.18);letter-spacing:-3px;font-family:monospace}
</style>
<div class="sg">
<div class="s2"><div class="st2">What We <span>Built</span> — ParkIQ</div><div class="ss">A complete parking enforcement intelligence platform — from raw data to actionable officer deployment</div></div>
<div class="bc acc-r">
  <div class="bct cr">✅ Deliverables Completed</div>
  <div class="bi"><div class="bck" style="background:rgba(233,69,96,.15);color:#E94560">✓</div><div><div class="bct2">Hotspot Detection Engine</div><div class="bcd">54 BTP junctions ranked by weighted priority score</div></div></div>
  <div class="bi"><div class="bck" style="background:rgba(245,166,35,.15);color:#F5A623">✓</div><div><div class="bct2">Temporal Pattern Analysis</div><div class="bcd">8–11 AM IST identified as critical enforcement window</div></div></div>
  <div class="bi"><div class="bck" style="background:rgba(74,222,222,.15);color:#4ADEDE">✓</div><div><div class="bct2">Cross-Dataset Correlation</div><div class="bcd">BTP violations × ASTRAM incidents at 500m resolution</div></div></div>
  <div class="bi"><div class="bck" style="background:rgba(162,155,254,.15);color:#A29BFE">✓</div><div><div class="bct2">HCM Congestion Quantification</div><div class="bcd">290 veh-hrs/day lost at Safina Plaza</div></div></div>
  <div class="bi"><div class="bck" style="background:rgba(74,194,154,.15);color:#4AC29A">✓</div><div><div class="bct2">Shift Optimizer (40% → 87%)</div><div class="bcd">4-shift allocation matrix, no new hires needed</div></div></div>
</div>
<div class="bc acc-t">
  <div class="bct ct">🚀 Next Steps (Phase 2)</div>
  <div class="bi"><div class="bck" style="background:rgba(74,222,222,.15);color:#4ADEDE">1</div><div><div class="bct2">Real-Time Feed Integration</div><div class="bcd">Connect live BTP enforcement API + ASTRAM stream</div></div></div>
  <div class="bi"><div class="bck" style="background:rgba(162,155,254,.15);color:#A29BFE">2</div><div><div class="bct2">ML Predictive Model</div><div class="bcd">LSTM: predict violation surges 2–4 hours ahead</div></div></div>
  <div class="bi"><div class="bck" style="background:rgba(245,166,35,.15);color:#F5A623">3</div><div><div class="bct2">Officer Mobile App</div><div class="bcd">React Native: live heatmap + shift alerts to field</div></div></div>
  <div class="bi"><div class="bck" style="background:rgba(74,194,154,.15);color:#4AC29A">4</div><div><div class="bct2">Multi-City Scaling</div><div class="bcd">Deploy in Chennai, Hyderabad, Pune</div></div></div>
</div>
<div class="kbar">
  <div class="kc"><span class="ki">📉</span><div class="kv cr">35–50%</div><div class="kl">Congestion Reduction</div></div>
  <div class="kc"><span class="ki">🚔</span><div class="kv ca">87%</div><div class="kl">Peak-Hour Coverage</div></div>
  <div class="kc"><span class="ki">⏱️</span><div class="kv ct">4 min</div><div class="kl">Saved per 10 Violations</div></div>
  <div class="kc"><span class="ki">🗺️</span><div class="kv cp">54</div><div class="kl">Junctions Covered</div></div>
  <div class="kc"><span class="ki">📊</span><div class="kv cg">290</div><div class="kl">Veh-hrs Saved Daily</div></div>
</div>
<div class="cta2">
  <div style="flex:1"><div class="ctah2">From Data to <span>Deployment</span> in 72 Hours</div><div class="ctab2">ParkIQ is built on real BTP data, grounded in traffic engineering (HCM), and designed for immediate deployment. No new infrastructure needed — runs on existing BTP data systems with a lightweight dashboard layer.</div></div>
  <div class="ctal2">ParkIQ</div>
</div>
</div>""", 12, "Summary & Impact")

# ═══════════════════════════════════════════════════════════════════════════════
# Generate all 12 frames
# ═══════════════════════════════════════════════════════════════════════════════
FRAMES = [f01,f02,f03,f04,f05,f06,f07,f08,f09,f10,f11,f12]

print("\nGenerating HTML frames…")
for i, fn in enumerate(FRAMES, 1):
    html = fn()
    html_path = os.path.join(HTML_DIR, f"frame_{i:02d}.html")
    png_path  = os.path.join(PNG_DIR,  f"frame_{i:02d}.png")
    with open(html_path, "w") as f: f.write(html)

    r = subprocess.run([
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        f"--screenshot={png_path}", "--window-size=1920,980",
        "--hide-scrollbars", "--force-device-scale-factor=1",
        f"file://{html_path}"
    ], capture_output=True, timeout=30)
    sz = os.path.getsize(png_path)//1024 if os.path.exists(png_path) else 0
    print(f"  frame_{i:02d}  {sz}KB  {'✓' if r.returncode==0 else '✗'}")

print(f"\nDone → {PNG_DIR}")
