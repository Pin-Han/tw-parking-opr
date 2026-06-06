import pandas as pd
from analysis.anomaly import anomaly_detect


def make_anomaly_df():
    rows = []
    for day in range(1, 7):
        rows.append({
            "date": f"2026-06-0{day}",
            "district": "大安區",
            "road_name": "忠孝東路",
            "hour": 14,
            "usage_rate": 0.80 + (day % 3) * 0.01,
            "is_holiday": 0,
        })
    rows.append({
        "date": "2026-06-07",
        "district": "大安區",
        "road_name": "忠孝東路",
        "hour": 14,
        "usage_rate": 0.98,
        "is_holiday": 0,
    })
    rows.append({
        "date": "2026-06-07",
        "district": "板橋區",
        "road_name": "文化路",
        "hour": 14,
        "usage_rate": 0.60,
        "is_holiday": 0,
    })
    for day in range(1, 7):
        rows.append({
            "date": f"2026-06-0{day}",
            "district": "板橋區",
            "road_name": "文化路",
            "hour": 14,
            "usage_rate": 0.60 + (day % 2) * 0.01,
            "is_holiday": 0,
        })
    return pd.DataFrame(rows)


def test_anomaly_detect_finds_anomaly():
    df = make_anomaly_df()
    result = anomaly_detect(df, today="2026-06-07", sigma=2.0)
    assert len(result) >= 1
    assert "大安區" in result["district"].values


def test_anomaly_detect_excludes_normal():
    df = make_anomaly_df()
    result = anomaly_detect(df, today="2026-06-07", sigma=2.0)
    assert "板橋區" not in result["district"].values


def test_anomaly_detect_has_z_score():
    df = make_anomaly_df()
    result = anomaly_detect(df, today="2026-06-07", sigma=2.0)
    assert "z_score" in result.columns
    da = result[result["district"] == "大安區"]
    assert da.iloc[0]["z_score"] > 2.0
