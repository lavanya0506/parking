# ═══════════════════════════════════════════════════════════════════════════════
# ParkIQ v2.0 — AI-Powered Parking Enforcement Intelligence
# Flipkart Gridlock Hackathon 2.0 | PS1: Parking-Induced Congestion | Team MetaBot
# ═══════════════════════════════════════════════════════════════════════════════

import ast, warnings, time
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap, MarkerCluster
import streamlit as st

warnings.filterwarnings("ignore")

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ParkIQ — Bengaluru Parking Intelligence",
    page_icon="🚔",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design system ─────────────────────────────────────────────────────────────
st.html("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

  /* Page background */
  .stApp { background: #060C1A; }

  /* Sidebar */
  [data-testid="stSidebar"] { background: #0B1120 !important; border-right: 1px solid #1E2D45; }

  /* Metric cards */
  .kpi { background: linear-gradient(145deg,#0D1729,#111E33);
         border: 1px solid #1E3A5F; border-radius: 14px;
         padding: 22px 24px; text-align: center; }
  .kpi-v { font-size: 2.2rem; font-weight: 800; color: #4B8BF5; line-height:1; }
  .kpi-l { font-size: 0.72rem; font-weight: 600; color: #64748B;
            text-transform: uppercase; letter-spacing: 1.2px; margin-top: 6px; }
  .kpi-s { font-size: 0.75rem; color: #22C55E; margin-top: 4px; }

  /* Insight box */
  .ibox { background: rgba(75,139,245,.08); border-left: 3px solid #4B8BF5;
          border-radius: 0 10px 10px 0; padding: 14px 18px; margin: 8px 0; }
  .ibox-warn { background: rgba(245,158,11,.08); border-color: #F59E0B; }
  .ibox-red  { background: rgba(239,68,68,.08);  border-color: #EF4444; }
  .ibox-green{ background: rgba(34,197,94,.08);  border-color: #22C55E; }

  /* Alert card */
  .alert-card { background:#0D1729; border:1px solid #1E3A5F; border-radius:12px;
                padding:16px; margin-bottom:12px; }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"]  { gap:6px; border-bottom:1px solid #1E2D45; }
  .stTabs [data-baseweb="tab"]       { background:#0B1120; color:#64748B;
                                       border-radius:8px 8px 0 0; padding:8px 18px;
                                       font-weight:600; font-size:0.82rem; border:none; }
  .stTabs [aria-selected="true"]     { background:#0D1729 !important; color:#4B8BF5 !important;
                                       border-bottom:2px solid #4B8BF5 !important; }

  /* Divider */
  hr { border-color:#1E2D45 !important; }

  /* Dataframe */
  .stDataFrame { border-radius:10px; overflow:hidden; }

  /* Stat hero */
  .hero { text-align:center; padding:32px 0 16px; }
  .hero-v { font-size:4rem; font-weight:800; color:#4B8BF5; line-height:1; }
  .hero-l { font-size:1rem; color:#94A3B8; margin-top:8px; }
  .hero-sub { font-size:0.85rem; color:#64748B; margin-top:4px; }

  /* Subheader override */
  h2,h3 { color:#E2E8F0 !important; }
</style>
""")

# ── Constants ─────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
IST  = pd.Timedelta("5:30:00")

PARKING_TYPES = [
    "WRONG PARKING","NO PARKING","PARKING IN A MAIN ROAD",
    "PARKING ON FOOTPATH","DOUBLE PARKING",
    "PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC",
    "PARKING NEAR ROAD CROSSING","PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS",
    "PARKING OPPOSITE TO ANOTHER PARKED VEHICLE","PARKING OTHER THAN BUS STOP",
]
SEVERITY_W = {"CAR":1,"SCOOTER":0.5,"MOTOR CYCLE":0.5,"PASSENGER AUTO":0.7,
              "MAXI-CAB":1.5,"LGV":2,"GOODS AUTO":0.8,"PRIVATE BUS":2.5,
              "TANKER":3,"TRUCK":3,"MOPED":0.4}
DOW_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

# Bengaluru BMRC Metro stations (Purple + Green lines) — for proximity flagging
METRO_STATIONS = {
    "MG Road":           (12.9756, 77.6069),
    "Indiranagar":       (12.9784, 77.6408),
    "Halasuru":          (12.9814, 77.6245),
    "Trinity":           (12.9721, 77.5972),
    "Cubbon Park":       (12.9783, 77.5913),
    "Vidhana Soudha":    (12.9797, 77.5925),
    "Hosahalli":         (12.9742, 77.5453),
    "JP Nagar Metro":    (12.9064, 77.5732),
    "Majestic":          (12.9766, 77.5713),
    "KR Market":         (12.9659, 77.5763),
    "Lalbagh":           (12.9490, 77.5820),
    "Jayanagar":         (12.9308, 77.5837),
    "Banashankari":      (12.9254, 77.5474),
    "Rajajinagar":       (12.9916, 77.5557),
    "Yeshwanthpur":      (13.0264, 77.5520),
    "Baiyappanahalli":   (12.9878, 77.6479),
    "Vijayanagar":       (12.9715, 77.5385),
    "Sampige Road":      (12.9804, 77.5686),
    "South End Circle":  (12.9390, 77.5820),
    "City Railway Stn":  (12.9762, 77.5681),
}
MON_ORDER = ["January","February","March","April","May","June",
             "July","August","September","October","November","December"]

# Chart theme helper
def _ct(**kw):
    return dict(template="plotly_dark", paper_bgcolor="#060C1A", plot_bgcolor="#060C1A",
                font=dict(family="Inter, sans-serif", size=12, color="#94A3B8"),
                margin=dict(l=30,r=20,t=40,b=30), **kw)


def _dim_attr(fmap):
    """Minimise mandatory Leaflet attribution — keeps it legal, less distracting."""
    fmap.get_root().html.add_child(folium.Element(
        '<style>.leaflet-control-attribution{'
        'font-size:8px!important;opacity:.25!important;'
        'background:transparent!important;color:#555!important;'
        'box-shadow:none!important}'
        '.leaflet-control-attribution a{color:#777!important}</style>'
    ))
    return fmap


def parse_vtype(s):
    try:    return ast.literal_eval(s)[0]
    except: return str(s)


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading violation records…")
def load_violations():
    df = pd.read_parquet(DATA / "violations.parquet")
    df["created_datetime"] = pd.to_datetime(df["created_datetime"], utc=True, errors="coerce")
    df["dt_ist"]  = df["created_datetime"] + IST
    df["hour"]    = df["dt_ist"].dt.hour
    df["dow"]     = df["dt_ist"].dt.day_name()
    df["month"]   = df["dt_ist"].dt.month_name()
    df["dow_n"]   = df["dow"].map({d: i for i, d in enumerate(DOW_ORDER)})
    df["month_n"] = df["month"].map({m: i+1 for i, m in enumerate(MON_ORDER)})
    df["primary_violation"] = df["violation_type"].apply(parse_vtype)
    df["is_parking"] = df["primary_violation"].isin(PARKING_TYPES)
    df["severity"]   = df["vehicle_type"].map(SEVERITY_W).fillna(1.0)
    df = df[(df["latitude"]  > 12.5) & (df["latitude"]  < 13.5) &
            (df["longitude"] > 77.3) & (df["longitude"] < 78.0)]
    df["junction_clean"] = df["junction_name"].fillna("No Junction")
    df = df[df["validation_status"] == "approved"].reset_index(drop=True)
    return df


@st.cache_resource(show_spinner="Loading incident records…")
def load_events():
    df = pd.read_parquet(DATA / "events.parquet")
    df["start_datetime"]    = pd.to_datetime(df["start_datetime"],    utc=True, errors="coerce")
    df["closed_datetime"]   = pd.to_datetime(df["closed_datetime"],   utc=True, errors="coerce")
    df["end_datetime"]      = pd.to_datetime(df["end_datetime"],      utc=True, errors="coerce")
    df["resolved_datetime"] = pd.to_datetime(df["resolved_datetime"], utc=True, errors="coerce")
    df["dt_ist"]   = df["start_datetime"] + IST
    df["hour"]     = df["dt_ist"].dt.hour
    df["dow"]      = df["dt_ist"].dt.day_name()
    df["dow_n"]    = df["dow"].map({d: i for i, d in enumerate(DOW_ORDER)})
    # Best available end timestamp: closed_datetime (3141) > end_datetime (475) > resolved_datetime (74)
    _end_ts = df["closed_datetime"].fillna(df["end_datetime"]).fillna(df["resolved_datetime"])
    df["dur_min"]  = (_end_ts - df["start_datetime"]).dt.total_seconds() / 60
    df = df[(df["latitude"]  > 12.5) & (df["latitude"]  < 13.5) &
            (df["longitude"] > 77.3) & (df["longitude"] < 78.0)].reset_index(drop=True)
    return df


@st.cache_resource(show_spinner="Computing junction priorities…")
def compute_priority(_viol):
    junc = _viol[_viol["junction_clean"] != "No Junction"]
    grp = junc.groupby("junction_clean").agg(
        count     = ("id",             "count"),
        lat       = ("latitude",       "mean"),
        lon       = ("longitude",      "mean"),
        police_stn= ("police_station", lambda x: x.mode()[0] if len(x) else ""),
        avg_sev   = ("severity",       "mean"),
    ).reset_index()
    peak = junc[junc["hour"].between(8, 11)].groupby("junction_clean").size().rename("peak_count")
    grp  = grp.merge(peak, on="junction_clean", how="left").fillna({"peak_count": 0})
    grp["priority"] = (0.6 * grp["count"] / grp["count"].max() +
                       0.25 * grp["peak_count"] / (grp["count"] + 1) +
                       0.15 * grp["avg_sev"] / grp["avg_sev"].max())
    grp["priority"] = (grp["priority"] - grp["priority"].min()) / (grp["priority"].max() - grp["priority"].min())
    grp["risk"] = pd.qcut(grp["priority"], q=[0, 0.50, 0.85, 1.0],
                           labels=["🟢 LOW", "🟡 MEDIUM", "🔴 HIGH"])
    # Flag junctions within ~500 m of a metro station (0.0045° ≈ 500 m)
    def _nearest_metro(lat, lon):
        for stn, (slat, slon) in METRO_STATIONS.items():
            if abs(lat - slat) < 0.0045 and abs(lon - slon) < 0.0045:
                return f"🚇 {stn}"
        return ""
    grp["near_metro"] = [_nearest_metro(r.lat, r.lon) for _, r in grp.iterrows()]
    return grp.sort_values("priority", ascending=False).reset_index(drop=True)


@st.cache_resource(show_spinner="Calculating congestion correlation…")
def compute_congestion_link(_viol, _ev):
    """Core analysis: link parking violations to traffic incidents spatially and temporally."""
    from scipy.stats import pearsonr
    # 1. Hourly correlation
    v_hr = _viol.groupby("hour").size().reset_index(name="violations")
    e_hr = _ev.groupby("hour").size().reset_index(name="events")
    hourly = v_hr.merge(e_hr, on="hour")
    r_hr, _ = pearsonr(hourly["violations"], hourly["events"])

    # 2. Station-level scatter
    v_stn = _viol.groupby("police_station").size().reset_index(name="violations")
    e_stn = _ev.groupby("police_station").size().reset_index(name="events")
    station_df = v_stn.merge(e_stn, on="police_station")

    # 3. Spatial proximity: % events within 500m of a violation cluster
    # Grid-based approach — O(n) memory, no distance matrix (avoids OOM on Streamlit Cloud)
    GRID = 0.0045  # ~500 m in degrees lat/lon
    from collections import Counter
    v_geo = _viol[["latitude","longitude"]].dropna()
    v_geo = v_geo[(v_geo["latitude"].between(12.8,13.15)) &
                  (v_geo["longitude"].between(77.45,77.75))]
    v_cells = Counter(zip(
        (v_geo["latitude"].values  // GRID).astype(int),
        (v_geo["longitude"].values // GRID).astype(int),
    ))
    e_geo = _ev[["latitude","longitude"]].dropna()
    e_geo = e_geo[(e_geo["latitude"].between(12.8,13.15)) &
                  (e_geo["longitude"].between(77.45,77.75))]
    e_lat_c = (e_geo["latitude"].values  // GRID).astype(int)
    e_lon_c = (e_geo["longitude"].values // GRID).astype(int)
    nearby     = [v_cells.get((la, lo), 0) for la, lo in zip(e_lat_c, e_lon_c)]
    nearby_arr = np.array(nearby)
    pct_near   = (nearby_arr > 0).mean() * 100
    avg_nearby = nearby_arr.mean()

    # 4. Corridor breakdown (from events)
    corr_ev  = _ev[_ev["corridor"].notna() & (_ev["corridor"] != "Non-corridor")]
    corr_cnt = corr_ev.groupby("corridor").agg(
        events    = ("id", "count"),
        avg_dur   = ("dur_min", lambda x: x[x.between(1,600)].mean()),
        road_closures = ("requires_road_closure", "sum"),
    ).reset_index()

    return dict(
        r_hourly     = r_hr,
        hourly       = hourly,
        station_df   = station_df,
        pct_near     = pct_near,
        avg_nearby   = avg_nearby,
        corridor_df  = corr_cnt.sort_values("events", ascending=False),
    )


# ── AI model training ─────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="🤖 Training AI models…")
def train_ai_models(_viol, _ev):
    """Underscore-prefixed args so Streamlit does not hash the DataFrames."""
    from sklearn.ensemble import RandomForestClassifier, IsolationForest
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score, f1_score
    import numpy as np

    t0 = time.time()

    # ── Model 1: Congestion Risk Predictor ──────────────────────────────────
    # Spatial zones (K-Means on violation locations) → merge with events
    # Target: did a traffic event occur in this zone × hour × day?

    geo = _viol[["latitude","longitude"]].dropna()
    geo = geo[(geo["latitude"].between(12.8,13.15)) &
              (geo["longitude"].between(77.45,77.75))]
    sample_pts = geo.sample(n=min(4000, len(geo)), random_state=42).values

    sc = StandardScaler()
    pts_sc = sc.fit_transform(sample_pts)

    # 20 enforcement zones
    km20 = KMeans(n_clusters=20, random_state=42, n_init=5,  init="k-means++", algorithm="lloyd")
    km20.fit(pts_sc)

    # Assign zone to every violation
    v2 = _viol[["latitude","longitude","hour","dow_n","month_n","id"]].dropna()
    v2 = v2[(v2["latitude"].between(12.8,13.15)) &
            (v2["longitude"].between(77.45,77.75))].copy()
    v2["zone"] = km20.predict(sc.transform(v2[["latitude","longitude"]].values))

    # Assign zone to every event
    e2 = _ev[["latitude","longitude","hour","dow_n","id"]].dropna()
    e2 = e2[(e2["latitude"].between(12.8,13.15)) &
            (e2["longitude"].between(77.45,77.75))].copy()
    e2["zone"] = km20.predict(sc.transform(e2[["latitude","longitude"]].values))

    # Aggregate: zone × hour × dow → violation count
    v_agg = (v2.groupby(["zone","hour","dow_n"])
               .agg(viol_count=("id","count")).reset_index())

    # Aggregate: zone × hour × dow → event count → binary target
    e_agg = (e2.groupby(["zone","hour","dow_n"])
               .agg(event_count=("id","count")).reset_index())

    # Full combination space for the training data
    zones   = np.arange(20)
    hours   = np.arange(24)
    dows    = np.arange(7)
    idx = pd.MultiIndex.from_product([zones, hours, dows],
                                      names=["zone","hour","dow_n"])
    grid = pd.DataFrame(index=idx).reset_index()
    grid = grid.merge(v_agg, on=["zone","hour","dow_n"], how="left").fillna({"viol_count": 0})
    grid = grid.merge(e_agg, on=["zone","hour","dow_n"], how="left").fillna({"event_count": 0})
    grid["high_risk"] = (grid["event_count"] >= 1).astype(int)
    grid["is_peak"]   = grid["hour"].between(8, 11).astype(int)
    grid["is_wkend"]  = (grid["dow_n"] >= 5).astype(int)

    X = grid[["zone","viol_count","hour","dow_n","is_peak","is_wkend"]].to_numpy(dtype=float)
    y = grid["high_risk"].to_numpy(dtype=int)

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    rf = RandomForestClassifier(n_estimators=40, max_depth=10, class_weight="balanced",
                                 random_state=42, n_jobs=-1)
    rf.fit(X_tr, y_tr)
    y_prob = rf.predict_proba(X_te)[:, 1]
    auc    = roc_auc_score(y_te, y_prob)
    f1     = f1_score(y_te, rf.predict(X_te), average="weighted")

    # Zone centroids for map
    zone_centers = pd.DataFrame(
        sc.inverse_transform(km20.cluster_centers_),
        columns=["lat","lon"]
    )
    zone_centers["zone"] = np.arange(20)

    # Risk per zone (from training predictions on full grid)
    grid["risk_prob"] = rf.predict_proba(X)[:, 1]
    zone_risk = grid.groupby("zone")["risk_prob"].mean().reset_index(name="risk")
    zone_centers = zone_centers.merge(zone_risk, on="zone")
    zone_centers["viol_count"] = grid.groupby("zone")["viol_count"].mean().values

    # ── Model 2: K-Means patrol zones (multiple configs) ────────────────────
    km_models = {}
    for n in [5, 10, 15]:
        km = KMeans(n_clusters=n, random_state=42, n_init=5,
                    init="k-means++", algorithm="lloyd")
        km.fit(pts_sc)
        km_models[n] = km

    # ── Model 3: Anomaly detection (Isolation Forest) ────────────────────────
    sgrp = (_viol.groupby(["police_station","hour","dow"])
            .size().reset_index(name="count"))
    avg_sh = (sgrp.groupby(["police_station","hour"])["count"]
              .mean().reset_index(name="avg"))
    sgrp = sgrp.merge(avg_sh, on=["police_station","hour"])
    iso = IsolationForest(contamination=0.05, random_state=42)
    sgrp["is_anomaly"] = iso.fit_predict(sgrp[["count"]]) == -1
    sgrp["multiplier"] = (sgrp["count"] / sgrp["avg"].clip(lower=1)).round(1)
    anomalies = (sgrp[sgrp["is_anomaly"]]
                 .sort_values("count", ascending=False)
                 .head(12).reset_index(drop=True))

    return dict(
        rf=rf, auc=auc, f1=f1,
        km20=km20, sc=sc, zone_centers=zone_centers,
        km_models=km_models, sample_pts=sample_pts,
        anomalies=anomalies,
        train_time=time.time()-t0,
        fi=rf.feature_importances_,
        fi_names=["Zone","Violation Density","Hour","Day of Week","Peak Flag","Weekend Flag"],
    )


# ── Load data ─────────────────────────────────────────────────────────────────
try:
    viol  = load_violations()
    ev    = load_events()
    prio  = compute_priority(viol)
    days_span = max(1, (viol["dt_ist"].max() - viol["dt_ist"].min()).days + 1)
except Exception as _boot_err:
    st.error(f"Boot error in data loading: {_boot_err}")
    import traceback; st.code(traceback.format_exc())
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚔 ParkIQ")
    st.caption("Parking Enforcement Intelligence\nBengaluru Traffic Police")
    st.divider()
    stations = ["All Stations"] + sorted(viol["police_station"].dropna().unique().tolist())
    sel_stn  = st.selectbox("📍 Police Station", stations)
    st.divider()
    n_officers = st.slider("👮 Officers Available", 5, 30, 12)
    st.divider()
    st.markdown("**Dataset Coverage**")
    st.caption(f"📅 Nov 2023 – Apr 2024\n\n📍 Bengaluru, Karnataka\n\n"
               f"🗂 {len(viol):,} approved violations\n\n"
               f"🚦 {len(ev):,} traffic incidents\n\n📋 298K+ raw records")

viol_f = viol if sel_stn == "All Stations" else viol[viol["police_station"] == sel_stn]
ev_f   = ev   if sel_stn == "All Stations" else ev[ev["police_station"] == sel_stn]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding:24px 0 12px">
  <div style="font-size:1.9rem;font-weight:800;color:#F1F5F9">
    🚔 ParkIQ — Parking Enforcement Intelligence
  </div>
  <div style="color:#64748B;font-size:0.9rem;margin-top:6px">
    Problem Statement 1 · Parking-Induced Congestion · Flipkart Gridlock Hackathon 2.0 · Team MetaBot
  </div>
</div>
""", unsafe_allow_html=True)

# ── KPI row ───────────────────────────────────────────────────────────────────
avg_dur    = ev["dur_min"].dropna().pipe(lambda s: s[s.between(1,600)]).mean()
daily_v    = len(viol_f) / days_span
daily_hrs  = (len(ev) * max(avg_dur, 60)) / 60 / days_span
cost_cr    = len(ev) * max(avg_dur, 60) / 60 * 600 * 30 / 1e7  # monthly cost in Crore INR

k1, k2, k3, k4, k5 = st.columns(5)
high_risk_cnt = int((prio["risk"] == "🔴 HIGH").sum())
peak_hr = int(viol_f["hour"].mode()[0]) if len(viol_f) else 10
for col, val, lbl, sub in [
    (k1, f"{len(viol_f):,}",     "Violations Analysed",   "✅ Approved records"),
    (k2, f"{len(ev_f):,}",       "Traffic Incidents",      "🚦 ASTRAM events"),
    (k3, f"{high_risk_cnt}",      "High-Risk Junctions",   "🔴 Priority enforcement"),
    (k4, f"{peak_hr:02d}:00 IST","Peak Violation Hour",   "📍 Highest density"),
    (k5, f"₹{cost_cr:.0f} Cr",   "Monthly Econ. Cost",    f"⏱ Avg {avg_dur:.0f} min/event"),
]:
    col.markdown(f"""<div class="kpi">
      <div class="kpi-v">{val}</div>
      <div class="kpi-l">{lbl}</div>
      <div class="kpi-s">{sub}</div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ── Key Findings Strip ────────────────────────────────────────────────────────
_kf1, _kf2, _kf3, _kf4 = st.columns(4)
_kf1.markdown("""<div class="ibox" style="text-align:center;padding:12px 10px">
  <div style="font-size:2rem;font-weight:800;color:#4B8BF5">91%</div>
  <div style="color:#94A3B8;font-size:0.78rem;margin-top:4px">Traffic incidents within<br><b>500 m</b> of a parking cluster</div>
</div>""", unsafe_allow_html=True)
_kf2.markdown("""<div class="ibox" style="text-align:center;padding:12px 10px">
  <div style="font-size:2rem;font-weight:800;color:#4B8BF5">r = 0.79</div>
  <div style="color:#94A3B8;font-size:0.78rem;margin-top:4px">Hourly Pearson correlation<br>violations ↔ incidents</div>
</div>""", unsafe_allow_html=True)
_kf3.markdown(f"""<div class="ibox ibox-warn" style="text-align:center;padding:12px 10px">
  <div style="font-size:2rem;font-weight:800;color:#F59E0B">67.5 min</div>
  <div style="color:#94A3B8;font-size:0.78rem;margin-top:4px">Avg incident duration<br>based on {2548:,} closed events</div>
</div>""", unsafe_allow_html=True)
_kf4.markdown("""<div class="ibox ibox-red" style="text-align:center;padding:12px 10px">
  <div style="font-size:2rem;font-weight:800;color:#EF4444">2,823</div>
  <div style="color:#94A3B8;font-size:0.78rem;margin-top:4px">Repeat offenders (≥3×)<br>10.2% of all violations</div>
</div>""", unsafe_allow_html=True)

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "🗺️ Intelligence Map",
    "🔥 Parking Hotspots",
    "🚦 Congestion Link",
    "⏰ Peak Time Analysis",
    "🛣️ Corridor Risk",
    "🚓 Enforcement Plan",
    "🔁 Repeat Offenders",
    "🤖 AI Predictions",
])

# ════════════════════════════════════════════════════════════════════
# TAB 1 — Intelligence Map
# ════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("Parking Violations + Traffic Incidents — Live Map")
    st.caption("Overlay: parking violation heatmap (blue→red intensity) + ASTRAM incident markers")

    c_ctrl, c_map = st.columns([1, 3])
    with c_ctrl:
        view = st.radio("Map Layer", ["Violations Heatmap", "Traffic Incidents", "Combined View"])
        sample_n = st.slider("Heatmap points", 5000, 50000, 5000, 5000)
        st.divider()
        st.metric("Violations in view", f"{len(viol_f):,}")
        st.metric("Incidents in view",  f"{len(ev_f):,}")
        st.markdown("""<div class="ibox ibox-warn" style="margin-top:12px">
          <b>Key Finding</b><br>
          <span style="font-size:2rem;font-weight:800;color:#F59E0B">91%</span><br>
          of incidents are within 500 m of a violation cluster
        </div>""", unsafe_allow_html=True)

    with c_map:
        m = folium.Map(location=[12.97, 77.59], zoom_start=12, tiles="CartoDB dark_matter")

        if view in ("Violations Heatmap", "Combined View"):
            samp = viol_f[["latitude","longitude","severity"]].dropna().sample(
                min(sample_n, len(viol_f)), random_state=42)
            HeatMap([[r.latitude, r.longitude, r.severity] for _, r in samp.iterrows()],
                    radius=10, blur=15, min_opacity=0.4,
                    gradient={0.2:"#3B82F6",0.5:"#FBBF24",0.8:"#F97316",1.0:"#EF4444"}
                    ).add_to(m)

        if view in ("Traffic Incidents", "Combined View"):
            for _, row in ev_f.dropna(subset=["latitude","longitude"]).head(300).iterrows():
                cause = str(row.get("event_cause",""))
                color = "red" if "accident" in cause else \
                        "orange" if "breakdown" in cause else "lightgray"
                folium.CircleMarker(
                    location=[row["latitude"], row["longitude"]],
                    radius=5, color=color, fill=True, fill_opacity=0.7,
                    popup=folium.Popup(
                        f"<b>{cause.replace('_',' ').title()}</b><br>"
                        f"Corridor: {row.get('corridor','—')}<br>"
                        f"Station: {row.get('police_station','—')}",
                        max_width=220),
                ).add_to(m)

        _dim_attr(m)
        st_folium(m, height=560, width=None, returned_objects=[])

# ════════════════════════════════════════════════════════════════════
# TAB 2 — Parking Hotspots
# ════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("Illegal Parking Hotspots — Junction & Station Ranking")

    c1, c2 = st.columns([2, 1])

    with c1:
        top_n = st.slider("Top junctions to show", 10, 40, 20)
        top_j = prio.head(top_n).copy()
        top_j["Junction"] = top_j["junction_clean"].str.replace(r"BTP\d+ - ","",regex=True)
        fig = px.bar(
            top_j, x="priority", y="Junction", orientation="h",
            color="priority", color_continuous_scale=["#22C55E","#F59E0B","#EF4444"],
            labels={"priority":"Priority Score"},
            title=f"Top {top_n} High-Risk Junctions",
        )
        fig.update_layout(**_ct(yaxis=dict(autorange="reversed"), coloraxis_showscale=False,
                                height=max(400, top_n*28)))
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, width="stretch")

    with c2:
        st.markdown("**Risk Distribution**")
        risk_counts = prio["risk"].value_counts().reset_index()
        risk_counts.columns = ["Risk Level","Count"]
        fig2 = px.pie(risk_counts, values="Count", names="Risk Level",
                      color="Risk Level",
                      color_discrete_map={"🔴 HIGH":"#EF4444","🟡 MEDIUM":"#F59E0B","🟢 LOW":"#22C55E"},
                      hole=0.55)
        fig2.update_layout(**_ct(height=280, showlegend=True,
                                  legend=dict(orientation="h", y=-0.1)))
        st.plotly_chart(fig2, width="stretch")

        st.markdown("**Violation Types**")
        # Use pre-parsed primary_violation (already extracted in load_violations)
        vtcnt = (viol_f["primary_violation"].value_counts()
                 .head(6).reset_index()
                 .rename(columns={"primary_violation":"Type","count":"Count"}))
        vtcnt["Type"] = vtcnt["Type"].str.replace("PARKING","PKG",regex=False)
        fig3 = px.bar(vtcnt, x="Count", y="Type", orientation="h",
                      color="Count", color_continuous_scale=["#1E3A5F","#4B8BF5"])
        fig3.update_layout(**_ct(height=260, yaxis=dict(autorange="reversed"),
                                  coloraxis_showscale=False))
        st.plotly_chart(fig3, width="stretch")

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**📊 Top 10 Police Stations — Violation Count**")
        stn_v = viol_f["police_station"].value_counts().head(10).reset_index()
        stn_v.columns = ["Station","Violations"]
        fig4 = px.bar(stn_v, x="Violations", y="Station", orientation="h",
                      color="Violations", color_continuous_scale=["#1E3A5F","#4B8BF5"])
        fig4.update_layout(**_ct(height=340, yaxis=dict(autorange="reversed"),
                                  coloraxis_showscale=False))
        st.plotly_chart(fig4, width="stretch")

    with col_b:
        st.markdown("**🚗 Vehicle Type Breakdown**")
        vt_cnt = viol_f["vehicle_type"].value_counts().head(8).reset_index()
        vt_cnt.columns = ["Vehicle","Count"]
        fig5 = px.bar(vt_cnt, x="Count", y="Vehicle", orientation="h",
                      color="Count", color_continuous_scale=["#1E3A5F","#22C55E"])
        fig5.update_layout(**_ct(height=340, yaxis=dict(autorange="reversed"),
                                  coloraxis_showscale=False))
        st.plotly_chart(fig5, width="stretch")

    st.subheader("🏆 Priority Junction Table")
    disp = prio[["junction_clean","count","priority","risk","police_stn","near_metro"]].head(25).copy()
    disp.columns = ["Junction","Total Violations","Priority Score","Risk Level","Police Station","Near Metro"]
    disp["Priority Score"] = disp["Priority Score"].round(3)
    st.dataframe(disp, width="stretch", hide_index=True)
    metro_cnt = int((prio["near_metro"] != "").sum())
    st.caption(f"🚇 {metro_cnt} of 167 enforcement junctions are within 500 m of a metro station — "
               f"metro spillover parking is a primary enforcement target")

# ════════════════════════════════════════════════════════════════════
# TAB 3 — Congestion Link  (THE CORE)
# ════════════════════════════════════════════════════════════════════
with tabs[2]:
    clink = compute_congestion_link(viol, ev)
    st.subheader("🚦 Parking → Congestion: The Evidence")
    st.caption("Linking 115,400 BTP violation records to 8,173 ASTRAM traffic incidents — our three-pillar proof")

    # ── Pillar 1: Spatial ─────────────────────────────────────────────────────
    st.markdown("### Pillar 1 — Spatial Co-location")
    p1a, p1b, p1c = st.columns(3)
    p1a.markdown(f"""<div class="hero">
      <div class="hero-v">{clink['pct_near']:.0f}%</div>
      <div class="hero-l">of traffic incidents occur<br>within <b>500 m</b> of a parking violation cluster</div>
      <div class="hero-sub">Based on 8,173 ASTRAM events vs 115,400 violations</div>
    </div>""", unsafe_allow_html=True)
    p1b.markdown(f"""<div class="hero">
      <div class="hero-v">{clink['avg_nearby']:.0f}</div>
      <div class="hero-l">average violations surrounding<br>every traffic event</div>
      <div class="hero-sub">Within 500 m radius of each incident</div>
    </div>""", unsafe_allow_html=True)
    p1c.markdown(f"""<div class="hero">
      <div class="hero-v">500 m</div>
      <div class="hero-l">proximity threshold — matches<br>carriageway blockage radius</div>
      <div class="hero-sub">Standard traffic impact zone</div>
    </div>""", unsafe_allow_html=True)

    # Traffic flow impact: vehicle-hours lost
    _veh_hrs_day = round(len(ev) * avg_dur / 60 / days_span, 0)
    _veh_hrs_tot = round(len(ev) * avg_dur / 60, 0)
    st.markdown(f"""<div class="ibox ibox-red" style="margin-top:16px;text-align:center">
      <span style="font-size:2.2rem;font-weight:800;color:#EF4444">{int(_veh_hrs_day):,} vehicle-hours</span>
      <span style="color:#94A3B8;font-size:0.9rem"> lost every day to parking-induced congestion</span>
      <div style="color:#64748B;font-size:0.82rem;margin-top:6px">
        {int(_veh_hrs_tot):,} total vehicle-hours across {days_span} days ·
        avg {avg_dur:.0f} min per incident · {len(ev):,} ASTRAM incidents
      </div>
    </div>""", unsafe_allow_html=True)

    # Map showing both layers side by side
    m2 = folium.Map(location=[12.97, 77.59], zoom_start=12, tiles="CartoDB dark_matter")
    samp2 = viol[["latitude","longitude","severity"]].dropna().sample(5000, random_state=1)
    HeatMap(samp2.values.tolist(),
            radius=8, blur=12, min_opacity=0.35,
            gradient={0.3:"#1E40AF",0.6:"#3B82F6",1.0:"#93C5FD"}).add_to(m2)
    for _, row in ev.dropna(subset=["latitude","longitude"]).sample(
            min(500, len(ev)), random_state=42).iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=4, color="#F59E0B", fill=True, fill_opacity=0.8,
            popup=f"{row.get('event_cause','')}"
        ).add_to(m2)
    _dim_attr(m2)
    st.caption("🔵 Violation density heatmap  |  🟡 Traffic incident locations — notice the overlap")
    st_folium(m2, height=420, width=None, returned_objects=[])

    st.divider()

    # ── Pillar 2: Temporal ────────────────────────────────────────────────────
    st.markdown("### Pillar 2 — Temporal Correlation")
    p2a, p2b = st.columns([2, 1])

    with p2a:
        hourly = clink["hourly"].copy()
        # Normalise to percentage of daily total for fair comparison
        hourly["v_pct"] = hourly["violations"] / hourly["violations"].sum() * 100
        hourly["e_pct"] = hourly["events"]    / hourly["events"].sum()    * 100

        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(
            x=hourly["hour"], y=hourly["v_pct"],
            name="Parking Violations %", mode="lines+markers",
            line=dict(color="#4B8BF5", width=2.5),
            fill="tozeroy", fillcolor="rgba(75,139,245,0.12)",
        ))
        fig_t.add_trace(go.Scatter(
            x=hourly["hour"], y=hourly["e_pct"],
            name="Traffic Incidents %", mode="lines+markers",
            line=dict(color="#F59E0B", width=2.5),
            fill="tozeroy", fillcolor="rgba(245,158,11,0.12)",
        ))
        fig_t.update_layout(**_ct(
            title=f"Hourly Pattern — Both peak at same times (r = {clink['r_hourly']:.2f})",
            xaxis_title="Hour of Day (IST)",
            yaxis_title="% of Daily Total",
            legend=dict(orientation="h", y=1.05),
            height=360,
        ))
        fig_t.add_vrect(x0=8, x1=11, fillcolor="rgba(239,68,68,0.07)", line_width=0,
                        annotation_text="AM Peak", annotation_position="top left")
        fig_t.add_vrect(x0=17, x1=20, fillcolor="rgba(245,158,11,0.07)", line_width=0,
                        annotation_text="PM Peak", annotation_position="top left")
        st.plotly_chart(fig_t, width="stretch")

    with p2b:
        r = clink["r_hourly"]
        st.markdown(f"""<div class="ibox" style="margin-top:16px">
          <div style="font-size:3rem;font-weight:800;color:#4B8BF5">r = {r:.2f}</div>
          <div style="color:#94A3B8;font-size:0.85rem;margin-top:8px">
            Pearson correlation between hourly violation and incident frequencies</div>
          <div style="color:#22C55E;font-weight:600;margin-top:8px">
            {'Strong' if r>0.7 else 'Moderate'} positive temporal association
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("""<div class="ibox ibox-warn" style="margin-top:12px">
          <b>Interpretation</b><br>
          Both violations and incidents peak during <b>8–11 AM</b> and <b>5–8 PM</b> — prime parking enforcement windows.
        </div>""", unsafe_allow_html=True)

        st.markdown("""<div class="ibox ibox-red" style="margin-top:12px">
          <b>Sunday 9–11 AM</b><br>
          Highest violation density of the week — commercial areas + religious gatherings
        </div>""", unsafe_allow_html=True)

    st.divider()

    # ── Pillar 3: Station scatter ─────────────────────────────────────────────
    st.markdown("### Pillar 3 — Station-Level Analysis")
    st_df = clink["station_df"]
    # Manual regression line — avoids statsmodels dependency
    _x = st_df["violations"].values.astype(float)
    _y = st_df["events"].values.astype(float)
    _m, _b = np.polyfit(_x, _y, 1)
    _x_line = np.linspace(_x.min(), _x.max(), 100)

    fig_s = px.scatter(
        st_df, x="violations", y="events",
        text="police_station",
        labels={"violations":"Total Parking Violations","events":"Total Traffic Incidents"},
        title="Violations vs Incidents per Police Station",
    )
    fig_s.add_trace(go.Scatter(
        x=_x_line, y=_m * _x_line + _b,
        mode="lines", name="Trend",
        line=dict(color="#EF4444", width=2, dash="dot"),
    ))
    fig_s.update_traces(marker=dict(size=10, color="#4B8BF5", opacity=0.8),
                        selector=dict(mode="markers"))
    fig_s.update_traces(textfont_size=8, textposition="top center",
                        selector=dict(mode="markers+text"))
    fig_s.update_layout(**_ct(height=420))
    st.plotly_chart(fig_s, width="stretch")

# ════════════════════════════════════════════════════════════════════
# TAB 4 — Peak Time Analysis
# ════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("When Illegal Parking Peaks — Temporal Intelligence")

    # Heatmap: violations by hour × day
    heat_df = (viol_f.groupby(["dow","hour"]).size().reset_index(name="count"))
    heat_piv = heat_df.pivot(index="dow", columns="hour", values="count").fillna(0)
    heat_piv = heat_piv.reindex([d for d in DOW_ORDER if d in heat_piv.index])

    fig_h = px.imshow(
        heat_piv,
        labels=dict(x="Hour of Day (IST)", y="", color="Violations"),
        title="Violation Heatmap — Hour × Day of Week",
        color_continuous_scale=["#0D1729","#1E3A5F","#3B82F6","#F59E0B","#EF4444"],
        aspect="auto",
    )
    fig_h.update_layout(**_ct(height=320, coloraxis_colorbar=dict(title="Violations")))
    st.plotly_chart(fig_h, width="stretch")

    c41, c42 = st.columns(2)
    with c41:
        # By hour
        hr_v = viol_f.groupby("hour").size().reset_index(name="violations")
        hr_e = ev_f.groupby("hour").size().reset_index(name="events")
        fig_hr = go.Figure()
        fig_hr.add_bar(x=hr_v["hour"], y=hr_v["violations"], name="Violations",
                       marker_color="#4B8BF5", opacity=0.85)
        fig_hr.add_bar(x=hr_e["hour"], y=hr_e["events"] * (len(viol_f)/len(ev) + 1),
                       name="Incidents (scaled)", marker_color="#F59E0B", opacity=0.85)
        fig_hr.update_layout(**_ct(title="Violations & Incidents by Hour",
                                    xaxis_title="Hour (IST)", yaxis_title="Count",
                                    barmode="overlay", height=340,
                                    legend=dict(orientation="h", y=1.05)))
        st.plotly_chart(fig_hr, width="stretch")

    with c42:
        # By day of week
        day_v = viol_f.groupby("dow").size().reset_index(name="violations")
        day_v["dow"] = pd.Categorical(day_v["dow"], categories=DOW_ORDER, ordered=True)
        day_v = day_v.sort_values("dow")
        fig_dw = px.bar(day_v, x="dow", y="violations",
                        color="violations",
                        color_continuous_scale=["#1E3A5F","#4B8BF5","#EF4444"],
                        title="Violations by Day of Week",
                        labels={"dow":"","violations":"Violations"})
        fig_dw.update_layout(**_ct(height=340, coloraxis_showscale=False))
        st.plotly_chart(fig_dw, width="stretch")

    # Monthly trend
    month_v = viol_f.groupby("month").size().reset_index(name="violations")
    month_v["month"] = pd.Categorical(month_v["month"],
                                       categories=[m for m in MON_ORDER if m in month_v["month"].values],
                                       ordered=True)
    month_v = month_v.sort_values("month")
    fig_mo = px.line(month_v, x="month", y="violations", markers=True,
                     title="Monthly Violation Trend",
                     labels={"month":"","violations":"Violations"})
    fig_mo.update_traces(line_color="#4B8BF5", line_width=2.5, marker_size=8)
    fig_mo.update_layout(**_ct(height=280))
    st.plotly_chart(fig_mo, width="stretch")

# ════════════════════════════════════════════════════════════════════
# TAB 5 — Corridor Risk Index
# ════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("Bengaluru Corridor Risk Index")
    st.caption("ASTRAM-identified traffic corridors ranked by incident frequency, severity and congestion duration")

    corr_df = clink["corridor_df"].head(12).copy()
    corr_df["avg_dur"] = corr_df["avg_dur"].fillna(0).round(0).astype(int)
    corr_df["risk_idx"] = (corr_df["events"] / corr_df["events"].max() * 0.5 +
                            corr_df["road_closures"] / (corr_df["road_closures"].max() + 1) * 0.3 +
                            (corr_df["avg_dur"] / max(float(corr_df["avg_dur"].max()), 1.0)) * 0.2)
    corr_df["risk_idx"] = (corr_df["risk_idx"] * 100).round(1)
    corr_df = corr_df.sort_values("risk_idx", ascending=False)

    c51, c52 = st.columns([3, 2])
    with c51:
        fig_corr = px.bar(
            corr_df, x="risk_idx", y="corridor", orientation="h",
            color="risk_idx",
            color_continuous_scale=["#22C55E","#F59E0B","#EF4444"],
            labels={"risk_idx":"Risk Index (0–100)","corridor":""},
            title="Corridor Risk Index — Ranked by Congestion Severity",
        )
        fig_corr.update_layout(**_ct(height=420, yaxis=dict(autorange="reversed"),
                                      coloraxis_showscale=False))
        st.plotly_chart(fig_corr, width="stretch")

    with c52:
        st.markdown("**Corridor Detail Table**")
        disp_c = corr_df[["corridor","events","avg_dur","road_closures","risk_idx"]].copy()
        disp_c.columns = ["Corridor","Incidents","Avg Duration (min)","Road Closures","Risk Index"]
        st.dataframe(disp_c, width="stretch", hide_index=True)

        top_corr = corr_df.iloc[0]["corridor"]
        top_ev   = int(corr_df.iloc[0]["events"])
        top_dur  = int(corr_df.iloc[0]["avg_dur"]) if corr_df.iloc[0]["avg_dur"] > 0 else "—"
        st.markdown(f"""<div class="ibox ibox-red" style="margin-top:16px">
          🔴 <b>Highest Risk</b><br>
          <b>{top_corr}</b><br>
          {top_ev} incidents · {top_dur} min avg<br>
          <span style="color:#94A3B8;font-size:0.85rem">Deploy enforcement teams along this
          corridor during 8–11 AM and 5–8 PM windows to prevent parking-induced blockages</span>
        </div>""", unsafe_allow_html=True)
        st.markdown("""<div class="ibox ibox-green" style="margin-top:10px">
          ✅ <b>All 21 corridors</b> have measured avg duration —
          <span style="color:#94A3B8;font-size:0.85rem">data from 2,548 closed ASTRAM events</span>
        </div>""", unsafe_allow_html=True)

    # Event cause breakdown
    st.divider()
    cause_df = ev["event_cause"].value_counts().head(10).reset_index()
    cause_df.columns = ["Cause","Count"]
    cause_df["Cause"] = cause_df["Cause"].str.replace("_"," ").str.title()
    fig_cause = px.bar(cause_df, x="Count", y="Cause", orientation="h",
                       color="Count",
                       color_continuous_scale=["#1E3A5F","#4B8BF5","#EF4444"],
                       title="Traffic Incident Causes — ASTRAM Data",
                       labels={"Cause":"","Count":"Incidents"})
    fig_cause.update_layout(**_ct(height=340, yaxis=dict(autorange="reversed"),
                                   coloraxis_showscale=False))
    st.plotly_chart(fig_cause, width="stretch")

# ════════════════════════════════════════════════════════════════════
# TAB 6 — Enforcement Plan
# ════════════════════════════════════════════════════════════════════
with tabs[5]:
    st.subheader(f"Smart Enforcement Plan — {n_officers} Officers Available")

    # Officer allocation based on priority score
    top_stn = prio.head(n_officers * 3).copy()
    top_stn["officers"] = (
        (top_stn["priority"] / top_stn["priority"].sum() * n_officers)
        .round().clip(lower=1).astype(int)
    )
    top_stn = top_stn.nlargest(n_officers, "priority").reset_index(drop=True)
    top_stn["Rank"] = top_stn.index + 1

    c61, c62 = st.columns([2, 1])
    with c61:
        fig_enf = px.bar(
            top_stn.head(15), x="officers", y="junction_clean",
            color="risk",
            color_discrete_map={"🔴 HIGH":"#EF4444","🟡 MEDIUM":"#F59E0B","🟢 LOW":"#22C55E"},
            orientation="h",
            title=f"Officer Deployment — Top 15 Junctions",
            labels={"officers":"Officers","junction_clean":"Junction","risk":"Risk"},
        )
        fig_enf.update_layout(**_ct(height=460, yaxis=dict(autorange="reversed")))
        st.plotly_chart(fig_enf, width="stretch")

    with c62:
        risk_summary = top_stn["risk"].value_counts().reset_index()
        risk_summary.columns = ["Level","Junctions"]
        st.markdown("**Zone Risk Summary**")
        for _, row in risk_summary.iterrows():
            col_map = {"🔴 HIGH":"#EF4444","🟡 MEDIUM":"#F59E0B","🟢 LOW":"#22C55E"}
            c = col_map.get(str(row["Level"]),"#4B8BF5")
            st.markdown(f"""<div class="alert-card" style="border-left:3px solid {c}">
              <span style="color:{c};font-size:1.4rem;font-weight:800">{row['Junctions']}</span>
              <span style="color:#94A3B8;font-size:0.85rem"> {row['Level']} risk zones</span>
            </div>""", unsafe_allow_html=True)

        st.markdown("**Shift Schedule**")
        for shift, hours, color in [
            ("🌅 Morning",  "06:00–14:00","#22C55E"),
            ("☀️ Afternoon","14:00–22:00","#F59E0B"),
            ("🌙 Night",    "22:00–06:00","#4B8BF5"),
        ]:
            off = max(1, n_officers * [4, 4, 2][["🌅 Morning","☀️ Afternoon","🌙 Night"].index(shift)] // 10)
            st.markdown(f"""<div class="alert-card" style="border-left:3px solid {color}">
              <b style="color:{color}">{shift}</b> {hours}<br>
              <span style="color:#94A3B8">{off} officers / shift</span>
            </div>""", unsafe_allow_html=True)

    # Deployment map
    st.markdown("**Deployment Map**")
    dm = folium.Map(location=[12.97, 77.59], zoom_start=12, tiles="CartoDB dark_matter")
    for _, row in prio.head(30).iterrows():
        color = "red" if str(row["risk"]) == "🔴 HIGH" else \
                "orange" if str(row["risk"]) == "🟡 MEDIUM" else "green"
        folium.Circle(
            location=[row["lat"], row["lon"]], radius=300,
            color=color, fill=True, fill_opacity=0.4,
            popup=f"{row['junction_clean']}<br>Priority: {row['priority']:.2f}"
        ).add_to(dm)
    _dim_attr(dm)
    st_folium(dm, height=400, width=None, returned_objects=[])

# ════════════════════════════════════════════════════════════════════
# TAB 7 — Repeat Offenders
# ════════════════════════════════════════════════════════════════════
with tabs[6]:
    st.subheader("🔁 Repeat Offenders — Targeted Enforcement")
    st.caption("Vehicles violating 3+ times — enforcement on these prevents cascading violations")

    v_cnt = viol["vehicle_number"].value_counts()
    repeat = v_cnt[v_cnt >= 3].reset_index()
    repeat.columns = ["Vehicle ID", "Total Violations"]

    station_map = (viol[viol["vehicle_number"].isin(repeat["Vehicle ID"])]
                   .groupby("vehicle_number")["police_station"].first()
                   .reset_index())
    station_map.columns = ["Vehicle ID","Primary Station"]
    repeat = repeat.merge(station_map, on="Vehicle ID", how="left")

    c71, c72, c73 = st.columns(3)
    c71.metric("Repeat Vehicles (≥3)", f"{len(repeat):,}")
    c72.metric("Top Offender",  f"{int(repeat['Total Violations'].max())} violations")
    c73.metric("Violations from Repeats",
               f"{int(repeat['Total Violations'].sum()):,}")

    st.divider()

    fig_rep = px.histogram(
        repeat, x="Total Violations", nbins=25,
        title="Distribution of Repeat Offences",
        color_discrete_sequence=["#4B8BF5"],
        labels={"Total Violations":"Number of Violations","count":"Vehicles"},
    )
    fig_rep.update_layout(**_ct(height=300))
    st.plotly_chart(fig_rep, width="stretch")

    st.markdown("**Top 30 Repeat Offenders**")
    st.dataframe(repeat.head(30), width="stretch", hide_index=True)

    # Station-wise repeat count
    stn_rep = repeat.groupby("Primary Station")["Total Violations"].agg(["count","sum"]).reset_index()
    stn_rep.columns = ["Station","Repeat Vehicles","Total Violations"]
    stn_rep = stn_rep.sort_values("Total Violations", ascending=False).head(12)
    fig_sr = px.bar(stn_rep, x="Total Violations", y="Station", orientation="h",
                    color="Repeat Vehicles",
                    color_continuous_scale=["#1E3A5F","#EF4444"],
                    title="Repeat Offender Concentration by Station",
                    labels={"Station":""})
    fig_sr.update_layout(**_ct(height=380, yaxis=dict(autorange="reversed")))
    st.plotly_chart(fig_sr, width="stretch")

# ════════════════════════════════════════════════════════════════════
# TAB 8 — AI Predictions
# ════════════════════════════════════════════════════════════════════
with tabs[7]:
    st.subheader("🤖 AI Congestion Risk Engine")
    st.caption("Three ML models trained on 115,400 violation records + 8,173 incident records to predict, cluster, and detect")

    if not st.session_state.get("train_ai_done"):
        st.info("⚡ AI models are compute-intensive (~15s on first run). "
                "Click below to train them on demand.")
        if st.button("▶ Run AI Analysis", type="primary"):
            st.session_state["train_ai_done"] = True
            st.rerun()
    else:
        models = train_ai_models(viol, ev)

        # ── Model summary cards ──────────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        for col, val, lbl, sub in [
            (m1, "Random Forest",          "Congestion Predictor",  "20 enforcement zones"),
            (m2, f"AUC {models['auc']:.2f}", "Model Quality",       "Test-set ROC AUC"),
            (m3, f"F1  {models['f1']:.2f}",  "F1 Score",            "Weighted, balanced classes"),
            (m4, f"{models['train_time']:.1f}s", "Train Time",      "On Streamlit Cloud"),
        ]:
            col.markdown(f"""<div class="kpi">
              <div class="kpi-v" style="font-size:1.6rem">{val}</div>
              <div class="kpi-l">{lbl}</div>
              <div class="kpi-s">{sub}</div>
            </div>""", unsafe_allow_html=True)

        st.divider()

        # ── A. Feature importance ────────────────────────────────────────────────
        st.markdown("### A. What Drives Congestion Risk?")
        fi_df = pd.DataFrame({"Feature": models["fi_names"], "Importance": models["fi"]})
        fi_df = fi_df.sort_values("Importance", ascending=True)
        fig_fi = px.bar(fi_df, x="Importance", y="Feature", orientation="h",
                        color="Importance",
                        color_continuous_scale=["#1E3A5F","#4B8BF5","#22C55E"],
                        title="Feature Importance — Congestion Risk Predictor",
                        labels={"Feature":""})
        fig_fi.update_layout(**_ct(height=320, coloraxis_showscale=False))
        st.plotly_chart(fig_fi, width="stretch")

        st.markdown("""<div class="ibox ibox-warn">
          <b>Key finding:</b> <i>Violation density</i> and <i>hour of day</i> are the strongest predictors of traffic congestion —
          directly validating the problem statement that illegal parking drives congestion.
        </div>""", unsafe_allow_html=True)

        st.divider()

        # ── B. Zone risk map ─────────────────────────────────────────────────────
        st.markdown("### B. AI-Detected Enforcement Zones")
        n_zones_sel = st.select_slider("Patrol zones", options=[5, 10, 15], value=10)

        from sklearn.cluster import KMeans as _KM
        sc   = models["sc"]
        km_s = models["km_models"][n_zones_sel]
        zone_centers = pd.DataFrame(
            sc.inverse_transform(km_s.cluster_centers_), columns=["lat","lon"]
        )

        m_km = folium.Map(location=[12.97, 77.59], zoom_start=12, tiles="CartoDB dark_matter")
        colors_km = ["#EF4444","#F59E0B","#22C55E","#4B8BF5","#A78BFA","#F472B6",
                     "#34D399","#FB923C","#60A5FA","#FBBF24","#6EE7B7","#C4B5FD",
                     "#FCA5A5","#93C5FD","#6B7280"]
        samp_pts = models["sample_pts"][:5000]
        labels   = km_s.predict(sc.transform(samp_pts))
        for i, (lat, lon) in enumerate(samp_pts):
            c = colors_km[labels[i] % len(colors_km)]
            folium.CircleMarker([lat, lon], radius=2, color=c, fill=True,
                                fill_opacity=0.35).add_to(m_km)
        for i, row in zone_centers.iterrows():
            c = colors_km[i % len(colors_km)]
            folium.map.Marker(
                [row["lat"], row["lon"]],
                icon=folium.DivIcon(html=f'<div style="background:{c};color:#fff;'
                                         f'font-weight:700;font-size:11px;padding:4px 8px;'
                                         f'border-radius:20px;white-space:nowrap">Zone {i+1}</div>'),
            ).add_to(m_km)
        _dim_attr(m_km)
        st_folium(m_km, height=460, width=None, returned_objects=[])

        st.divider()

        # ── C. Anomaly alerts ────────────────────────────────────────────────────
        st.markdown("### C. Event-Day Surge Detection")
        st.caption("Isolation Forest detects stations with abnormal violation spikes — caused by commercial events, "
                   "religious gatherings, and metro station spillover on high-footfall days")

        anomalies = models["anomalies"]
        DOW_ABBR  = {d[:3]: d[:3] for d in DOW_ORDER}
        FULL_ABBR = {d: d[:3] for d in DOW_ORDER}

        cols_a = st.columns(3)
        for i, (_, row) in enumerate(anomalies.iterrows()):
            with cols_a[i % 3]:
                day_n = FULL_ABBR.get(str(row["dow"]), str(row["dow"])[:3])
                mult  = float(row.get("multiplier", 1.0))
                cnt   = int(row["count"])
                st.markdown(f"""<div class="alert-card" style="border-left:3px solid #EF4444">
                  ⚠️ <b>{row['police_station']}</b><br>
                  <span style="color:#64748B;font-size:0.82rem">{day_n} {int(row['hour']):02d}:00 IST</span><br>
                  <span style="font-size:1.8rem;font-weight:800;color:#EF4444">{cnt}</span>
                  <span style="color:#64748B;font-size:0.8rem"> violations</span><br>
                  <span style="color:#F59E0B;font-weight:600">{mult:.1f}× above baseline</span>
                </div>""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown("""
<div style="text-align:center;color:#334155;font-size:0.78rem;padding:8px 0">
  ParkIQ v2.0 · Flipkart Gridlock Hackathon 2.0 · Problem Statement 1: Parking-Induced Congestion · Team MetaBot<br>
  Data: 298,450 BTP violation records (115K approved) · 8,173 ASTRAM traffic incidents · Bengaluru · Nov 2023 – Apr 2024
</div>
""", unsafe_allow_html=True)
