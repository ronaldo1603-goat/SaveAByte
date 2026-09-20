import os
from datetime import date

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv() # read .env file and put variables in os.environ (a dict)

BUCKET = "tray-images" # bucket in supabase


def _cfg(name: str) -> str:
    if name in os.environ:
        return os.environ[name]
    return st.secrets[name]


@st.cache_resource # decorator helps create and reuse client whenever run streamlit
def get_client() -> Client: # create connection with supabase
    return create_client(_cfg("SUPABASE_URL"), _cfg("SUPABASE_SERVICE_KEY"))

# upload images to storage
def upload_tray_image(image_bytes: bytes, scan_id: str, meal_date: str) -> str: 
    path = f"{meal_date}/{scan_id}.jpg"
    get_client().storage.from_(BUCKET).upload(
        path=path,
        file=image_bytes,
        file_options={"content-type": "image/jpeg", "upsert": "false"},
    )
    return path

# save scan to table
def save_scan(scan_id: str, image_path: str, analysis, meal_date: str,
              phase: str = "after") -> None:
    """1 khay -> nhiều row, cùng scan_id. Bulk insert 1 request."""
    rows = [
        {
            "scan_id": scan_id,
            "image_url": image_path,
            "dish_name": c.dish_name,
            "fill_fraction": c.fill_fraction,
            "inedible_ratio": c.inedible_ratio,   
            "meal_date": meal_date,
            "phase": phase,                       
        }
        for c in analysis.compartments
        if c.has_food
    ]
    if not rows:
        return
    get_client().table("waste_logs").insert(rows).execute()
# extra portions count
def log_tap(dish_name: str, meal_date: str) -> None:
    get_client().table("tap_counts").insert(
        {"dish_name": dish_name, "meal_date": meal_date}
    ).execute()

# get data from the past for dashboard
def _select_all(table: str, start_date: str, end_date: str,
                page_size: int = 1000) -> pd.DataFrame:
    rows, offset = [], 0
    while True:
        res = (
            get_client().table(table)
            .select("*")
            .gte("meal_date", start_date)
            .lte("meal_date", end_date)
            .order("id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return pd.DataFrame(rows)


def fetch_logs(start_date: str, end_date: str) -> pd.DataFrame:
    return _select_all("waste_logs", start_date, end_date)


def fetch_taps(start_date: str, end_date: str) -> pd.DataFrame:
    return _select_all("tap_counts", start_date, end_date)


def signed_url(path: str, seconds: int = 3600) -> str | None:
    res = get_client().storage.from_(BUCKET).create_signed_url(path, seconds)
    # tên key khác nhau giữa các bản storage3
    return res.get("signedURL") or res.get("signedUrl")

def save_calibration(slope, intercept, n, mae, bias_before, spearman, scope="global"):
    return get_client().table("calibration").insert({
        "scope": scope, "slope": slope, "intercept": intercept,
        "n": n, "mae": mae, "bias_before": bias_before, "spearman": spearman,
    }).execute()


def latest_calibration(scope: str = "global") -> dict | None:
    res = (
        get_client().table("calibration")
        .select("*")
        .eq("scope", scope)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None

