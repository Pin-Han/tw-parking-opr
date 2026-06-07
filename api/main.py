import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from api.database import init_db
from api.routes import realtime, snapshot, opr
from data.snapshot import save_snapshot

load_dotenv()

# Init DB on cold start
init_db()

app = FastAPI(title="Parking OPR API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(realtime.router)
app.include_router(snapshot.router)
app.include_router(opr.router)


@app.get("/")
def root():
    return {"message": "Parking OPR API", "docs": "/docs"}


# Vercel serverless handler
from mangum import Mangum
handler = Mangum(app)


@app.get("/api/cron/snapshot")
def cron_snapshot(request: Request):
    """Triggered by Vercel Cron every 30 min to collect parking data."""
    auth = request.headers.get("authorization")
    cron_secret = os.getenv("CRON_SECRET", "")
    if cron_secret and auth != f"Bearer {cron_secret}":
        return {"error": "Unauthorized"}, 401
    save_snapshot()
    return {"status": "ok"}
