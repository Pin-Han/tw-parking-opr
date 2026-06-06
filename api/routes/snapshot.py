from fastapi import APIRouter
from sqlalchemy import text
from api.database import get_engine

router = APIRouter(prefix="/api")


@router.get("/snapshots/status")
def get_snapshot_status():
    engine = get_engine()
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM snapshots")).scalar() or 0
        latest = conn.execute(text("SELECT MAX(snapshot_time) FROM snapshots")).scalar()
        days = conn.execute(text("SELECT COUNT(DISTINCT date(snapshot_time)) FROM snapshots")).scalar() or 0
        today_count = conn.execute(text("SELECT COUNT(*) FROM snapshots WHERE date(snapshot_time) = date('now')")).scalar() or 0
    return {
        "total_records": total,
        "latest_snapshot": latest,
        "days_collected": days,
        "today_snapshots": today_count,
    }
