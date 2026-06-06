# Parking OPR Analytics

台北市 + 新北市路邊停車 OPR（Operational Performance Report）分析平台。

## Features

- **即時停車地圖** — 新北市路邊停車使用率即時視覺化
- **自動快照累積** — 每 30 分鐘自動記錄停車數據至 PostgreSQL
- **OPR 統計分析** — 每日彙總、24H 時段模式、週環比
- **異常偵測** — Z-score 偵測使用率偏離歷史均值的路段

## Tech Stack

- **Backend:** FastAPI + APScheduler
- **Frontend:** Streamlit + pydeck + Plotly
- **Database:** PostgreSQL (Neon)
- **Data Sources:** 台北市政府開放資料、新北市政府開放資料、中央氣象署

## Setup

```bash
# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your DATABASE_URL and CWA_API_KEY

# Init DB
python -c "from api.database import init_db; init_db()"

# Run API
uvicorn api.main:app --port 8000

# Run Dashboard (separate terminal)
streamlit run dashboard/app.py
```

## Data Sources

| Source | Format | Update Frequency |
|--------|--------|-----------------|
| [台北市路邊停車](https://data.gov.tw/dataset/128617) | XML | Real-time |
| [新北市路邊停車](https://data.gov.tw/dataset/122901) | CSV | Every 2 min |
| [中央氣象署](https://opendata.cwa.gov.tw/) | JSON | Hourly |
| [台灣假日](https://cdn.jsdelivr.net/gh/ruyut/TaiwanCalendar/) | JSON | Yearly |

## Architecture

```
Government APIs → FastAPI (fetch + schedule) → PostgreSQL → Streamlit Dashboard
                       ↓
               APScheduler (30 min snapshots)
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/realtime` | Real-time parking data |
| `GET /api/snapshots/status` | Snapshot collection stats |
| `GET /api/opr/daily` | Daily OPR summary |
| `GET /api/opr/hourly` | 24-hour usage pattern |
| `GET /api/opr/wow` | Week-over-week comparison |
| `GET /api/opr/anomalies` | Anomaly detection |
