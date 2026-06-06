from datetime import datetime
from sqlalchemy import text
from api.database import get_engine
from data.fetcher import fetch_taipei, fetch_ntpc
from data.weather import get_weather
from data.holidays import is_holiday


def save_snapshot():
    now = datetime.now()
    holiday = 1 if is_holiday(now.year, now.month, now.day) else 0
    weather = get_weather()

    tp_records = fetch_taipei()
    ntpc_records = fetch_ntpc()
    all_records = tp_records + ntpc_records

    if not all_records:
        print(f"[snapshot] {now.strftime('%H:%M')} No records fetched, skipping")
        return

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO snapshots (
                    source, road_id, road_name, district,
                    total_spots, available_spots, usage_rate,
                    snapshot_time, hour, day_of_week, is_weekend, is_holiday,
                    weather_main, latitude, longitude
                ) VALUES (
                    :source, :road_id, :road_name, :district,
                    :total_spots, :available_spots, :usage_rate,
                    :snapshot_time, :hour, :day_of_week, :is_weekend, :is_holiday,
                    :weather_main, :latitude, :longitude
                )
            """),
            [
                {
                    "source": r["source"],
                    "road_id": r["road_id"],
                    "road_name": r["road_name"],
                    "district": r["district"],
                    "total_spots": r["total_spots"],
                    "available_spots": r["available_spots"],
                    "usage_rate": r["usage_rate"],
                    "snapshot_time": now.isoformat(),
                    "hour": now.hour,
                    "day_of_week": now.weekday(),
                    "is_weekend": 1 if now.weekday() >= 5 else 0,
                    "is_holiday": holiday,
                    "weather_main": weather["weather_main"],
                    "latitude": r["latitude"],
                    "longitude": r["longitude"],
                }
                for r in all_records
                if r["total_spots"] > 0
            ],
        )

    print(f"[snapshot] {now.strftime('%H:%M')} Saved {len(all_records)} records")
