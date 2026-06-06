import os
import pandas as pd
import httpx

API_BASE = os.getenv("API_BASE", "")


def get_realtime_df() -> pd.DataFrame:
    if API_BASE:
        try:
            res = httpx.get(f"{API_BASE}/api/realtime", timeout=15)
            res.raise_for_status()
            return pd.DataFrame(res.json()["records"])
        except Exception:
            pass
    from data.fetcher import fetch_taipei, fetch_ntpc
    tp = fetch_taipei()
    ntpc = fetch_ntpc()
    return pd.DataFrame(tp + ntpc)


def get_opr_data(endpoint: str, params: dict = None) -> tuple[pd.DataFrame, str | None]:
    if API_BASE:
        try:
            res = httpx.get(f"{API_BASE}/api/opr/{endpoint}", params=params, timeout=15)
            res.raise_for_status()
            data = res.json()
            if data.get("message"):
                return pd.DataFrame(), data["message"]
            return pd.DataFrame(data["data"]), None
        except Exception:
            pass
    from analysis.opr import get_snapshot_df, daily_opr_summary, hourly_pattern, week_over_week
    days = (params or {}).get("days", 14)
    df = get_snapshot_df(days=days)
    if df.empty:
        return pd.DataFrame(), "尚無快照資料"
    if endpoint == "daily":
        return daily_opr_summary(df), None
    elif endpoint == "hourly":
        return hourly_pattern(df, district=(params or {}).get("district")), None
    elif endpoint == "wow":
        return week_over_week(df), None
    return pd.DataFrame(), "Unknown endpoint"


def get_anomalies(days: int = 14, sigma: float = 2.0) -> tuple[pd.DataFrame, str | None]:
    if API_BASE:
        try:
            res = httpx.get(
                f"{API_BASE}/api/opr/anomalies",
                params={"days": days, "sigma": sigma},
                timeout=15,
            )
            res.raise_for_status()
            data = res.json()
            if data.get("message"):
                return pd.DataFrame(), data["message"]
            return pd.DataFrame(data["data"]), None
        except Exception:
            pass
    from analysis.opr import get_snapshot_df
    from analysis.anomaly import anomaly_detect
    df = get_snapshot_df(days=days)
    if df.empty:
        return pd.DataFrame(), "尚無快照資料"
    result = anomaly_detect(df, sigma=sigma)
    return result, None
