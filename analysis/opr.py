import pandas as pd
from sqlalchemy import text
from datetime import datetime, timedelta
from api.database import get_engine


def get_snapshot_df(days: int = 14) -> pd.DataFrame:
    engine = get_engine()
    since = (datetime.now() - timedelta(days=days)).isoformat()
    with engine.connect() as conn:
        df = pd.read_sql(
            text("SELECT * FROM snapshots WHERE snapshot_time > :since ORDER BY snapshot_time"),
            conn,
            params={"since": since},
        )
    if len(df) == 0:
        return df
    df["snapshot_time"] = pd.to_datetime(df["snapshot_time"], format="ISO8601")
    df["date"] = df["snapshot_time"].dt.date.astype(str)
    return df


def daily_opr_summary(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["date", "district"])
        .agg(
            avg_usage=("usage_rate", "mean"),
            peak_usage=("usage_rate", "max"),
            min_usage=("usage_rate", "min"),
            sample_count=("usage_rate", "count"),
        )
        .reset_index()
        .round(3)
    )


def hourly_pattern(df: pd.DataFrame, district: str = None) -> pd.DataFrame:
    if district:
        df = df[df["district"] == district]
    return (
        df.groupby(["hour", "is_holiday"])["usage_rate"]
        .mean()
        .reset_index()
        .round(3)
    )


def week_over_week(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["week"] = df["snapshot_time"].dt.isocalendar().week.astype(int)
    return (
        df.groupby(["week", "district"])["usage_rate"]
        .mean()
        .reset_index()
        .round(3)
    )
