from datetime import datetime
from fastapi import APIRouter
from data.fetcher import fetch_taipei, fetch_ntpc

router = APIRouter(prefix="/api")


@router.get("/realtime")
def get_realtime():
    tp = fetch_taipei()
    ntpc = fetch_ntpc()
    all_records = tp + ntpc
    return {
        "records": all_records,
        "count": len(all_records),
        "fetched_at": datetime.now().isoformat(),
    }
