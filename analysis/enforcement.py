"""
Enforcement Priority Scoring and Patrol Optimization.
"""
import pandas as pd
import numpy as np

def enforcement_priority(viol_df, event_df=None):
    """
    Composite priority score per junction:
    Score = 0.4*violation_freq + 0.3*peak_concentration + 0.2*incident_corr + 0.1*vehicle_severity
    """
    junc = viol_df[viol_df["junction_clean"] != "No Junction"].copy()
    total = len(junc)

    grp = junc.groupby("junction_clean").agg(
        count        = ("id","count"),
        lat          = ("latitude","mean"),
        lon          = ("longitude","mean"),
        peak_hour    = ("hour", lambda x: x.mode()[0]),
        police_stn   = ("police_station", lambda x: x.mode()[0]),
    ).reset_index()

    # Normalised violation frequency
    grp["freq_score"] = grp["count"] / grp["count"].max()

    # Peak concentration: how concentrated in peak hours (8-11 AM)?
    peak = junc[junc["hour"].between(8, 11)]
    peak_grp = peak.groupby("junction_clean").size().rename("peak_count")
    grp = grp.merge(peak_grp, on="junction_clean", how="left")
    grp["peak_count"] = grp["peak_count"].fillna(0)
    grp["peak_score"] = grp["peak_count"] / (grp["count"] + 1)

    # Vehicle severity score (heavier vehicle = more impact)
    severity_map = {
        "CAR": 1, "SCOOTER": 0.5, "MOTOR CYCLE": 0.5,
        "PASSENGER AUTO": 0.7, "MAXI-CAB": 1.5, "LGV": 2,
        "GOODS AUTO": 0.8, "PRIVATE BUS": 2.5, "TANKER": 3,
        "TRUCK": 3, "MOPED": 0.4,
    }
    junc["severity"] = junc["vehicle_type"].map(severity_map).fillna(1)
    sev_grp = junc.groupby("junction_clean")["severity"].mean().rename("avg_severity")
    grp = grp.merge(sev_grp, on="junction_clean", how="left")
    grp["sev_score"] = grp["avg_severity"] / grp["avg_severity"].max()

    # Incident correlation via police station
    if event_df is not None:
        e = event_df.groupby("police_station").size().rename("incidents")
        v = junc.groupby(["junction_clean","police_station"]).size().reset_index(name="cnt")
        v2 = v.merge(e.reset_index(), on="police_station", how="left")
        corr = v2.groupby("junction_clean")["incidents"].first().fillna(0)
        corr = (corr / corr.max()).rename("inc_score")
        grp = grp.merge(corr, on="junction_clean", how="left")
        grp["inc_score"] = grp["inc_score"].fillna(0)
    else:
        grp["inc_score"] = 0

    # Composite score
    grp["priority_score"] = (
        0.40 * grp["freq_score"] +
        0.30 * grp["peak_score"] +
        0.20 * grp["inc_score"] +
        0.10 * grp["sev_score"]
    )
    grp["priority_rank"] = grp["priority_score"].rank(ascending=False).astype(int)
    grp["alert_level"] = pd.cut(
        grp["priority_score"],
        bins=[0, 0.3, 0.6, 1.0],
        labels=["🟢 LOW", "🟡 MEDIUM", "🔴 HIGH"]
    )
    return grp.sort_values("priority_score", ascending=False).reset_index(drop=True)


def patrol_schedule(priority_df, n_officers=10):
    """
    Given N officers, generate optimal hourly patrol assignments.
    Greedy: assign each officer to highest-priority unserved zone.
    """
    top = priority_df.head(n_officers * 3).copy()
    # Peak hours for each zone (violations by hour)
    hours = [
        {"hour_range": "08:00-10:00", "label": "Morning Rush"},
        {"hour_range": "10:00-12:00", "label": "Late Morning"},
        {"hour_range": "00:00-03:00", "label": "Night Drive"},
    ]
    schedule = []
    assigned = 0
    for _, zone in top.iterrows():
        if assigned >= n_officers:
            break
        shift = hours[assigned % 3]
        schedule.append({
            "Officer": f"Officer-{assigned+1:02d}",
            "Zone": zone["junction_clean"],
            "Police Station": zone["police_stn"],
            "Shift": shift["hour_range"],
            "Shift Type": shift["label"],
            "Expected Violations": int(zone["count"] // 5),
            "Priority": zone["alert_level"],
            "Score": round(zone["priority_score"], 3),
        })
        assigned += 1
    return pd.DataFrame(schedule)
