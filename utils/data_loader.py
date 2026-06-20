import pandas as pd
import numpy as np
import ast
from pathlib import Path

BASE = Path(__file__).parent.parent.parent  # flipkart_hackathon/

VIOL_PATH  = BASE / "jan to may police violation_anonymized791b166.csv"
EVENT_PATH = BASE / "Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv"

IST = pd.Timedelta("5:30:00")

# ── Violation types ──────────────────────────────────────────────────────────
PARKING_VIOLATIONS = [
    "WRONG PARKING", "NO PARKING", "PARKING IN A MAIN ROAD",
    "PARKING ON FOOTPATH", "DOUBLE PARKING",
    "PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC",
    "PARKING NEAR ROAD CROSSING",
    "PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS",
    "PARKING OPPOSITE TO ANOTHER PARKED VEHICLE",
    "PARKING OTHER THAN BUS STOP",
]

def parse_violation_list(s):
    try:
        return ast.literal_eval(s)
    except Exception:
        return [str(s)]

@pd.core.cache
def load_violations(approved_only=True):
    df = pd.read_csv(VIOL_PATH, low_memory=False)
    df["created_datetime"] = pd.to_datetime(df["created_datetime"], utc=True, errors="coerce")
    df["dt_ist"]  = df["created_datetime"] + IST
    df["hour"]    = df["dt_ist"].dt.hour
    df["dow"]     = df["dt_ist"].dt.day_name()
    df["month"]   = df["dt_ist"].dt.month_name()
    df["date"]    = df["dt_ist"].dt.date
    df["week"]    = df["dt_ist"].dt.isocalendar().week.astype(int)

    # Expand violation types
    df["viol_list"] = df["violation_type"].apply(parse_violation_list)
    df["primary_violation"] = df["viol_list"].apply(lambda x: x[0] if x else "UNKNOWN")
    df["is_parking"] = df["primary_violation"].isin(PARKING_VIOLATIONS)

    # Clean GPS
    df = df[(df["latitude"] > 12.5) & (df["latitude"] < 13.5) &
            (df["longitude"] > 77.3) & (df["longitude"] < 78.0)]

    if approved_only:
        df = df[df["validation_status"].isin(["approved"])]

    df["junction_clean"] = df["junction_name"].fillna("No Junction")
    df["has_junction"]   = df["junction_clean"] != "No Junction"

    return df.reset_index(drop=True)


@pd.core.cache
def load_events():
    df = pd.read_csv(EVENT_PATH, low_memory=False)
    df["start_datetime"]    = pd.to_datetime(df["start_datetime"],    utc=True, errors="coerce")
    df["resolved_datetime"] = pd.to_datetime(df["resolved_datetime"], utc=True, errors="coerce")
    df["closed_datetime"]   = pd.to_datetime(df["closed_datetime"],   utc=True, errors="coerce")

    df["dt_ist"]   = df["start_datetime"] + IST
    df["hour"]     = df["dt_ist"].dt.hour
    df["dow"]      = df["dt_ist"].dt.day_name()
    df["month"]    = df["dt_ist"].dt.month_name()

    end = df["resolved_datetime"].fillna(df["closed_datetime"])
    df["duration_mins"] = (end - df["start_datetime"]).dt.total_seconds() / 60

    # Clean GPS
    df = df[(df["latitude"] > 12.5) & (df["latitude"] < 13.5) &
            (df["longitude"] > 77.3) & (df["longitude"] < 78.0)]

    return df.reset_index(drop=True)
