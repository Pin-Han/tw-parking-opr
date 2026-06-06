"""Generate realistic historical parking snapshot data for demo purposes.

Usage:
    python -m data.seed          # Insert 14 days of simulated snapshots
    python -m data.seed --clear  # Remove all seed data (keeps real snapshots)
    python -m data.seed --clear-all  # Remove ALL snapshots (seed + real)
"""

import random
import math
import sys
from datetime import datetime, timedelta
from sqlalchemy import text
from api.database import get_engine, init_db

SEED_SOURCE_TAG = "seed"  # Used to distinguish seed data from real snapshots

DISTRICTS_TAIPEI = [
    ("中正區", 0.78), ("大同區", 0.72), ("中山區", 0.82), ("松山區", 0.80),
    ("大安區", 0.88), ("萬華區", 0.74), ("信義區", 0.85), ("士林區", 0.68),
    ("北投區", 0.55), ("內湖區", 0.70), ("南港區", 0.62), ("文山區", 0.58),
]

DISTRICTS_NTPC = [
    ("板橋區", 0.83, 25.014, 121.459), ("三重區", 0.78, 25.062, 121.487),
    ("中和區", 0.76, 24.999, 121.494), ("永和區", 0.80, 25.008, 121.516),
    ("新莊區", 0.75, 25.036, 121.450), ("新店區", 0.65, 24.968, 121.542),
    ("樹林區", 0.60, 24.990, 121.421), ("土城區", 0.62, 24.972, 121.443),
    ("蘆洲區", 0.72, 25.085, 121.474), ("汐止區", 0.58, 25.063, 121.640),
    ("淡水區", 0.50, 25.169, 121.441), ("林口區", 0.55, 25.077, 121.392),
    ("五股區", 0.52, 25.083, 121.438), ("泰山區", 0.56, 25.058, 121.432),
]

WEATHER_PROBS = [
    ("clear", 0.45), ("cloudy", 0.30), ("rain", 0.24), ("typhoon", 0.01),
]

ROAD_NAMES_TAIPEI = {
    "中正區": ["忠孝西路", "中華路一段", "重慶南路"],
    "大同區": ["民生西路", "重慶北路", "延平北路"],
    "中山區": ["中山北路二段", "南京東路一段", "林森北路"],
    "松山區": ["南京東路四段", "敦化北路", "八德路三段"],
    "大安區": ["忠孝東路四段", "復興南路", "和平東路"],
    "萬華區": ["和平西路", "西園路", "萬大路"],
    "信義區": ["松仁路", "信義路五段", "忠孝東路五段"],
    "士林區": ["中正路", "文林路", "福國路"],
    "北投區": ["光明路", "中央北路", "石牌路"],
    "內湖區": ["成功路", "內湖路一段", "民權東路六段"],
    "南港區": ["研究院路", "南港路一段", "忠孝東路七段"],
    "文山區": ["木柵路", "興隆路", "羅斯福路六段"],
}


def hourly_pattern(hour: int, is_weekend: bool, base_rate: float) -> float:
    """Generate realistic occupancy based on hour and day type."""
    if is_weekend:
        # Weekend: gradual rise, peak at 14-16, slow decline
        curve = {
            0: 0.15, 1: 0.10, 2: 0.08, 3: 0.07, 4: 0.07, 5: 0.08,
            6: 0.12, 7: 0.18, 8: 0.30, 9: 0.45, 10: 0.60, 11: 0.72,
            12: 0.78, 13: 0.82, 14: 0.85, 15: 0.84, 16: 0.80, 17: 0.72,
            18: 0.60, 19: 0.48, 20: 0.38, 21: 0.30, 22: 0.22, 23: 0.18,
        }
    else:
        # Weekday: morning rush, lunch peak, evening peak
        curve = {
            0: 0.12, 1: 0.08, 2: 0.06, 3: 0.05, 4: 0.05, 5: 0.08,
            6: 0.15, 7: 0.35, 8: 0.62, 9: 0.78, 10: 0.85, 11: 0.88,
            12: 0.82, 13: 0.85, 14: 0.88, 15: 0.90, 16: 0.88, 17: 0.82,
            18: 0.68, 19: 0.52, 20: 0.40, 21: 0.30, 22: 0.22, 23: 0.15,
        }

    time_factor = curve.get(hour, 0.5)
    # Blend base rate with time pattern
    rate = base_rate * 0.4 + time_factor * 0.6
    # Add noise
    rate += random.gauss(0, 0.04)
    return max(0.02, min(0.99, rate))


def weather_effect(weather: str, rate: float) -> float:
    """Adjust occupancy based on weather."""
    if weather == "rain":
        return rate * 0.92  # Rain reduces street parking slightly
    elif weather == "typhoon":
        return rate * 0.40  # Typhoon drastically reduces
    return rate


def pick_weather() -> str:
    r = random.random()
    cumulative = 0
    for w, p in WEATHER_PROBS:
        cumulative += p
        if r < cumulative:
            return w
    return "clear"


def generate_snapshots(days: int = 14, snapshots_per_day: int = 48):
    """Generate simulated snapshot records."""
    now = datetime.now()
    start = now - timedelta(days=days)
    records = []

    for day_offset in range(days):
        date = start + timedelta(days=day_offset)
        is_weekend = date.weekday() >= 5
        day_weather = pick_weather()

        # Simulate snapshots every 30 min
        for snap_idx in range(snapshots_per_day):
            hour = snap_idx // 2
            minute = (snap_idx % 2) * 30
            snap_time = date.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if snap_time > now:
                break

            # Taipei districts (no coordinates)
            for district, base_rate in DISTRICTS_TAIPEI:
                roads = ROAD_NAMES_TAIPEI.get(district, [f"{district}路段"])
                for road in roads:
                    total = random.randint(8, 40)
                    rate = hourly_pattern(hour, is_weekend, base_rate)
                    rate = weather_effect(day_weather, rate)
                    occupied = int(total * rate)
                    available = total - occupied
                    records.append({
                        "source": SEED_SOURCE_TAG,
                        "road_id": f"TP-{district}-{road}",
                        "road_name": f"{district}{road}",
                        "district": district,
                        "total_spots": total,
                        "available_spots": available,
                        "usage_rate": round(occupied / total, 4) if total > 0 else 0,
                        "snapshot_time": snap_time.isoformat(),
                        "hour": hour,
                        "day_of_week": snap_time.weekday(),
                        "is_weekend": 1 if is_weekend else 0,
                        "is_holiday": 1 if is_weekend else 0,
                        "weather_main": day_weather,
                        "latitude": None,
                        "longitude": None,
                    })

            # New Taipei districts (with coordinates)
            for district, base_rate, lat, lng in DISTRICTS_NTPC:
                for road_idx in range(3):
                    road_name = f"{district}路段{road_idx + 1}"
                    total = random.randint(15, 60)
                    rate = hourly_pattern(hour, is_weekend, base_rate)
                    rate = weather_effect(day_weather, rate)
                    occupied = int(total * rate)
                    available = total - occupied
                    records.append({
                        "source": SEED_SOURCE_TAG,
                        "road_id": f"NTPC-{district}-{road_idx}",
                        "road_name": road_name,
                        "district": district,
                        "total_spots": total,
                        "available_spots": available,
                        "usage_rate": round(occupied / total, 4) if total > 0 else 0,
                        "snapshot_time": snap_time.isoformat(),
                        "hour": hour,
                        "day_of_week": snap_time.weekday(),
                        "is_weekend": 1 if is_weekend else 0,
                        "is_holiday": 1 if is_weekend else 0,
                        "weather_main": day_weather,
                        "latitude": round(lat + random.gauss(0, 0.005), 6),
                        "longitude": round(lng + random.gauss(0, 0.005), 6),
                    })

    return records


def seed_db(days: int = 14):
    """Insert seed data into the database."""
    init_db()
    engine = get_engine()

    # Check if seed data already exists
    with engine.connect() as conn:
        existing = conn.execute(
            text("SELECT COUNT(*) FROM snapshots WHERE source = :src"),
            {"src": SEED_SOURCE_TAG},
        ).scalar()
        if existing > 0:
            print(f"[seed] Found {existing} existing seed records. Clearing first...")
            clear_seed(engine)

    records = generate_snapshots(days=days)
    print(f"[seed] Generated {len(records)} records for {days} days")

    with engine.begin() as conn:
        batch_size = 1000
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
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
                batch,
            )
            print(f"  Inserted {min(i + batch_size, len(records))}/{len(records)}")

    print(f"[seed] Done! {len(records)} seed records inserted.")


def clear_seed(engine=None):
    """Remove only seed data, keep real snapshots."""
    if engine is None:
        engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM snapshots WHERE source = :src"),
            {"src": SEED_SOURCE_TAG},
        )
        print(f"[seed] Cleared {result.rowcount} seed records. Real data preserved.")


def clear_all():
    """Remove ALL snapshots (seed + real)."""
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(text("DELETE FROM snapshots"))
        print(f"[seed] Cleared ALL {result.rowcount} snapshot records.")


if __name__ == "__main__":
    if "--clear-all" in sys.argv:
        clear_all()
    elif "--clear" in sys.argv:
        clear_seed()
    else:
        seed_db()
