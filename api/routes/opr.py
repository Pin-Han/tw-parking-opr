from fastapi import APIRouter, Query
from analysis.opr import get_snapshot_df, daily_opr_summary, hourly_pattern, week_over_week
from analysis.anomaly import anomaly_detect

router = APIRouter(prefix="/api/opr")


@router.get("/daily")
def get_daily_summary(days: int = Query(default=14, ge=1, le=90)):
    df = get_snapshot_df(days=days)
    if df.empty:
        return {"data": [], "message": "No snapshot data yet"}
    summary = daily_opr_summary(df)
    return {"data": summary.to_dict(orient="records")}


@router.get("/hourly")
def get_hourly_pattern(days: int = Query(default=14, ge=1, le=90), district: str = Query(default=None)):
    df = get_snapshot_df(days=days)
    if df.empty:
        return {"data": [], "message": "No snapshot data yet"}
    pattern = hourly_pattern(df, district=district)
    return {"data": pattern.to_dict(orient="records")}


@router.get("/wow")
def get_week_over_week(days: int = Query(default=14, ge=1, le=90)):
    df = get_snapshot_df(days=days)
    if df.empty:
        return {"data": [], "message": "No snapshot data yet"}
    wow = week_over_week(df)
    return {"data": wow.to_dict(orient="records")}


@router.get("/anomalies")
def get_anomalies(days: int = Query(default=14, ge=1, le=90), sigma: float = 2.0):
    df = get_snapshot_df(days=days)
    if df.empty:
        return {"data": [], "message": "No snapshot data yet"}
    anomalies = anomaly_detect(df, sigma=sigma)
    return {"data": anomalies.to_dict(orient="records")}
