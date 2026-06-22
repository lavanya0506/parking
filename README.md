# 🚔 ParkIQ — AI-Powered Parking Enforcement Intelligence

**Flipkart Gridlock Hackathon 2.0 · Problem Statement 1: Parking-Induced Congestion · Team MetaBot**

> Live app: https://parkiq-gridlock-jqd9ewsbuxzbqpzvwzyggv.streamlit.app

---

## How ParkIQ Solves Every PS Gap

| PS Gap | ParkIQ Solution | Key Metric |
|--------|----------------|------------|
| **No heatmap** of violations vs congestion | Live dual-overlay Folium map — violation heatmap + ASTRAM incident markers | 91% of 8,173 incidents within 500 m of a violation cluster (3.7× enrichment, p<0.0001) |
| **Reactive enforcement** — patrol-based, no intelligence | Smart Patrol Advisor — select day + hour → top 5 junctions to deploy *right now* | Covers commercial areas, metro stations (35 junctions), event-day surges |
| **Can't prioritize** enforcement zones | AI-scored priority for all 167 junctions → 25 HIGH · 58 MEDIUM · 84 LOW | r = 0.79 hourly correlation (p<0.0001) · ₹17 Cr monthly economic impact |

---

## Three-Pillar Proof (Parking → Congestion)

| Pillar | Evidence | Stat |
|--------|----------|------|
| **Spatial** | 91% of ASTRAM incidents co-locate with violation clusters | 3.7× enrichment over random baseline · χ²=7,184 · p<0.0001 |
| **Temporal** | Both violations and incidents peak 8–11 AM and 5–8 PM | Pearson r = 0.79 · p = 0.000005 · 24 hourly data points |
| **Economic** | 65 vehicle-hours lost/day across 140-day study period | ₹17 Crore/month at ₹600/hr vehicle delay cost |

---

## Dataset

| Source | Records | Period |
|--------|---------|--------|
| BTP Parking Violations | 298,450 raw → **115,400 approved** | Nov 2023 – Apr 2024 |
| ASTRAM Traffic Incidents | **8,173 events** | Nov 2023 – Apr 2024 |

Both datasets cover **54 Bengaluru police stations** with GPS coordinates.

---

## Dashboard — 8 Tabs

| Tab | What it shows | PS relevance |
|-----|--------------|--------------|
| 🗺️ Intelligence Map | Violation heatmap + incident overlay | Directly solves "no heatmap" gap |
| 🔥 Parking Hotspots | Junction ranking · metro/commercial tags · risk pie | Zone prioritization |
| 🚦 Congestion Link | Three-pillar proof · 3.7× enrichment · r=0.79 | Core evidence |
| ⏰ Peak Time Analysis | Hour × day heatmap · monthly trend | Shift scheduling |
| 🛣️ Corridor Risk | 21 ASTRAM corridors ranked by risk index | Road-level targeting |
| 🚓 Enforcement Plan | Smart Patrol Advisor · officer allocation map | Targeted deployment |
| 🔁 Repeat Offenders | 2,823 vehicles with 3+ violations | Predictive enforcement |
| 🤖 AI Predictions | RF (AUC 0.905) · K-Means zones · Isolation Forest anomalies | AI layer |

---

## AI Models

| Model | Purpose | Performance |
|-------|---------|-------------|
| Random Forest Classifier | Predict high-risk zone × hour × day | AUC **0.905** · F1 0.855 |
| K-Means (20 zones) | Spatial patrol zone clustering | 5/10/15 zone configs |
| Isolation Forest | Event-day surge detection | 12 anomalous spikes identified |

Top feature importances: Hour of day (0.436) → Violation density (0.326) — directly validates PS.

---

## Run Locally

```bash
git clone https://github.com/BhuwanSKumar/parkiq-gridlock
cd parkiq-gridlock
pip install -r requirements.txt
streamlit run app.py
```

---

## Key Numbers at a Glance

```
115,400  approved BTP violations   |   8,173  ASTRAM incidents
    167  junctions scored          |      25  HIGH-risk junctions
     35  metro-adjacent            |      36  commercial-area junctions
  2,823  repeat offenders          |    91%   spatial co-location
   0.79  Pearson r (hourly)        |   ₹17Cr  monthly economic impact
  0.905  Random Forest AUC         |   5.7min demo video (ParkIQ_Demo_v3.mp4)
```

---

*ParkIQ v2.0 · Team MetaBot · NIT Durgapur*
