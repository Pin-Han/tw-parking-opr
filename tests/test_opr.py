import pandas as pd
from analysis.opr import daily_opr_summary, hourly_pattern, week_over_week


def make_sample_df():
    rows = []
    for day_offset in range(3):
        date = f"2026-06-0{day_offset + 1}"
        for hour in [8, 12, 16, 20]:
            for district, rate in [("大安區", 0.85), ("板橋區", 0.65)]:
                rows.append({
                    "date": date,
                    "district": district,
                    "hour": hour,
                    "day_of_week": day_offset,
                    "is_holiday": 0,
                    "is_weekend": 0,
                    "usage_rate": rate + (hour - 12) * 0.01,
                    "snapshot_time": pd.Timestamp(f"{date} {hour}:00:00"),
                    "weather_main": "clear",
                    "road_name": f"{district}路段1",
                    "source": "taipei",
                })
    return pd.DataFrame(rows)


def test_daily_opr_summary_shape():
    df = make_sample_df()
    result = daily_opr_summary(df)
    assert len(result) == 6
    assert "avg_usage" in result.columns
    assert "peak_usage" in result.columns
    assert "min_usage" in result.columns


def test_daily_opr_summary_values():
    df = make_sample_df()
    result = daily_opr_summary(df)
    da = result[(result["date"] == "2026-06-01") & (result["district"] == "大安區")]
    assert len(da) == 1
    assert 0.8 < da.iloc[0]["avg_usage"] < 0.9


def test_hourly_pattern():
    df = make_sample_df()
    result = hourly_pattern(df, district="大安區")
    assert len(result) > 0
    assert "hour" in result.columns
    assert "usage_rate" in result.columns


def test_hourly_pattern_all_districts():
    df = make_sample_df()
    result = hourly_pattern(df)
    assert len(result) >= 4


def test_week_over_week():
    df = make_sample_df()
    df["snapshot_time"] = pd.to_datetime(df["snapshot_time"])
    result = week_over_week(df)
    assert "week" in result.columns
    assert "district" in result.columns
    assert "usage_rate" in result.columns
