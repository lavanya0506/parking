"""
Impact quantification: cross-correlate violations with ASTRAM traffic events.
This answers PS1's hardest requirement: "quantify impact on traffic flow."
"""
import pandas as pd
import numpy as np
from scipy.stats import pearsonr

def station_level_correlation(viol_df, event_df):
    """
    Per police-station: violation count vs incident count.
    Returns correlation and station-level merged table.
    """
    v = viol_df.groupby("police_station").size().rename("violations")
    e = event_df.groupby("police_station").size().rename("incidents")
    merged = pd.DataFrame({"violations": v, "incidents": e}).dropna()
    if len(merged) > 2:
        r, p = pearsonr(merged["violations"], merged["incidents"])
    else:
        r, p = 0, 1
    merged["violation_rank"] = merged["violations"].rank(ascending=False).astype(int)
    merged["incident_rank"]  = merged["incidents"].rank(ascending=False).astype(int)
    return merged.reset_index(), round(r, 3), round(p, 4)

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    return R * 2 * np.arcsin(np.sqrt(a))

def violations_near_incidents(viol_df, event_df, radius_km=0.5, sample_events=500):
    """
    For a sample of events, count violations within radius_km and time_window_hrs.
    Returns: event rows with nearby_violations count.
    """
    ev_sample = event_df.dropna(subset=["latitude","longitude"]).head(sample_events).copy()
    counts = []
    for _, ev in ev_sample.iterrows():
        dist = haversine_distance(ev["latitude"], ev["longitude"],
                                  viol_df["latitude"].values, viol_df["longitude"].values)
        nearby = (dist <= radius_km).sum()
        counts.append(nearby)
    ev_sample["nearby_violations"] = counts
    return ev_sample

def throughput_impact_estimate(viol_df):
    """
    Estimate throughput reduction per junction using:
    - 1 blocking vehicle reduces effective lane width → capacity drop
    - Using HCM approximation: 5-10% capacity reduction per blocking vehicle
    - Duration proxy: average challan processing time (~15 min)
    """
    junc = viol_df[viol_df["junction_clean"] != "No Junction"]
    grp = junc.groupby("junction_clean").agg(
        total_violations = ("id","count"),
        lat = ("latitude","mean"),
        lon = ("longitude","mean"),
    ).reset_index()

    # Impact score: each violation blocks ~15 min, reduces throughput 5-10%
    grp["estimated_vehicle_hours_lost"] = grp["total_violations"] * 0.25 * 0.075
    grp["monthly_throughput_impact_pct"] = (
        grp["total_violations"] / grp["total_violations"].sum() * 100
    ).round(2)
    return grp.sort_values("estimated_vehicle_hours_lost", ascending=False)
