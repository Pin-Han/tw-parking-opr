import pandas as pd
from datetime import datetime


def anomaly_detect(df: pd.DataFrame, today: str = None, sigma: float = 2.0) -> pd.DataFrame:
    if today is None:
        today = datetime.now().date().isoformat()

    today_df = df[df["date"] == today]
    if today_df.empty:
        return pd.DataFrame()

    hist = df[df["date"] != today]
    if hist.empty:
        return pd.DataFrame()

    hist_stats = (
        hist.groupby(["district", "hour"])["usage_rate"]
        .agg(["mean", "std"])
        .reset_index()
    )
    hist_stats.columns = ["district", "hour", "hist_mean", "hist_std"]
    hist_stats["hist_std"] = hist_stats["hist_std"].fillna(0.05)
    hist_stats["hist_std"] = hist_stats["hist_std"].clip(lower=0.01)

    merged = today_df.merge(hist_stats, on=["district", "hour"], how="inner")
    if merged.empty:
        return pd.DataFrame()

    merged["z_score"] = (merged["usage_rate"] - merged["hist_mean"]) / merged["hist_std"]

    anomalies = merged[merged["z_score"].abs() > sigma].sort_values("z_score", ascending=False)
    return anomalies
