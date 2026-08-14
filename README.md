# 🚔 ParkIQ — AI-Powered Parking Enforcement Intelligence




---

## How ParkIQ Solves Every PS Gap

| PS Gap | ParkIQ Solution | Key Metric |
|--------|----------------|------------|
| **No heatmap** of violations vs congestion | Live dual-overlay Folium map — violation heatmap + traffic incident markers | 87% of 1,49,462 parking violations within 500 m of a congestion hotspot (3.5× enrichment, p<0.0001) |
| **Reactive enforcement** — patrol-based, no intelligence | Smart Patrol Advisor — select day + hour → top 5 junctions to deploy *right now* | Covers commercial areas, metro stations (32 junctions), event-day surges |
| **Can't prioritize** enforcement zones | AI-scored priority for all 145 junctions → 28 HIGH · 52 MEDIUM · 65 LOW | r = 0.76 hourly correlation (p<0.0001) · ₹22 Cr monthly economic impact |

---

## Three-Pillar Proof (Parking → Congestion)

| Pillar | Evidence | Stat |
|--------|----------|------|
| **Spatial** | 87% of parking violations co-locate with traffic congestion hotspots | 3.5× enrichment over random baseline · χ²=6,892 · p<0.0001 |
| **Temporal** | Both violations and congestion peak 8–11 AM and 5–8 PM | Pearson r = 0.76 · p = 0.000012 · 24 hourly data points |
| **Economic** | 72 vehicle-hours lost/day across 150-day study period | ₹22 Crore/month at ₹650/hr vehicle delay cost |

---

## Dataset

---

## Dashboard — 8 Tabs

| Tab | What it shows | PS relevance |
|-----|--------------|--------------|
| 🗺️ Intelligence Map | Violation heatmap + congestion overlay | Directly solves "no heatmap" gap |
| 🔥 Parking Hotspots | Junction ranking · metro/commercial tags · risk pie | Zone prioritization |
| 🚦 Congestion Link | Three-pillar proof · 3.5× enrichment · r=0.76 | Core evidence |
| ⏰ Peak Time Analysis | Hour × day heatmap · monthly trend | Shift scheduling |
| 🛣️ Corridor Risk | 18 major corridors ranked by risk index | Road-level targeting |
| 🚓 Enforcement Plan | Smart Patrol Advisor · officer allocation map | Targeted deployment |
| 🔁 Repeat Offenders | 3,156 vehicles with 3+ violations | Predictive enforcement |
| 🤖 AI Predictions | RF (AUC 0.905) · K-Means zones · Isolation Forest anomalies | AI layer |

---

## AI Models

| Model | Purpose | Performance |
|-------|---------|-------------|
| Random Forest Classifier | Predict high-risk zone × hour × day | AUC **0.898** · F1 0.842 |
| K-Means (18 zones) | Spatial patrol zone clustering | 5/10/15 zone configs |
| Isolation Forest | Event-day surge detection | 14 anomalous spikes identified |

Top feature importances: Hour of day (0.441) → Violation density (0.328) — directly validates PS.

---

## Run Locally

```bash
git clone https://github.com/lavanya0506/parking.git
cd parkiq-gridlock
pip install -r requirements.txt
streamlit run app.py
```

---

## Key Numbers at a Glance

```
1,49,462 parking violations       |   8,450  traffic incidents
    145  junctions scored          |      28  HIGH-risk junctions
     32  metro-adjacent            |      38  commercial-area junctions
  3,156  repeat offenders          |    87%   spatial co-location
   0.76  Pearson r (hourly)        |   ₹22Cr  monthly economic impact
  0.898  Random Forest AUC         |   5.7min demo video (ParkIQ_Demo_v3.mp4)
```
