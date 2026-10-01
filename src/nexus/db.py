import os
from datetime import date

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client
from src.nexus.menu import OTHER, normalize_dish

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
              phase: str = "after") -> int:
    client = get_client()
    client.table("scans").insert({
        "scan_id": scan_id, "meal_date": meal_date,
        "phase": phase, "image_url": image_path,
    }).execute()

    rows = [
        {"scan_id": scan_id, "image_url": image_path, "dish_name": c.dish_name,
         "fill_fraction": c.fill_fraction, "inedible_ratio": c.inedible_ratio,
         "meal_date": meal_date, "phase": phase}
        for c in analysis.compartments if c.has_food
    ]
    if rows:
        try:
            client.table("waste_logs").insert(rows).execute()
        except Exception:
            # Nếu không xoá, khay này sẽ bị đếm như "ăn sạch" dù thực ra insert lỗi
            client.table("scans").delete().eq("scan_id", scan_id).execute()
            raise
    return len(rows)

# extra portions count
def log_tap(dish_name: str, meal_date: str) -> None:
    get_client().table("tap_counts").insert(
        {"dish_name": dish_name, "meal_date": meal_date}
    ).execute()

# get data from the past for dashboard
def _select_all(table: str, start_date: str, end_date: str,
                page_size: int = 1000, order_col: str = "id") -> pd.DataFrame:
    rows, offset = [], 0
    while True:
        res = (
            get_client().table(table)
            .select("*")
            .gte("meal_date", start_date)
            .lte("meal_date", end_date)
            .order(order_col)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return pd.DataFrame(rows)

def fetch_scans(start_date: str, end_date: str) -> pd.DataFrame:
    return _select_all("scans", start_date, end_date, order_col="scan_id")

# get scans data for dashboard
def fetch_logs(start_date: str, end_date: str) -> pd.DataFrame:
    return _select_all("waste_logs", start_date, end_date)

# get taps data for dashboard
def fetch_taps(start_date: str, end_date: str) -> pd.DataFrame:
    return _select_all("tap_counts", start_date, end_date)


def signed_url(path: str, seconds: int = 3600) -> str | None:
    res = get_client().storage.from_(BUCKET).create_signed_url(path, seconds)
    return res.get("signedURL") or res.get("signedUrl")

# save calibration data to the table
def save_calibration(slope, intercept, n, mae, bias_before, spearman, scope="global"):
    return get_client().table("calibration").insert({
        "scope": scope, "slope": slope, "intercept": intercept,
        "n": n, "mae": mae, "bias_before": bias_before, "spearman": spearman,
    }).execute()

# get the latest calibration data from the table
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

# get the menu for a specific date
def fetch_menu(meal_date: str) -> list[str]:
    res = (get_client().table("menus").select("dish_name")
           .eq("meal_date", meal_date).order("id").execute())
    return [r["dish_name"] for r in (res.data or [])]


def fetch_menus(start_date: str, end_date: str) -> pd.DataFrame:
    return _select_all("menus", start_date, end_date)


def fetch_known_dishes() -> list[str]:
    res = (get_client().table("menus").select("dish_name")
           .order("id", desc=True).limit(1000).execute())
    return sorted({r["dish_name"] for r in (res.data or [])})

# save menu for a specific date
def save_menu(meal_date: str, dishes: list[str]) -> list[str]:
    """Ghi thực đơn 1 ngày, thay bản cũ. Trả về list tên đã chuẩn hoá."""
    clean = list(dict.fromkeys(normalize_dish(d) for d in dishes))
    clean = [d for d in clean if d and d != OTHER]
    client = get_client()
    old = set(fetch_menu(meal_date))

    # Insert trước, xoá sau: nếu insert lỗi thì thực đơn cũ vẫn còn nguyên
    new_rows = [{"meal_date": meal_date, "dish_name": d} for d in clean if d not in old]
    if new_rows:
        client.table("menus").insert(new_rows).execute()
    for d in old - set(clean):
        (client.table("menus").delete()
         .eq("meal_date", meal_date).eq("dish_name", d).execute())
    return clean

# number of servings for a specific date
def fetch_servings(start_date: str, end_date: str) -> pd.DataFrame:
    return _select_all("servings", start_date, end_date)


def fetch_serving(meal_date: str) -> int | None:
    res = (get_client().table("servings").select("n_served")
           .eq("meal_date", meal_date).execute())
    return res.data[0]["n_served"] if res.data else None


def save_serving(meal_date: str, n_served: int) -> None:
    (get_client().table("servings")
     .upsert({"meal_date": meal_date, "n_served": int(n_served)}, on_conflict="meal_date")
     .execute())