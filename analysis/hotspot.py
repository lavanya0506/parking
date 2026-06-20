"""
Hotspot detection: DBSCAN spatial clustering + junction-level aggregation.
"""
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

EARTH_RADIUS_KM = 6371.0

def dbscan_hotspots(df, eps_km=0.3, min_samples=50):
    """
    Cluster violation lat/lon with DBSCAN.
    eps_km: neighbourhood radius in km
    Returns df with 'cluster' column (-1 = noise)
    """
    coords = df[["latitude", "longitude"]].dropna().values
    eps_rad = eps_km / EARTH_RADIUS_KM
    db = DBSCAN(eps=eps_rad, min_samples=min_samples,
                algorithm="ball_tree", metric="haversine")
    labels = db.fit_predict(np.radians(coords))
    out = df.loc[df[["latitude","longitude"]].dropna().index].copy()
    out["cluster"] = labels
    return out

def cluster_summary(clustered_df):
    """Summary table of each cluster: centroid, count, top violation type."""
    valid = clustered_df[clustered_df["cluster"] >= 0]
    rows = []
    for cid, grp in valid.groupby("cluster"):
        rows.append({
            "cluster_id":  cid,
            "lat":         grp["latitude"].mean(),
            "lon":         grp["longitude"].mean(),
            "count":       len(grp),
            "top_violation": grp["primary_violation"].mode()[0],
            "top_vehicle": grp["vehicle_type"].mode()[0] if "vehicle_type" in grp else "N/A",
            "police_station": grp["police_station"].mode()[0] if "police_station" in grp else "N/A",
        })
    return pd.DataFrame(rows).sort_values("count", ascending=False).reset_index(drop=True)

def junction_stats(df):
    """Per-junction violation stats."""
    junc = df[df["junction_clean"] != "No Junction"]
    grp = junc.groupby("junction_clean").agg(
        total       = ("id","count"),
        lat         = ("latitude","mean"),
        lon         = ("longitude","mean"),
        peak_hour   = ("hour", lambda x: x.mode()[0]),
        top_vehicle = ("vehicle_type", lambda x: x.mode()[0]),
        police_stn  = ("police_station", lambda x: x.mode()[0]),
    ).reset_index().sort_values("total", ascending=False)
    return grp

def top_areas(df, n=20):
    """Top n areas by violation count using 4-decimal lat/lon rounding."""
    df2 = df.copy()
    df2["area"] = df2["latitude"].round(3).astype(str) + "," + df2["longitude"].round(3).astype(str)
    return df2.groupby("area").agg(
        count=("id","count"),
        lat=("latitude","mean"),
        lon=("longitude","mean"),
        top_violation=("primary_violation", lambda x: x.mode()[0]),
    ).sort_values("count", ascending=False).head(n).reset_index()
