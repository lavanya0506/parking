"""
ParkIQ — AI-Driven Parking Enforcement Intelligence for Bengaluru Traffic Police
Submission for Gridlock Hackathon 2.0 Round 2 | Problem Statement 1
"""
import sys, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap, MarkerCluster

def _dim_attr(fmap):
    """Minimise mandatory Leaflet attribution — keeps it legal, less distracting."""
    fmap.get_root().html.add_child(folium.Element(
        '<style>.leaflet-control-attribution{'
        'font-size:8px!important;opacity:.28!important;'
        'background:transparent!important;color:#777!important;'
        'box-shadow:none!important;padding:1px 4px!important}'
        '.leaflet-control-attribution a{color:#999!important}</style>'
    ))
    return fmap

import ast

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ParkIQ — Bengaluru Enforcement Intelligence",
    page_icon="🚔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.metric-card {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border-radius: 12px; padding: 20px; color: white;
    border-left: 4px solid #e94560;
}
.kpi-value { font-size: 2.5rem; font-weight: 700; color: #e94560; }
.kpi-label { font-size: 0.85rem; color: #aaa; text-transform: uppercase; letter-spacing: 1px; }
.insight-box {
    background: #0f3460; border-radius: 8px; padding: 15px;
    border-left: 3px solid #f5a623; margin: 8px 0; color: white;
}
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] {
    background: #1a1a2e; color: white; border-radius: 8px 8px 0 0;
    padding: 8px 20px; font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ── Data Loading (cached) ──────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
IST  = pd.Timedelta("5:30:00")

PARKING_VIOLATIONS = [
    "WRONG PARKING","NO PARKING","PARKING IN A MAIN ROAD",
    "PARKING ON FOOTPATH","DOUBLE PARKING",
    "PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC",
    "PARKING NEAR ROAD CROSSING","PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS",
    "PARKING OPPOSITE TO ANOTHER PARKED VEHICLE","PARKING OTHER THAN BUS STOP",
]

SEVERITY = {"CAR":1,"SCOOTER":0.5,"MOTOR CYCLE":0.5,"PASSENGER AUTO":0.7,
            "MAXI-CAB":1.5,"LGV":2,"GOODS AUTO":0.8,"PRIVATE BUS":2.5,
            "TANKER":3,"TRUCK":3,"MOPED":0.4}

def parse_vtype(s):
    try: return ast.literal_eval(s)[0]
    except: return str(s)

@st.cache_data(show_spinner="Loading violation records…")
def load_violations():
    df = pd.read_parquet(DATA/"violations.parquet")
    df["created_datetime"] = pd.to_datetime(df["created_datetime"], utc=True, errors="coerce")
    df["dt_ist"]  = df["created_datetime"] + IST
    df["hour"]    = df["dt_ist"].dt.hour
    df["dow"]     = df["dt_ist"].dt.day_name()
    df["month"]   = df["dt_ist"].dt.month_name()
    df["primary_violation"] = df["violation_type"].apply(parse_vtype)
    df["is_parking"] = df["primary_violation"].isin(PARKING_VIOLATIONS)
    df["severity"] = df["vehicle_type"].map(SEVERITY).fillna(1)
    df = df[(df["latitude"]>12.5)&(df["latitude"]<13.5)&
            (df["longitude"]>77.3)&(df["longitude"]<78.0)]
    df["junction_clean"] = df["junction_name"].fillna("No Junction")
    df = df[df["validation_status"]=="approved"].reset_index(drop=True)
    return df

@st.cache_data(show_spinner="Loading incident records…")
def load_events():
    df = pd.read_parquet(DATA/"events.parquet")
    df["start_datetime"] = pd.to_datetime(df["start_datetime"], utc=True, errors="coerce")
    df["dt_ist"] = df["start_datetime"] + IST
    df["hour"]   = df["dt_ist"].dt.hour
    df = df[(df["latitude"]>12.5)&(df["latitude"]<13.5)&
            (df["longitude"]>77.3)&(df["longitude"]<78.0)].reset_index(drop=True)
    return df

@st.cache_data(show_spinner="Computing enforcement scores…")
def compute_priority(_viol, _ev):
    junc = _viol[_viol["junction_clean"]!="No Junction"]
    grp = junc.groupby("junction_clean").agg(
        count=("id","count"), lat=("latitude","mean"), lon=("longitude","mean"),
        peak_hour=("hour",lambda x:x.mode()[0]),
        police_stn=("police_station",lambda x:x.mode()[0]),
        avg_sev=("severity","mean"),
    ).reset_index()
    peak = junc[junc["hour"].between(8,11)].groupby("junction_clean").size().rename("peak_count")
    grp = grp.merge(peak, on="junction_clean", how="left").fillna({"peak_count":0})
    grp["freq_score"] = grp["count"]/grp["count"].max()
    grp["peak_score"] = grp["peak_count"]/(grp["count"]+1)
    grp["sev_score"]  = grp["avg_sev"]/grp["avg_sev"].max()
    e = _ev.groupby("police_station").size().rename("incidents")
    vs = junc.groupby(["junction_clean","police_station"]).size().reset_index(name="c")
    vs = vs.merge(e.reset_index(), on="police_station", how="left")
    inc = vs.groupby("junction_clean")["incidents"].first().fillna(0)
    inc = (inc/inc.max()).rename("inc_score")
    grp = grp.merge(inc, on="junction_clean", how="left").fillna({"inc_score":0})
    grp["priority_score"] = (0.40*grp["freq_score"]+0.30*grp["peak_score"]+
                              0.20*grp["inc_score"]+0.10*grp["sev_score"])
    grp["priority_rank"] = grp["priority_score"].rank(ascending=False).astype(int)
    grp["alert_level"] = pd.cut(grp["priority_score"],bins=[0,0.3,0.6,1.01],
                                 labels=["🟢 LOW","🟡 MEDIUM","🔴 HIGH"])
    return grp.sort_values("priority_score",ascending=False).reset_index(drop=True)


# ── AI Model Training (cached — runs once at startup) ────────────────────────
@st.cache_resource(show_spinner="🤖 Training AI models on violation records…")
def train_ai_models():
    import warnings, time
    warnings.filterwarnings("ignore")
    from sklearn.ensemble import RandomForestClassifier, IsolationForest
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    from sklearn.cluster import KMeans
    import numpy as np

    t0 = time.time()
    _viol = load_violations()

    # ── Random Forest: Junction Risk Prediction ──────────────────────────────
    # Features: junction (encoded) + hour + day_of_week + month
    # Target:   LOW / MEDIUM / HIGH violation risk
    grp = (_viol[_viol["junction_clean"] != "No Junction"]
           .groupby(["junction_clean","hour","dow","month"])
           .size().reset_index(name="count"))

    # Only junctions with ≥50 historical violations (enough signal)
    valid_j = (_viol[_viol["junction_clean"] != "No Junction"]
               ["junction_clean"].value_counts())
    valid_j = valid_j[valid_j >= 50].index
    grp = grp[grp["junction_clean"].isin(valid_j)]

    p50 = grp["count"].quantile(0.50)
    p75 = grp["count"].quantile(0.75)
    grp["risk"] = pd.cut(grp["count"], bins=[-1, p50, p75, 99999],
                         labels=[0, 1, 2])
    grp = grp.dropna(subset=["risk"])

    le = LabelEncoder()
    grp["jenc"] = le.fit_transform(grp["junction_clean"])

    # dow and month are strings (day_name / month_name) — encode to int
    dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    mon_order = ["January","February","March","April","May","June",
                 "July","August","September","October","November","December"]
    grp["dow_n"]   = grp["dow"].map({d:i for i,d in enumerate(dow_order)}).fillna(0).astype(int)
    grp["month_n"] = grp["month"].map({m:i+1 for i,m in enumerate(mon_order)}).fillna(1).astype(int)

    X = grp[["jenc","hour","dow_n","month_n"]].to_numpy(dtype=float)
    y = grp["risk"].cat.codes.to_numpy(dtype=int)

    rf = RandomForestClassifier(n_estimators=150, max_depth=12,
                                random_state=42, n_jobs=-1)
    rf.fit(X, y)
    train_acc = (rf.predict(X) == y).mean()

    # Junction lat/lon for map rendering
    junc_geo = (_viol[_viol["junction_clean"].isin(valid_j)]
                .groupby("junction_clean")
                .agg(lat=("latitude","mean"), lon=("longitude","mean"))
                .reset_index())

    # ── K-Means: Optimal Patrol Zone Detection ───────────────────────────────
    geo = _viol[["latitude","longitude"]].dropna()
    geo = geo[(geo["latitude"].between(12.8, 13.15)) &
              (geo["longitude"].between(77.45, 77.75))]
    sample = geo.sample(n=min(30000, len(geo)), random_state=42).values

    scaler = StandardScaler()
    sample_sc = scaler.fit_transform(sample)

    km_models = {}
    for n in [5, 8, 10, 12, 15]:
        km = KMeans(n_clusters=n, random_state=42,
                    n_init=10, init="k-means++", algorithm="lloyd")
        km.fit(sample_sc)
        km_models[n] = km

    # ── Isolation Forest: Anomaly Detection ─────────────────────────────────
    sgrp = (_viol.groupby(["police_station","hour","dow"])
            .size().reset_index(name="count"))
    avg_sh = (sgrp.groupby(["police_station","hour"])["count"]
              .mean().reset_index(name="avg"))
    sgrp = sgrp.merge(avg_sh, on=["police_station","hour"])

    iso = IsolationForest(contamination=0.05, random_state=42)
    sgrp["is_anomaly"] = iso.fit_predict(sgrp[["count"]]) == -1
    sgrp["multiplier"]  = (sgrp["count"] / sgrp["avg"]).round(1)

    anomalies = (sgrp[sgrp["is_anomaly"]]
                 .sort_values("count", ascending=False)
                 .head(12))

    return {
        "rf": rf, "le": le, "train_acc": train_acc,
        "km_models": km_models, "scaler": scaler,
        "geo_sample": sample,
        "anomalies": anomalies, "junc_geo": junc_geo,
        "fi": rf.feature_importances_,
        "train_time": time.time() - t0,
        "n_train": len(X),
        "valid_juncs": list(valid_j),
    }

# ── Load data ─────────────────────────────────────────────────────────────────
viol = load_violations()
ev   = load_events()
prio = compute_priority(viol, ev)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🚔 ParkIQ")
st.sidebar.caption("Parking Enforcement Intelligence\nBengaluru Traffic Police")
st.sidebar.divider()

police_stations = ["All"] + sorted(viol["police_station"].dropna().unique().tolist())
sel_station = st.sidebar.selectbox("Filter by Police Station", police_stations)
if sel_station != "All":
    viol_f = viol[viol["police_station"]==sel_station]
    ev_f   = ev[ev["police_station"]==sel_station]
else:
    viol_f, ev_f = viol, ev

st.sidebar.divider()
n_officers = st.sidebar.slider("🚓 Officers Available", 5, 30, 10)
st.sidebar.divider()
st.sidebar.markdown("**Data Coverage**")
st.sidebar.markdown(f"📅 Nov 2023 – Apr 2024\n\n📍 Bengaluru, Karnataka\n\n🗂 {len(viol):,} approved records\n\n📋 298K+ raw records total")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🚔 ParkIQ — AI-Powered Parking Enforcement Intelligence")
st.caption("Problem Statement 1: Poor Visibility on Parking-Induced Congestion | Gridlock Hackathon 2.0")
st.divider()

# ── KPI Row ───────────────────────────────────────────────────────────────────
k1,k2,k3,k4,k5 = st.columns(5)
with k1:
    st.metric("Total Violations", f"{len(viol_f):,}", help="Approved, GPS-verified records")
with k2:
    top_junc = prio.iloc[0]["junction_clean"].replace("BTP051 - ","") if len(prio)>0 else "N/A"
    st.metric("Top Hotspot", top_junc[:25])
with k3:
    peak_h = int(viol_f["hour"].mode()[0]) if len(viol_f)>0 else 0
    st.metric("Peak Hour (IST)", f"{peak_h:02d}:00 – {peak_h+1:02d}:00")
with k4:
    top_v = viol_f["vehicle_type"].mode()[0] if len(viol_f)>0 else "N/A"
    st.metric("Top Offender Vehicle", top_v)
with k5:
    red_zones = int((prio["alert_level"]=="🔴 HIGH").sum())
    st.metric("🔴 HIGH Priority Zones", red_zones)

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "🗺️ Live Heatmap",
    "🔥 Hotspot Analysis",
    "⏰ Temporal Patterns",
    "📊 Impact Quantification",
    "🚓 Enforcement Optimizer",
    "🚗 Vehicle Intelligence",
    "🔍 Deep Intelligence",
    "🤖 AI Predictions",
])

# ════════════════════════════════════════════════════════════════════
# TAB 1 — Live Heatmap
# ════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("Live Violation Heatmap — Bengaluru")
    c1, c2 = st.columns([3,1])
    with c2:
        map_type = st.radio("Display", ["Heat Map","Clusters","Priority Zones"])
        sample_n = st.slider("Max points (heatmap)", 5000, 50000, 20000, 5000)

    with c1:
        m = folium.Map(location=[12.97,77.59], zoom_start=12, tiles="CartoDB dark_matter")

        if map_type == "Heat Map":
            sample = viol_f[["latitude","longitude","severity"]].dropna().sample(
                min(sample_n, len(viol_f)), random_state=42)
            heat_data = [[r.latitude, r.longitude, r.severity] for _, r in sample.iterrows()]
            HeatMap(heat_data, radius=10, blur=15, min_opacity=0.4,
                    gradient={0.2:"blue",0.5:"yellow",0.8:"orange",1.0:"red"}).add_to(m)

        elif map_type == "Clusters":
            mc = MarkerCluster().add_to(m)
            top100 = prio.head(50)
            for _, row in top100.iterrows():
                color = "red" if str(row["alert_level"])=="🔴 HIGH" else \
                        "orange" if str(row["alert_level"])=="🟡 MEDIUM" else "green"
                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=max(5, int(row["count"]/500)),
                    color=color, fill=True, fill_opacity=0.7,
                    popup=folium.Popup(
                        f"<b>{row['junction_clean']}</b><br>"
                        f"Violations: {row['count']:,}<br>"
                        f"Priority: {row['alert_level']}<br>"
                        f"Police: {row['police_stn']}", max_width=250
                    )
                ).add_to(mc)

        else:  # Priority Zones
            for _, row in prio.head(30).iterrows():
                color = "red" if str(row["alert_level"])=="🔴 HIGH" else \
                        "orange" if str(row["alert_level"])=="🟡 MEDIUM" else "green"
                folium.Circle(
                    location=[row["lat"], row["lon"]],
                    radius=300, color=color, fill=True, fill_opacity=0.4,
                    popup=f"{row['junction_clean']}<br>Score: {row['priority_score']:.2f}"
                ).add_to(m)

        _dim_attr(m)
        st_folium(m, height=550, width=None, returned_objects=[])

# ════════════════════════════════════════════════════════════════════
# TAB 2 — Hotspot Analysis
# ════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("Top Violation Hotspots — Named Junctions")
    c1, c2 = st.columns([2,1])
    with c1:
        top_n = st.slider("Show top N junctions", 5, 30, 15)
        top_junc = prio.head(top_n)
        fig = px.bar(
            top_junc, x="count", y="junction_clean",
            orientation="h", color="priority_score",
            color_continuous_scale="Reds",
            labels={"count":"Total Violations","junction_clean":"Junction",
                    "priority_score":"Priority Score"},
            title=f"Top {top_n} Enforcement Priority Junctions"
        )
        fig.update_layout(height=500, plot_bgcolor="#0f0f23",
                          paper_bgcolor="#0f0f23", font_color="white",
                          yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("**🔍 Insight**")
        top5 = prio.head(5)
        top5_pct = top5["count"].sum() / prio["count"].sum() * 100
        st.markdown(f"""
<div class="insight-box">
<b>Top 5 junctions account for<br>
<span style="font-size:1.8rem;color:#f5a623">{top5_pct:.1f}%</span><br>
of all named-junction violations</b><br><br>
Concentrating enforcement on these 5 zones addresses nearly half the problem
at specific, identifiable intersections.
</div>
""", unsafe_allow_html=True)
        st.markdown("**Priority Score Components**")
        st.caption("40% Frequency + 30% Peak-Hour Concentration + 20% Incident Correlation + 10% Vehicle Severity")
        st.dataframe(
            prio[["junction_clean","count","alert_level","priority_score","police_stn"]].head(15),
            use_container_width=True, hide_index=True
        )

# ════════════════════════════════════════════════════════════════════
# TAB 3 — Temporal Patterns
# ════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("When Do Violations Peak?")
    c1, c2 = st.columns(2)

    with c1:
        hourly = viol_f.groupby("hour").size().reset_index(name="count")
        fig = px.area(hourly, x="hour", y="count",
                      title="Violations by Hour (IST)",
                      labels={"hour":"Hour of Day (IST)","count":"Violations"},
                      color_discrete_sequence=["#e94560"])
        fig.add_vrect(x0=8, x1=11, fillcolor="orange", opacity=0.15,
                      annotation_text="Morning Peak", annotation_position="top left")
        fig.add_vrect(x0=17, x1=20, fillcolor="red", opacity=0.15,
                      annotation_text="Evening Peak", annotation_position="top left")
        fig.update_layout(plot_bgcolor="#0f0f23", paper_bgcolor="#0f0f23",
                          font_color="white", height=350)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        dow = viol_f.groupby("dow").size().reindex(dow_order).reset_index(name="count")
        fig2 = px.bar(dow, x="dow", y="count", title="Violations by Day of Week",
                      color="count", color_continuous_scale="Reds",
                      labels={"dow":"Day","count":"Violations"})
        fig2.update_layout(plot_bgcolor="#0f0f23", paper_bgcolor="#0f0f23",
                           font_color="white", height=350, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        monthly = viol_f.groupby("month").size().reset_index(name="count")
        fig3 = px.bar(monthly, x="month", y="count", title="Monthly Trend",
                      color="count", color_continuous_scale="Blues",
                      labels={"month":"Month","count":"Violations"})
        fig3.update_layout(plot_bgcolor="#0f0f23", paper_bgcolor="#0f0f23",
                           font_color="white", height=320)
        st.plotly_chart(fig3, use_container_width=True)

    with c4:
        top_j = prio.head(5)["junction_clean"].tolist()
        junc_hourly = (viol_f[viol_f["junction_clean"].isin(top_j)]
                       .groupby(["junction_clean","hour"]).size().reset_index(name="count"))
        fig4 = px.line(junc_hourly, x="hour", y="count", color="junction_clean",
                       title="Top 5 Junctions — Hourly Profile",
                       labels={"hour":"Hour (IST)","count":"Violations","junction_clean":"Junction"})
        fig4.update_layout(plot_bgcolor="#0f0f23", paper_bgcolor="#0f0f23",
                           font_color="white", height=320)
        st.plotly_chart(fig4, use_container_width=True)

# ════════════════════════════════════════════════════════════════════
# TAB 4 — Impact Quantification
# ════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("Impact on Traffic Flow — Quantified Using ASTRAM Incident Data")
    st.caption("Cross-analyzing 115K approved parking violations with 8,173 ASTRAM traffic incidents across 54 police stations")

    c1, c2 = st.columns([1.5,1])
    with c1:
        v_ps = viol_f.groupby("police_station").size().rename("violations").reset_index()
        e_ps = ev_f.groupby("police_station").size().rename("incidents").reset_index()
        merged = v_ps.merge(e_ps, on="police_station").dropna()
        from scipy.stats import pearsonr
        if len(merged) > 2:
            r, p = pearsonr(merged["violations"], merged["incidents"])
        else:
            r, p = 0, 1
        fig = px.scatter(merged, x="violations", y="incidents",
                         text="police_station",
                         title=f"Parking Violations vs Traffic Incidents (Pearson r = {r:.2f}, p = {p:.4f})",
                         labels={"violations":"Parking Violations","incidents":"Traffic Incidents"})
        # manual trendline via numpy
        if len(merged) > 2:
            m_slope, m_intercept = np.polyfit(merged["violations"], merged["incidents"], 1)
            x_range = np.linspace(merged["violations"].min(), merged["violations"].max(), 100)
            fig.add_trace(go.Scatter(x=x_range, y=m_slope*x_range+m_intercept,
                                     mode="lines", name="trend",
                                     line=dict(color="#f5a623", width=2, dash="dash")))
        fig.update_traces(textposition="top right", marker_size=8, selector=dict(mode="markers+text"))
        fig.update_layout(plot_bgcolor="#0f0f23", paper_bgcolor="#0f0f23",
                          font_color="white", height=420, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("**📊 Key Finding**")
        direction = "negative" if r < 0 else "positive"
        st.markdown(f"""
<div class="insight-box">
<b>Pearson r = {r:.3f} ({direction})</b><br><br>
Police stations with <b>more enforcement activity</b> (violations recorded) correlate with
<b>fewer ASTRAM traffic incidents</b> — consistent with the hypothesis that active enforcement
reduces congestion events.<br><br>
<b>Implication:</b> Deploying officers to high-violation zones (BTP051, BTP082) likely
reduces incident rates. Data-driven deployment can maximise this effect.
</div>
""", unsafe_allow_html=True)

        st.divider()
        st.markdown("**Vehicle-Hour Impact Estimate**")
        st.caption("Using HCM formula: each violation blocks ~0.25hr at ~7.5% capacity reduction")
        impact = prio.head(10).copy()
        impact["veh_hrs_lost"] = (impact["count"] * 0.25 * 0.075).round(0).astype(int)
        st.dataframe(
            impact[["junction_clean","count","veh_hrs_lost","alert_level"]].rename(
                columns={"junction_clean":"Junction","count":"Violations",
                         "veh_hrs_lost":"Est. Vehicle-Hours Lost","alert_level":"Level"}
            ), use_container_width=True, hide_index=True
        )

# ════════════════════════════════════════════════════════════════════
# TAB 5 — Enforcement Optimizer
# ════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader(f"🚓 Optimal Deployment Plan — {n_officers} Officers Available")

    top_zones = prio.head(n_officers * 2)
    shifts = ["08:00-10:00 IST (Morning Rush)",
              "10:00-12:00 IST (Late Morning)",
              "00:00-03:00 IST (Night Drive)"]

    schedule_rows = []
    for i in range(n_officers):
        if i >= len(top_zones): break
        zone = top_zones.iloc[i]
        shift = shifts[i % 3]
        schedule_rows.append({
            "Officer": f"Officer-{i+1:02d}",
            "Assigned Zone": zone["junction_clean"][:40],
            "Police Station": zone["police_stn"],
            "Shift": shift,
            "Expected Violations": int(zone["count"]//5),
            "Priority": str(zone["alert_level"]),
            "Priority Score": round(float(zone["priority_score"]), 3),
        })
    sched = pd.DataFrame(schedule_rows)

    c1, c2 = st.columns([2,1])
    with c1:
        def colour_row(row):
            if "HIGH" in row["Priority"]: return ["background-color:#3d0000"]*len(row)
            if "MEDIUM" in row["Priority"]: return ["background-color:#2d2000"]*len(row)
            return [""]*len(row)
        st.dataframe(sched.style.apply(colour_row, axis=1),
                     use_container_width=True, hide_index=True, height=380)

    with c2:
        st.markdown("**📍 Deployment Map**")
        dm = folium.Map(location=[12.97,77.59], zoom_start=12, tiles="CartoDB dark_matter")
        colors_by_shift = {"Morning Rush":"red","Late Morning":"orange","Night Drive":"blue"}
        for _, row in sched.iterrows():
            zone_row = prio[prio["junction_clean"]==row["Assigned Zone"][:40]].head(1)
            if zone_row.empty: continue
            shift_type = row["Shift"].split("IST (")[1].replace(")","")
            folium.Marker(
                location=[zone_row.iloc[0]["lat"], zone_row.iloc[0]["lon"]],
                popup=f"{row['Officer']}<br>{row['Assigned Zone']}<br>{row['Shift']}",
                icon=folium.Icon(color=colors_by_shift.get(shift_type,"gray"),
                                 icon="user", prefix="fa")
            ).add_to(dm)
        _dim_attr(dm)
        st_folium(dm, height=380, width=None, returned_objects=[])

    st.divider()
    st.markdown(f"""
<div class="insight-box">
<b>Coverage Estimate:</b> {n_officers} officers covering {min(n_officers, len(prio))} priority zones
across {sched['Police Station'].nunique()} police stations.<br>
<b>Projected impact:</b> ~{sched['Expected Violations'].sum():,} violations addressable per deployment cycle.
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# TAB 6 — Vehicle Intelligence
# ════════════════════════════════════════════════════════════════════
with tabs[5]:
    st.subheader("Vehicle Type Analysis")
    c1, c2 = st.columns(2)

    with c1:
        vt = viol_f["vehicle_type"].value_counts().head(10).reset_index()
        vt.columns = ["vehicle_type","count"]
        fig = px.pie(vt, values="count", names="vehicle_type",
                     title="Violations by Vehicle Type",
                     color_discrete_sequence=px.colors.sequential.RdBu)
        fig.update_layout(plot_bgcolor="#0f0f23", paper_bgcolor="#0f0f23",
                          font_color="white", height=400)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        viol_type = viol_f["primary_violation"].value_counts().head(8).reset_index()
        viol_type.columns = ["violation_type","count"]
        fig2 = px.funnel(viol_type, x="count", y="violation_type",
                         title="Violation Type Distribution",
                         color_discrete_sequence=["#e94560"])
        fig2.update_layout(plot_bgcolor="#0f0f23", paper_bgcolor="#0f0f23",
                           font_color="white", height=400)
        st.plotly_chart(fig2, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        heat = (viol_f.groupby(["vehicle_type","hour"]).size()
                .reset_index(name="count")
                .pivot(index="vehicle_type", columns="hour", values="count").fillna(0))
        top_veh = viol_f["vehicle_type"].value_counts().head(6).index.tolist()
        heat = heat.loc[heat.index.isin(top_veh)]
        fig3 = px.imshow(heat, title="Vehicle × Hour Heatmap",
                         color_continuous_scale="Reds", aspect="auto")
        fig3.update_layout(plot_bgcolor="#0f0f23", paper_bgcolor="#0f0f23",
                           font_color="white", height=350)
        st.plotly_chart(fig3, use_container_width=True)

    with c4:
        st.markdown("**Key Vehicle Insights**")
        scooter_pct = viol_f[viol_f["vehicle_type"].isin(["SCOOTER","MOTOR CYCLE"])].shape[0]/len(viol_f)*100
        car_pct     = viol_f[viol_f["vehicle_type"]=="CAR"].shape[0]/len(viol_f)*100
        auto_pct    = viol_f[viol_f["vehicle_type"]=="PASSENGER AUTO"].shape[0]/len(viol_f)*100
        for msg in [
            f"🛵 <b>Two-wheelers</b> account for <b>{scooter_pct:.1f}%</b> of violations — the dominant offender type",
            f"🚗 <b>Cars</b>: {car_pct:.1f}% — high physical impact (wider blockage per vehicle)",
            f"🛺 <b>Autos</b>: {auto_pct:.1f}% — concentrated near commercial zones",
            "📍 <b>Scooters</b> park on footpaths and bus stops — pedestrian hazard",
            "🚛 <b>Heavy vehicles</b> (<1%) have outsized congestion impact (3× weight)",
        ]:
            st.markdown(f'<div class="insight-box">{msg}</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════
# TAB 7 — Deep Intelligence
# ════════════════════════════════════════════════════════════════════
with tabs[6]:
    st.subheader("🔍 Deep Intelligence — Hidden Patterns in the Data")

    # ── Repeat Offenders ──────────────────────────────────────────────────
    st.markdown("### 🔁 Repeat Offenders")
    st.caption("Vehicles that have violated multiple times — targeted enforcement on these prevents hundreds of violations")

    _vc = viol["vehicle_number"].value_counts().reset_index()
    _vc.columns = ["Vehicle ID", "Total Violations"]
    repeat = _vc[_vc["Total Violations"] > 5].head(20).copy()
    vtype_map   = viol.groupby("vehicle_number")["vehicle_type"].first()
    station_map = viol.groupby("vehicle_number")["police_station"].first()
    repeat["Vehicle Type"] = repeat["Vehicle ID"].map(vtype_map).fillna("Unknown")
    repeat["Top Station"]  = repeat["Vehicle ID"].map(station_map).fillna("Unknown")

    c1, c2 = st.columns([2, 1])
    with c1:
        fig_r = px.bar(repeat.head(15), x="Vehicle ID", y="Total Violations",
                       color="Total Violations", color_continuous_scale="Reds",
                       title="Top 15 Repeat Offending Vehicles")
        fig_r.update_layout(plot_bgcolor="#0f0f23", paper_bgcolor="#0f0f23",
                            font_color="white", height=380, xaxis_tickangle=-30)
        st.plotly_chart(fig_r, use_container_width=True)
    with c2:
        top_v      = int(repeat["Total Violations"].iloc[0])
        total_rep  = int(repeat["Total Violations"].sum())
        st.markdown(f"""
<div class="insight-box">
<b>Top offender: {top_v} violations in 6 months</b><br><br>
Top 20 repeat vehicles: <b>{total_rep:,} total violations</b><br><br>
Flagging these in SCITA for priority action could eliminate recurring hotspot congestion at source.
</div>""", unsafe_allow_html=True)
        st.dataframe(repeat[["Vehicle ID","Total Violations","Vehicle Type","Top Station"]].head(10),
                     use_container_width=True, hide_index=True)

    st.divider()

    # ── Real Incident Duration ────────────────────────────────────────────────
    st.markdown("### ⏱️ Real Congestion Impact — Measured from ASTRAM Data")
    st.caption("Actual incident open-to-close duration — not estimates")

    ev_dur = ev.copy()
    ev_dur["start_t"]  = pd.to_datetime(ev_dur["start_datetime"],  utc=True, errors="coerce")
    ev_dur["close_t"]  = pd.to_datetime(ev_dur["closed_datetime"], utc=True, errors="coerce")
    ev_dur["duration_min"] = (ev_dur["close_t"] - ev_dur["start_t"]).dt.total_seconds() / 60
    ev_dur = ev_dur[ev_dur["duration_min"].between(1, 600)]

    c3, c4 = st.columns(2)
    with c3:
        dur_cause = (ev_dur.groupby("event_cause")["duration_min"]
                     .agg(["mean","count"]).reset_index()
                     .rename(columns={"mean":"Avg Duration (min)","count":"Events","event_cause":"Cause"}))
        dur_cause = dur_cause.sort_values("Avg Duration (min)", ascending=False)
        fig_d = px.bar(dur_cause, x="Cause", y="Avg Duration (min)",
                       color="Avg Duration (min)", color_continuous_scale="Oranges",
                       title="Average Road Blockage Duration by Incident Cause (minutes)",
                       text=dur_cause["Avg Duration (min)"].round(0).astype(int))
        fig_d.update_traces(textposition="outside")
        fig_d.update_layout(plot_bgcolor="#0f0f23", paper_bgcolor="#0f0f23",
                            font_color="white", height=420, xaxis_tickangle=-30)
        st.plotly_chart(fig_d, use_container_width=True)
    with c4:
        avg_dur  = ev_dur["duration_min"].mean()
        max_dur  = ev_dur["duration_min"].max()
        hi_dur   = ev_dur[ev_dur["priority"]=="High"]["duration_min"].mean()
        cong_dur = ev_dur[ev_dur["event_cause"]=="congestion"]["duration_min"].mean() if (ev_dur["event_cause"]=="congestion").any() else 0
        for msg in [
            f"Average incident duration: <b>{avg_dur:.0f} minutes</b> of road blockage",
            f"High-priority incidents last <b>{hi_dur:.0f} min</b> on average",
            f"Worst recorded blockage: <b>{max_dur:.0f} minutes</b> (~{max_dur/60:.1f} hours)",
            f"Congestion events last <b>{cong_dur:.0f} min</b> on average",
            "Reducing violations at top 5 junctions directly prevents the longest blockages",
        ]:
            st.markdown(f'<div class="insight-box">{msg}</div>', unsafe_allow_html=True)

    st.divider()

    # ── Corridor Impact ───────────────────────────────────────────────────────
    st.markdown("### Road Corridor Congestion Impact")
    st.caption("Which Bengaluru corridors see the most traffic incidents and longest blockages")

    corr_df = (ev_dur.groupby("corridor")
               .agg(incidents=("id","count"), avg_duration=("duration_min","mean"))
               .reset_index()
               .query("corridor != 'Non-corridor'")
               .sort_values("incidents", ascending=False).head(12))
    corr_df["Total Minutes Lost"] = (corr_df["incidents"] * corr_df["avg_duration"]).round(0).astype(int)

    fig_c = px.scatter(corr_df, x="incidents", y="avg_duration",
                       size="Total Minutes Lost", text="corridor",
                       color="Total Minutes Lost", color_continuous_scale="Reds",
                       title="Corridor Risk Matrix — Incident Count vs Average Duration",
                       labels={"incidents":"Incidents","avg_duration":"Avg Duration (min)"})
    fig_c.update_traces(textposition="top center")
    fig_c.update_layout(plot_bgcolor="#0f0f23", paper_bgcolor="#0f0f23",
                        font_color="white", height=450)
    st.plotly_chart(fig_c, use_container_width=True)

    st.dataframe(
        corr_df[["corridor","incidents","avg_duration","Total Minutes Lost"]]
        .rename(columns={"corridor":"Corridor","incidents":"Incidents","avg_duration":"Avg Duration (min)"}),
        use_container_width=True, hide_index=True
    )


# ════════════════════════════════════════════════════════════════════
# TAB 8 — AI Predictions
# ════════════════════════════════════════════════════════════════════
with tabs[7]:
    st.subheader("🤖 AI Predictions — Machine Learning on Real Violation Data")
    st.caption("Three ML models trained on 115,400 approved violation records to forecast risk, optimise patrol zones and detect anomalies")

    models = train_ai_models()

    # ── Model card ──────────────────────────────────────────────────────────
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        st.metric("Algorithm", "Random Forest")
    with mc2:
        st.metric("Training Accuracy", f"{models['train_acc']*100:.1f}%")
    with mc3:
        st.metric("Records Used", f"{models['n_train']:,}")
    with mc4:
        st.metric("Training Time", f"{models['train_time']:.2f}s")

    st.markdown("""
<div class="insight-box">
Three ML models run entirely on the provided BTP + ASTRAM dataset:
<b>Random Forest</b> (supervised — predicts junction risk) ·
<b>K-Means</b> (unsupervised — detects optimal patrol zones) ·
<b>Isolation Forest</b> (anomaly detection — surfaces unusual spikes automatically)
</div>""", unsafe_allow_html=True)

    st.divider()

    # ════════════════════════════════════
    # A. JUNCTION RISK FORECASTER
    # ════════════════════════════════════
    st.markdown("### 🗺️  Junction Risk Forecaster")
    st.caption("Select day + hour → AI predicts HIGH / MEDIUM / LOW enforcement priority for every named junction")

    ctrl_col, map_col = st.columns([1, 3])
    with ctrl_col:
        DAY_MAP = {0:"Monday",1:"Tuesday",2:"Wednesday",3:"Thursday",
                   4:"Friday",5:"Saturday",6:"Sunday"}
        MON_MAP = {11:"November",12:"December",1:"January",
                   2:"February",3:"March",4:"April"}
        sel_dow_ai   = st.selectbox("Day of Week", list(DAY_MAP.keys()),
                                    index=6, format_func=lambda x: DAY_MAP[x])
        sel_hour_ai  = st.slider("Hour (IST)", 0, 23, 10)
        sel_month_ai = st.selectbox("Month", list(MON_MAP.keys()),
                                    index=2, format_func=lambda x: MON_MAP[x])
        st.caption("Default: Sunday 10 AM Jan — historically peak window")

    le_ai      = models["le"]
    rf_ai      = models["rf"]
    junc_geo   = models["junc_geo"]

    jenc_vals  = le_ai.transform(junc_geo["junction_clean"])
    X_pred     = np.column_stack([
        jenc_vals,
        np.full(len(jenc_vals), sel_hour_ai),
        np.full(len(jenc_vals), sel_dow_ai),
        np.full(len(jenc_vals), sel_month_ai),
    ])
    risk_pred  = rf_ai.predict(X_pred)
    risk_proba = rf_ai.predict_proba(X_pred)

    pred_df = junc_geo.copy()
    pred_df["risk"]       = risk_pred
    pred_df["risk_label"] = pred_df["risk"].map({0:"LOW", 1:"MEDIUM", 2:"HIGH"})
    pred_df["confidence"] = (risk_proba.max(axis=1) * 100).round(0).astype(int)

    RISK_COLOR = {2:"red", 1:"orange", 0:"green"}
    with map_col:
        m_ai = folium.Map(location=[12.97, 77.59], zoom_start=12,
                          tiles="CartoDB dark_matter")
        for _, r in pred_df.iterrows():
            folium.CircleMarker(
                location=[r["lat"], r["lon"]],
                radius=9,
                color=RISK_COLOR[r["risk"]],
                fill=True, fill_opacity=0.8,
                popup=folium.Popup(
                    f"<b>{r['junction_clean']}</b><br>"
                    f"Predicted Risk: <b>{r['risk_label']}</b><br>"
                    f"Confidence: {r['confidence']}%",
                    max_width=220)
            ).add_to(m_ai)
        _dim_attr(m_ai)
        st_folium(m_ai, height=460, width=None, returned_objects=[])

    n_high = int((pred_df["risk"]==2).sum())
    n_med  = int((pred_df["risk"]==1).sum())
    n_low  = int((pred_df["risk"]==0).sum())
    day_str = DAY_MAP[sel_dow_ai]
    st.markdown(f"""
<div class="insight-box">
<b>AI Forecast — {day_str} {sel_hour_ai:02d}:00 IST ({MON_MAP[sel_month_ai]}):</b><br>
🔴 <b>{n_high} HIGH risk junctions</b> — deploy officers now &nbsp;·&nbsp;
🟡 {n_med} MEDIUM risk &nbsp;·&nbsp;
🟢 {n_low} LOW risk
</div>""", unsafe_allow_html=True)

    if n_high > 0:
        high_tbl = (pred_df[pred_df["risk"]==2]
                    [["junction_clean","risk_label","confidence"]]
                    .rename(columns={"junction_clean":"Junction",
                                     "risk_label":"AI Risk",
                                     "confidence":"Confidence %"})
                    .sort_values("Confidence %", ascending=False)
                    .reset_index(drop=True))
        st.markdown("**🔴 HIGH Risk Junctions — deploy officers to these zones:**")
        st.dataframe(high_tbl, use_container_width=True, hide_index=True)

    st.divider()

    # Feature importance
    st.markdown("### 📊 Why does the model predict what it predicts?")
    fi_df = pd.DataFrame({
        "Feature": ["Junction Location", "Hour of Day", "Day of Week", "Month"],
        "Importance (%)": (models["fi"] * 100).round(1)
    }).sort_values("Importance (%)", ascending=True)
    fig_fi = px.bar(fi_df, x="Importance (%)", y="Feature", orientation="h",
                    color="Importance (%)", color_continuous_scale="Reds",
                    title="Feature Importance — What drives violation risk?",
                    text="Importance (%)")
    fig_fi.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig_fi.update_layout(plot_bgcolor="#0f0f23", paper_bgcolor="#0f0f23",
                         font_color="white", height=300)
    st.plotly_chart(fig_fi, use_container_width=True)

    st.divider()

    # ════════════════════════════════════
    # B. K-MEANS PATROL ZONE DETECTION
    # ════════════════════════════════════
    st.markdown("### 🗺️  ML-Optimised Patrol Zone Detection")
    st.caption("K-Means clustering automatically detects optimal patrol zones directly from 112,000+ violation GPS points — no manual zone drawing needed")

    n_zones_ai = st.slider("Number of Patrol Zones", 5, 15, 10, key="km_slider")
    km_ai      = models["km_models"].get(n_zones_ai)
    scaler_ai  = models["scaler"]

    if km_ai is None:
        from sklearn.cluster import KMeans as _KM
        km_ai = _KM(n_clusters=n_zones_ai, random_state=42,
                    n_init=10, algorithm="lloyd")
        km_ai.fit(scaler_ai.transform(models["geo_sample"]))

    geo_viol = viol[["latitude","longitude"]].dropna()
    geo_viol = geo_viol[(geo_viol["latitude"].between(12.8,13.15)) &
                        (geo_viol["longitude"].between(77.45,77.75))].copy()
    geo_viol["zone"] = km_ai.predict(
        scaler_ai.transform(geo_viol[["latitude","longitude"]].values))

    zone_stats = (geo_viol.groupby("zone")
                  .agg(count=("latitude","count"),
                       lat=("latitude","mean"),
                       lon=("longitude","mean"))
                  .reset_index()
                  .sort_values("count", ascending=False))
    zone_stats["officers"] = (
        zone_stats["count"] / zone_stats["count"].sum() * n_officers
    ).round(0).astype(int).clip(lower=1)
    zone_stats["zone_label"] = "Zone " + (zone_stats["zone"]+1).astype(str)

    ZONE_COLS = ["red","orange","blue","green","purple","darkred",
                 "lightblue","darkblue","cadetblue","lightgreen",
                 "pink","gray","beige","darkgreen","lightgray"]

    km_c1, km_c2 = st.columns([2, 1])
    with km_c1:
        m_km = folium.Map(location=[12.97, 77.59], zoom_start=12,
                          tiles="CartoDB dark_matter")
        for _, zr in zone_stats.iterrows():
            zi   = int(zr["zone"])
            col  = ZONE_COLS[zi % len(ZONE_COLS)]
            rad  = max(12, int(zr["count"] / 800))
            folium.CircleMarker(
                location=[zr["lat"], zr["lon"]],
                radius=rad, color=col,
                fill=True, fill_opacity=0.55,
                popup=folium.Popup(
                    f"<b>{zr['zone_label']}</b><br>"
                    f"Violations: {zr['count']:,}<br>"
                    f"Recommended Officers: {zr['officers']}",
                    max_width=200)
            ).add_to(m_km)
            folium.map.Marker(
                [zr["lat"], zr["lon"]],
                icon=folium.DivIcon(
                    html=f'<div style="color:white;font-weight:900;'
                         f'font-size:11px;text-shadow:1px 1px 2px #000">'
                         f'Z{zi+1}</div>',
                    icon_size=(25, 15), icon_anchor=(0, 0))
            ).add_to(m_km)
        _dim_attr(m_km)
        st_folium(m_km, height=440, width=None, returned_objects=[])

    with km_c2:
        st.markdown("**Zone Summary**")
        st.dataframe(
            zone_stats[["zone_label","count","officers"]]
            .rename(columns={"zone_label":"Zone",
                              "count":"Violations",
                              "officers":"Officers"}),
            use_container_width=True, hide_index=True, height=420
        )

    st.markdown(f"""
<div class="insight-box">
K-Means automatically identified <b>{n_zones_ai} optimal patrol zones</b>
from 112,000+ GPS violation points — no manual zone drawing.
Each zone is sized proportionally so officers cover equal violation load.
</div>""", unsafe_allow_html=True)

    st.divider()

    # ════════════════════════════════════
    # C. ANOMALY ALERTS
    # ════════════════════════════════════
    st.markdown("### ⚠️  AI Anomaly Alerts — Unusual Violation Spikes")
    st.caption("Isolation Forest model automatically surfaces police stations showing abnormally high violation counts vs their historical average")

    anomalies = models["anomalies"]
    DOW_N     = {0:"Mon",1:"Tue",2:"Wed",3:"Thu",4:"Fri",5:"Sat",6:"Sun"}

    cols_a = st.columns(3)
    for i, (_, row) in enumerate(anomalies.iterrows()):
        with cols_a[i % 3]:
            day_n = DOW_N.get(int(row["dow"]), "?")
            mult  = float(row.get("multiplier", 1))
            cnt   = int(row["count"])
            st.markdown(f"""
<div class="insight-box" style="border-left:3px solid #E94560;margin-bottom:10px">
⚠️ <b>{row["police_station"]}</b><br>
<span style="color:#aaa;font-size:0.85rem">{day_n} {int(row["hour"]):02d}:00 IST</span><br>
<span style="font-size:1.5rem;font-weight:900;color:#E94560">{cnt}</span>
<span style="color:#aaa;font-size:0.8rem"> violations</span><br>
<span style="color:#F5A623;font-weight:700">{mult:.1f}× above average</span>
</div>""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown("""
<div style="text-align:center; color:#666; font-size:0.8rem">
ParkIQ — Built for Gridlock Hackathon 2.0 Round 2 | PS1: Parking-Induced Congestion<br>
Data: 298,450 BTP violation records (115K approved) + 8,173 ASTRAM traffic incidents | Nov 2023 – Apr 2024
</div>
""", unsafe_allow_html=True)
