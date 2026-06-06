import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from api.database import init_db
from api.routes import realtime, snapshot
from data.snapshot import save_snapshot

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    interval = int(os.getenv("SNAPSHOT_INTERVAL_MINUTES", "30"))
    scheduler = BackgroundScheduler()
    scheduler.add_job(save_snapshot, "interval", minutes=interval, id="snapshot")
    scheduler.start()
    print(f"[scheduler] Snapshot every {interval} min")
    yield
    scheduler.shutdown()


app = FastAPI(title="Parking OPR API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(realtime.router)
app.include_router(snapshot.router)


@app.get("/")
def root():
    return {"message": "Parking OPR API", "docs": "/docs"}
