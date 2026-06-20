# 🚔 ParkIQ — AI-Powered Parking Enforcement Intelligence

**Gridlock Hackathon 2.0 Round 2 | Problem Statement 1: Parking-Induced Congestion**

> Real-time violation heatmaps, data-driven enforcement deployment, and quantified traffic impact — built on 298,450 BTP records and 8,173 ASTRAM traffic incidents from Bengaluru.

---

## 🎯 Problem Statement

Bengaluru Traffic Police lacks visibility into **where, when, and how severely** illegal parking disrupts traffic flow. Officers are deployed reactively, not proactively — leading to persistent congestion at known hotspots.

## 💡 Solution

ParkIQ is a Streamlit dashboard that transforms raw BTP violation data into **actionable enforcement intelligence**:

| Feature | Description |
|---|---|
| 🗺️ Live Heatmap | Violation density and severity across Bengaluru with 3 view modes |
| 🔥 Hotspot Analysis | Priority-scored junctions using 4-factor composite scoring |
| ⏰ Temporal Patterns | Hourly, daily, monthly violation profiles per junction |
| 📊 Impact Quantification | Cross-analysis with ASTRAM incident data + vehicle-hour loss estimates |
| 🚓 Enforcement Optimizer | Shift-wise patrol schedule for N officers across priority zones |
| 🚗 Vehicle Intelligence | Violation breakdown by vehicle type and time-of-day heatmap |

## 📊 Data

| Dataset | Size | Period |
|---|---|---|
| BTP Parking Violations | 298,450 records (115K approved) | Nov 2023 – Apr 2024 |
| ASTRAM Traffic Incidents | 8,173 events | Nov 2023 – Apr 2024 |

Both datasets cover exactly **54 police stations** across Bengaluru.

## 🔑 Key Findings

- **Top hotspot**: BTP051 - Safina Plaza (15,000+ violations)
- **Peak enforcement window**: 10:00 AM IST (morning rush)
- **Enforcement effect**: Stations with active enforcement show fewer ASTRAM incidents (r = -0.14)
- **Top 5 junctions** account for ~40% of all named-junction violations

## 🚀 Run Locally

```bash
git clone https://github.com/YOUR_USERNAME/parkiq
cd parkiq

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

streamlit run app.py
```

The app reads from `data/violations.parquet` and `data/events.parquet`. Original CSVs are available in the submission ZIP.

## 📁 Project Structure

```
parkiq/
├── app.py                  # Main Streamlit dashboard (6 tabs)
├── requirements.txt
├── data/
│   ├── violations.parquet  # 115K approved BTP violation records
│   └── events.parquet      # 8,173 ASTRAM traffic incidents
├── analysis/
│   ├── hotspot.py          # DBSCAN clustering + junction scoring
│   ├── impact.py           # Cross-dataset correlation analysis
│   └── enforcement.py      # Patrol optimizer
└── utils/
    └── data_loader.py      # Data loading utilities
```

## 🧮 Priority Score Formula

```
Priority Score = 0.40 x Frequency Score
              + 0.30 x Peak-Hour Concentration (8–11 AM)
              + 0.20 x Incident Correlation Score
              + 0.10 x Vehicle Severity Score
```

## 🛠 Tech Stack

Streamlit · Pandas · Plotly · Folium · SciPy · scikit-learn · PyArrow

## 📋 Submission

Gridlock Hackathon 2.0 — Round 2 | PS1: Parking-Induced Congestion, Bengaluru
