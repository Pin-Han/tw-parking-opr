# Parking OPR Analytics — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a real-time street parking OPR (Operational Performance Report) analytics platform for Taipei + New Taipei City, with live data, automated snapshots, and statistical analysis dashboards.

**Architecture:** FastAPI serves as the API layer (fetching, snapshot scheduling, OPR endpoints). Streamlit consumes the API to render dashboards. PostgreSQL (Neon free tier) stores snapshots for historical analysis. The fetcher layer pulls real-time data from government open-data APIs (Taipei XML, New Taipei CSV), calculates usage rates, and normalizes into a common schema.

**Tech Stack:** Python 3.11+, FastAPI, Streamlit, PostgreSQL (Neon), SQLAlchemy, APScheduler, pydeck, Plotly Express, pandas, httpx

---

## File Map

```
parking_opr/
├── README.md                        # Project overview and setup instructions
├── .env.example                     # Environment variable template
├── .gitignore                       # Python/IDE/env ignores
├── requirements.txt                 # Python dependencies
│
├── data/
│   ├── __init__.py
│   ├── fetcher.py                   # fetch_taipei(), fetch_ntpc() → list[dict]
│   ├── snapshot.py                  # save_snapshot() + APScheduler startup
│   ├── weather.py                   # get_weather() from CWA API
│   ├── holidays.py                  # get_holiday_set() from jsDelivr
│   ├── districts.py                 # District code→name mappings for both cities
│   └── schema.sql                   # PostgreSQL DDL (snapshots, opr_daily tables)
│
├── analysis/
│   ├── __init__.py
│   ├── opr.py                       # daily_opr_summary(), hourly_pattern(), week_over_week()
│   └── anomaly.py                   # anomaly_detect() using z-score
│
├── api/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app, lifespan (scheduler), CORS
│   ├── database.py                  # SQLAlchemy engine + get_db() helper
│   └── routes/
│       ├── __init__.py
│       ├── realtime.py              # GET /api/realtime
│       ├── opr.py                   # GET /api/opr/daily, /api/opr/hourly, /api/opr/wow
│       └── snapshot.py              # GET /api/snapshots/status
│
├── dashboard/
│   ├── app.py                       # Streamlit entrypoint + page config
│   └── pages/
│       ├── 1_即時地圖.py             # Real-time map (New Taipei) + district stats
│       ├── 2_OPR分析.py              # Daily summary, hourly pattern, week-over-week
│       └── 3_異常偵測.py             # Z-score anomaly cards
│
└── tests/
    ├── __init__.py
    ├── conftest.py                  # Shared fixtures (sample XML, CSV, DB)
    ├── test_fetcher.py              # Taipei XML + New Taipei CSV parsing tests
    ├── test_districts.py            # District mapping tests
    ├── test_opr.py                  # OPR calculation tests
    ├── test_anomaly.py              # Anomaly detection tests
    └── test_api.py                  # FastAPI endpoint tests
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `data/__init__.py`, `analysis/__init__.py`, `api/__init__.py`, `api/routes/__init__.py`, `dashboard/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
fastapi==0.115.0
uvicorn==0.30.0
streamlit==1.37.0
pydeck==0.9.1
plotly==5.22.0
pandas==2.2.0
httpx==0.27.0
apscheduler==3.10.4
python-dotenv==1.0.0
sqlalchemy==2.0.30
psycopg2-binary==2.9.9
pytest==8.2.0
pytest-asyncio==0.23.0
```

- [ ] **Step 2: Create .env.example**

```
DATABASE_URL=postgresql://user:pass@host/dbname
CWA_API_KEY=your_cwa_key_here
SNAPSHOT_INTERVAL_MINUTES=30
```

- [ ] **Step 3: Create .gitignore**

```
__pycache__/
*.pyc
.env
*.db
.venv/
venv/
.idea/
.vscode/
*.egg-info/
dist/
build/
.pytest_cache/
```

- [ ] **Step 4: Create all `__init__.py` files**

Create empty `__init__.py` in: `data/`, `analysis/`, `api/`, `api/routes/`, `tests/`

No `__init__.py` needed for `dashboard/` — Streamlit doesn't use it.

- [ ] **Step 5: Install dependencies and verify**

Run: `pip install -r requirements.txt`
Expected: All packages install without errors.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .env.example .gitignore data/__init__.py analysis/__init__.py api/__init__.py api/routes/__init__.py tests/__init__.py
git commit -m "chore: scaffold project structure and dependencies"
```

---

## Task 2: Database Schema and Connection

**Files:**
- Create: `data/schema.sql`
- Create: `api/database.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create data/schema.sql**

```sql
CREATE TABLE IF NOT EXISTS snapshots (
    id              SERIAL PRIMARY KEY,
    source          TEXT NOT NULL,
    road_id         TEXT NOT NULL,
    road_name       TEXT,
    district        TEXT,
    total_spots     INTEGER,
    available_spots INTEGER,
    usage_rate      REAL,
    snapshot_time   TIMESTAMP NOT NULL,
    hour            INTEGER,
    day_of_week     INTEGER,
    is_weekend      INTEGER,
    is_holiday      INTEGER DEFAULT 0,
    weather_main    TEXT,
    latitude        REAL,
    longitude       REAL
);

CREATE TABLE IF NOT EXISTS opr_daily (
    id              SERIAL PRIMARY KEY,
    date            TEXT NOT NULL,
    district        TEXT NOT NULL,
    avg_usage_rate  REAL,
    peak_usage_rate REAL,
    peak_hour       INTEGER,
    min_usage_rate  REAL,
    off_peak_hour   INTEGER,
    is_holiday      INTEGER,
    weather_main    TEXT,
    UNIQUE(date, district)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_time ON snapshots(snapshot_time);
CREATE INDEX IF NOT EXISTS idx_snapshots_district_hour ON snapshots(district, hour, day_of_week);
CREATE INDEX IF NOT EXISTS idx_opr_daily_date ON opr_daily(date, district);
```

- [ ] **Step 2: Create api/database.py**

```python
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///parking.db")

# SQLAlchemy engine — works with both SQLite and PostgreSQL
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def init_db():
    """Run schema.sql to create tables if they don't exist."""
    schema_path = os.path.join(os.path.dirname(__file__), "..", "data", "schema.sql")
    with open(schema_path) as f:
        schema_sql = f.read()
    with engine.begin() as conn:
        for statement in schema_sql.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(text(statement))


def get_engine():
    return engine
```

- [ ] **Step 3: Create tests/conftest.py with in-memory SQLite fixture**

```python
import pytest
from sqlalchemy import create_engine, text
from api.database import init_db
import os


@pytest.fixture
def db_engine(tmp_path):
    """Create a temporary SQLite database for testing."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    # Read and execute schema
    schema_path = os.path.join(os.path.dirname(__file__), "..", "data", "schema.sql")
    with open(schema_path) as f:
        schema_sql = f.read()
    with engine.begin() as conn:
        for statement in schema_sql.split(";"):
            stmt = statement.strip()
            if stmt:
                # Replace SERIAL with INTEGER for SQLite compatibility
                stmt = stmt.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
                conn.execute(text(stmt))
    yield engine
    engine.dispose()
```

- [ ] **Step 4: Verify schema works**

Run: `python -c "from api.database import init_db; init_db(); print('DB initialized OK')"`

If using SQLite locally (no DATABASE_URL set), this should create `parking.db` and print success.

- [ ] **Step 5: Commit**

```bash
git add data/schema.sql api/database.py tests/conftest.py
git commit -m "feat: add database schema and connection layer"
```

---

## Task 3: District Code Mappings

**Files:**
- Create: `data/districts.py`
- Create: `tests/test_districts.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_districts.py
from data.districts import extract_district_taipei, extract_district_ntpc, NTPC_AREA_CODES


def test_taipei_district_from_road_name():
    assert extract_district_taipei("大安區忠孝東路四段") == "大安區"
    assert extract_district_taipei("信義區松仁路") == "信義區"


def test_taipei_district_unknown():
    assert extract_district_taipei("某某路") == "其他"


def test_ntpc_district_from_areacode():
    assert extract_district_ntpc("65000010") == "板橋區"
    assert extract_district_ntpc("65000020") == "三重區"


def test_ntpc_district_unknown_code():
    assert extract_district_ntpc("99999999") == "其他"


def test_ntpc_area_codes_dict_not_empty():
    assert len(NTPC_AREA_CODES) >= 10
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_districts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'data.districts'`

- [ ] **Step 3: Implement data/districts.py**

```python
TAIPEI_DISTRICTS = [
    "中正區", "大同區", "中山區", "松山區", "大安區", "萬華區",
    "信義區", "士林區", "北投區", "內湖區", "南港區", "文山區",
]

NTPC_AREA_CODES = {
    "65000010": "板橋區",
    "65000020": "三重區",
    "65000030": "中和區",
    "65000040": "永和區",
    "65000050": "新莊區",
    "65000060": "新店區",
    "65000070": "樹林區",
    "65000080": "鶯歌區",
    "65000090": "三峽區",
    "65000100": "淡水區",
    "65000110": "汐止區",
    "65000120": "瑞芳區",
    "65000130": "土城區",
    "65000140": "蘆洲區",
    "65000150": "五股區",
    "65000160": "泰山區",
    "65000170": "林口區",
    "65000180": "深坑區",
    "65000190": "石碇區",
    "65000200": "坪林區",
    "65000210": "三芝區",
    "65000220": "石門區",
    "65000230": "八里區",
    "65000240": "平溪區",
    "65000250": "雙溪區",
    "65000260": "貢寮區",
    "65000270": "金山區",
    "65000280": "萬里區",
    "65000290": "烏來區",
}


def extract_district_taipei(road_name: str) -> str:
    """Extract district from Taipei road name. e.g. '大安區忠孝東路' → '大安區'"""
    for d in TAIPEI_DISTRICTS:
        if d in road_name:
            return d
    return "其他"


def extract_district_ntpc(areacode: str) -> str:
    """Map New Taipei areacode to district name. e.g. '65000010' → '板橋區'"""
    return NTPC_AREA_CODES.get(str(areacode), "其他")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_districts.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add data/districts.py tests/test_districts.py
git commit -m "feat: add district code mappings for Taipei and New Taipei"
```

---

## Task 4: Taipei Fetcher (XML Parser)

**Files:**
- Create: `data/fetcher.py`
- Create: `tests/test_fetcher.py`

- [ ] **Step 1: Write the failing test for Taipei XML parsing**

```python
# tests/test_fetcher.py
from data.fetcher import parse_taipei_xml


SAMPLE_TAIPEI_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<DATA>
    <ROAD>
        <cellStatusList>
            <cell>
                <cellStatus>1</cellStatus>
                <coord_X>0.0</coord_X>
                <coord_Y>0.0</coord_Y>
                <data_Dt>2026-06-06 19:06:58</data_Dt>
                <psId>01</psId>
            </cell>
            <cell>
                <cellStatus>2</cellStatus>
                <coord_X>0.0</coord_X>
                <coord_Y>0.0</coord_Y>
                <data_Dt>2026-06-06 17:54:59</data_Dt>
                <psId>02</psId>
            </cell>
            <cell>
                <cellStatus>1</cellStatus>
                <coord_X>0.0</coord_X>
                <coord_Y>0.0</coord_Y>
                <data_Dt>2026-06-06 17:12:24</data_Dt>
                <psId>08</psId>
            </cell>
        </cellStatusList>
        <roadSegAvail>-99</roadSegAvail>
        <roadSegCarType>1</roadSegCarType>
        <roadSegFee>30元</roadSegFee>
        <roadSegID>1002053</roadSegID>
        <roadSegName>中山區中山北路一段53巷</roadSegName>
        <roadSegtimeEnd>20:00</roadSegtimeEnd>
        <roadSegtimeStart>07:00</roadSegtimeStart>
        <roadSegTotalValue>8</roadSegTotalValue>
        <roadSegUpdatetime>20260606T204009</roadSegUpdatetime>
        <roadSegUsage>-99.0</roadSegUsage>
    </ROAD>
    <ROAD>
        <cellStatusList>
            <cell>
                <cellStatus>2</cellStatus>
                <coord_X>0.0</coord_X>
                <coord_Y>0.0</coord_Y>
                <data_Dt>2026-06-06 10:00:00</data_Dt>
                <psId>01</psId>
            </cell>
        </cellStatusList>
        <roadSegAvail>-99</roadSegAvail>
        <roadSegCarType>1</roadSegCarType>
        <roadSegFee>40元</roadSegFee>
        <roadSegID>2001001</roadSegID>
        <roadSegName>大安區忠孝東路四段</roadSegName>
        <roadSegtimeEnd>20:00</roadSegtimeEnd>
        <roadSegtimeStart>07:00</roadSegtimeStart>
        <roadSegTotalValue>20</roadSegTotalValue>
        <roadSegUpdatetime>20260606T204009</roadSegUpdatetime>
        <roadSegUsage>-99.0</roadSegUsage>
    </ROAD>
</DATA>
"""


def test_parse_taipei_xml_record_count():
    records = parse_taipei_xml(SAMPLE_TAIPEI_XML)
    assert len(records) == 2


def test_parse_taipei_xml_first_record_fields():
    records = parse_taipei_xml(SAMPLE_TAIPEI_XML)
    r = records[0]
    assert r["source"] == "taipei"
    assert r["road_id"] == "1002053"
    assert r["road_name"] == "中山區中山北路一段53巷"
    assert r["district"] == "中山區"
    assert r["total_spots"] == 3  # 3 cells in the XML
    assert r["available_spots"] == 1  # 1 cell with cellStatus=2
    assert abs(r["usage_rate"] - 2 / 3) < 0.01  # 2 occupied / 3 total
    assert r["latitude"] is None
    assert r["longitude"] is None


def test_parse_taipei_xml_usage_calculated_from_cells():
    """usage_rate should be calculated from cellStatus, not roadSegUsage (-99)."""
    records = parse_taipei_xml(SAMPLE_TAIPEI_XML)
    r = records[1]
    # 1 cell, cellStatus=2 (available), so 0 occupied / 1 total = 0.0
    assert r["usage_rate"] == 0.0
    assert r["available_spots"] == 1
    assert r["total_spots"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_fetcher.py -v`
Expected: FAIL — `ImportError: cannot import name 'parse_taipei_xml'`

- [ ] **Step 3: Implement data/fetcher.py with parse_taipei_xml**

```python
import xml.etree.ElementTree as ET
import pandas as pd
import httpx
from data.districts import extract_district_taipei, extract_district_ntpc

TAIPEI_URL = "https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_roadquery.xml"
NTPC_URL = "https://data.ntpc.gov.tw/api/datasets/54a507c4-c038-41b5-bf60-bbecb9d052c6/csv/file"


def parse_taipei_xml(xml_content: str) -> list[dict]:
    """Parse Taipei parking XML into normalized records.

    Usage rate is calculated from individual cellStatus values
    because roadSegUsage is -99 for 99%+ of records.
    cellStatus: 1=occupied, 2=available, 0=unknown (excluded)
    """
    root = ET.fromstring(xml_content)
    records = []
    for road in root.iter("ROAD"):
        road_id = road.findtext("roadSegID") or ""
        road_name = road.findtext("roadSegName") or ""

        # Count cells by status
        occupied = 0
        available = 0
        for cell in road.iter("cell"):
            status = cell.findtext("cellStatus")
            if status == "1":
                occupied += 1
            elif status == "2":
                available += 1
            # status == "0" is unknown, skip

        total = occupied + available
        if total == 0:
            continue

        usage_rate = occupied / total

        records.append({
            "source": "taipei",
            "road_id": road_id,
            "road_name": road_name,
            "district": extract_district_taipei(road_name),
            "total_spots": total,
            "available_spots": available,
            "usage_rate": round(usage_rate, 4),
            "latitude": None,
            "longitude": None,
        })
    return records


def fetch_taipei() -> list[dict]:
    """Fetch and parse Taipei real-time parking data."""
    try:
        res = httpx.get(TAIPEI_URL, timeout=15)
        res.raise_for_status()
        return parse_taipei_xml(res.text)
    except Exception as e:
        print(f"[fetch_taipei] Failed: {e}")
        return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_fetcher.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add data/fetcher.py tests/test_fetcher.py
git commit -m "feat: add Taipei XML parking data parser"
```

---

## Task 5: New Taipei Fetcher (CSV Parser)

**Files:**
- Modify: `data/fetcher.py`
- Modify: `tests/test_fetcher.py`

- [ ] **Step 1: Write the failing test for New Taipei CSV parsing**

Add to `tests/test_fetcher.py`:

```python
import io
from data.fetcher import parse_ntpc_csv

SAMPLE_NTPC_CSV = """id,cellid,name,day,hour,pay,paycash,memo,roadid,roadname,cellstatus,isnowcash,parkingstatus,latitude,longitude,countycode,areacode
155355,0,時段性禁停停車位,週一-週五,07:00-20:00,計時收費,30元/時,"禁停0700-0900,1700-1900;",T63,建一路,Y,false,3,25.001812,121.487941,65000,65000030
155362,0,時段性禁停停車位,週一-週五,07:00-20:00,計時收費,30元/時,"禁停0700-0900,1700-1900;",T63,建一路,N,false,3,25.001441,121.487956,65000,65000030
155363,0,時段性禁停停車位,週一-週五,07:00-20:00,計時收費,30元/時,,T64,中正路,Y,false,3,25.002000,121.488000,65000,65000030
155364,0,時段性禁停停車位,週一-週五,07:00-20:00,計時收費,30元/時,,T64,中正路,Y,false,3,25.002100,121.488100,65000,65000030
"""


def test_parse_ntpc_csv_aggregates_by_road():
    records = parse_ntpc_csv(SAMPLE_NTPC_CSV)
    # 2 roads: 建一路 (2 cells) and 中正路 (2 cells)
    assert len(records) == 2


def test_parse_ntpc_csv_usage_rate():
    records = parse_ntpc_csv(SAMPLE_NTPC_CSV)
    # Sort by road_name for deterministic order
    records.sort(key=lambda r: r["road_name"])
    # 中正路: 2 cells, both Y (occupied) → usage_rate = 1.0
    assert records[0]["road_name"] == "中正路"
    assert records[0]["usage_rate"] == 1.0
    assert records[0]["total_spots"] == 2
    assert records[0]["available_spots"] == 0
    # 建一路: 2 cells, 1 Y + 1 N → usage_rate = 0.5
    assert records[1]["road_name"] == "建一路"
    assert records[1]["usage_rate"] == 0.5
    assert records[1]["available_spots"] == 1


def test_parse_ntpc_csv_district_from_areacode():
    records = parse_ntpc_csv(SAMPLE_NTPC_CSV)
    for r in records:
        assert r["district"] == "中和區"  # areacode 65000030


def test_parse_ntpc_csv_has_coordinates():
    records = parse_ntpc_csv(SAMPLE_NTPC_CSV)
    for r in records:
        assert r["latitude"] is not None
        assert r["longitude"] is not None
        assert r["source"] == "ntpc"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_fetcher.py::test_parse_ntpc_csv_aggregates_by_road -v`
Expected: FAIL — `ImportError: cannot import name 'parse_ntpc_csv'`

- [ ] **Step 3: Add parse_ntpc_csv and fetch_ntpc to data/fetcher.py**

Append to `data/fetcher.py`:

```python
def parse_ntpc_csv(csv_content: str) -> list[dict]:
    """Parse New Taipei parking CSV into normalized records, aggregated by road.

    cellstatus: Y=occupied, N=available.
    Aggregates individual parking cells by roadname.
    """
    df = pd.read_csv(io.StringIO(csv_content), dtype=str)
    df["is_occupied"] = df["cellstatus"] == "Y"
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    grp = df.groupby(["roadid", "roadname", "areacode"]).agg(
        total_spots=("cellstatus", "count"),
        occupied_spots=("is_occupied", "sum"),
        latitude=("latitude", "mean"),
        longitude=("longitude", "mean"),
    ).reset_index()

    grp["available_spots"] = grp["total_spots"] - grp["occupied_spots"]
    grp["usage_rate"] = grp["occupied_spots"] / grp["total_spots"]

    records = []
    for _, row in grp.iterrows():
        records.append({
            "source": "ntpc",
            "road_id": row["roadid"],
            "road_name": row["roadname"],
            "district": extract_district_ntpc(row["areacode"]),
            "total_spots": int(row["total_spots"]),
            "available_spots": int(row["available_spots"]),
            "usage_rate": round(float(row["usage_rate"]), 4),
            "latitude": float(row["latitude"]) if pd.notna(row["latitude"]) else None,
            "longitude": float(row["longitude"]) if pd.notna(row["longitude"]) else None,
        })
    return records


def fetch_ntpc() -> list[dict]:
    """Fetch and parse New Taipei real-time parking data."""
    try:
        res = httpx.get(NTPC_URL, timeout=15)
        res.raise_for_status()
        return parse_ntpc_csv(res.text)
    except Exception as e:
        print(f"[fetch_ntpc] Failed: {e}")
        return []
```

Also add `import io` at the top of `data/fetcher.py`.

- [ ] **Step 4: Run all fetcher tests to verify they pass**

Run: `pytest tests/test_fetcher.py -v`
Expected: All 7 tests PASS (3 Taipei + 4 New Taipei).

- [ ] **Step 5: Smoke-test with real API**

Run: `python -c "from data.fetcher import fetch_taipei, fetch_ntpc; tp=fetch_taipei(); nt=fetch_ntpc(); print(f'Taipei: {len(tp)} roads, NTPC: {len(nt)} roads'); print(tp[0] if tp else 'EMPTY'); print(nt[0] if nt else 'EMPTY')"`

Expected: Prints record counts and a sample record from each city. Verify:
- Taipei records have `source='taipei'`, `latitude=None`, `usage_rate` between 0 and 1
- NTPC records have `source='ntpc'`, `latitude` / `longitude` filled, `district` is a real district name

- [ ] **Step 6: Commit**

```bash
git add data/fetcher.py tests/test_fetcher.py
git commit -m "feat: add New Taipei CSV parking data parser"
```

---

## Task 6: Weather and Holiday Helpers

**Files:**
- Create: `data/weather.py`
- Create: `data/holidays.py`

- [ ] **Step 1: Create data/weather.py**

```python
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

CWA_URL = (
    "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"
    "?Authorization={key}&locationName={location}&elementName=Wx"
)


def get_weather(location: str = "臺北市") -> dict:
    """Fetch current weather from CWA API.

    Returns: {"weather_main": "clear"|"rain"|"cloudy"|"typhoon"|"unknown"}
    """
    key = os.getenv("CWA_API_KEY", "")
    if not key:
        return {"weather_main": "unknown"}
    try:
        url = CWA_URL.format(key=key, location=location)
        res = httpx.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        wx = data["records"]["location"][0]["weatherElement"][0]["time"][0]
        wx_name = wx["parameter"]["parameterName"]
        if "雨" in wx_name or "雷" in wx_name:
            return {"weather_main": "rain"}
        elif "颱" in wx_name:
            return {"weather_main": "typhoon"}
        elif "陰" in wx_name or "雲" in wx_name:
            return {"weather_main": "cloudy"}
        else:
            return {"weather_main": "clear"}
    except Exception as e:
        print(f"[get_weather] Failed: {e}")
        return {"weather_main": "unknown"}
```

- [ ] **Step 2: Create data/holidays.py**

```python
import httpx

_holiday_cache: dict[int, set[str]] = {}


def get_holiday_set(year: int) -> set[str]:
    """Load Taiwan holidays for a given year. Returns set of 'YYYYMMDD' strings.

    Cached per year to avoid repeated requests.
    """
    if year in _holiday_cache:
        return _holiday_cache[year]
    url = f"https://cdn.jsdelivr.net/gh/ruyut/TaiwanCalendar/data/{year}.json"
    try:
        data = httpx.get(url, timeout=10).json()
        holidays = {d["date"] for d in data if d.get("isHoliday")}
        _holiday_cache[year] = holidays
        return holidays
    except Exception as e:
        print(f"[get_holiday_set] Failed: {e}")
        return set()


def is_holiday(year: int, month: int, day: int) -> bool:
    """Check if a specific date is a holiday."""
    date_str = f"{year}{month:02d}{day:02d}"
    return date_str in get_holiday_set(year)
```

- [ ] **Step 3: Smoke-test both helpers**

Run: `python -c "from data.holidays import get_holiday_set; h=get_holiday_set(2026); print(f'{len(h)} holidays in 2026'); print('20260101' in h)"`
Expected: Prints holiday count and `True` (New Year's Day).

Run: `python -c "from data.weather import get_weather; print(get_weather())"`
Expected: Prints a dict with `weather_main` key (value depends on current weather; `unknown` if no CWA key in `.env`).

- [ ] **Step 4: Commit**

```bash
git add data/weather.py data/holidays.py
git commit -m "feat: add weather and holiday data helpers"
```

---

## Task 7: Snapshot System

**Files:**
- Create: `data/snapshot.py`

- [ ] **Step 1: Create data/snapshot.py**

```python
from datetime import datetime
from sqlalchemy import text
from api.database import get_engine
from data.fetcher import fetch_taipei, fetch_ntpc
from data.weather import get_weather
from data.holidays import is_holiday


def save_snapshot():
    """Fetch real-time data from both cities and save to database.

    Called every SNAPSHOT_INTERVAL_MINUTES by APScheduler.
    """
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
```

- [ ] **Step 2: Smoke-test snapshot manually**

Set up `.env` with your `DATABASE_URL` (or let it default to SQLite), then:

Run: `python -c "from api.database import init_db; init_db(); from data.snapshot import save_snapshot; save_snapshot()"`
Expected: Prints `[snapshot] HH:MM Saved NNNN records`. Check DB has rows.

- [ ] **Step 3: Commit**

```bash
git add data/snapshot.py
git commit -m "feat: add snapshot system for periodic data collection"
```

---

## Task 8: FastAPI Application + Realtime Endpoint

**Files:**
- Create: `api/main.py`
- Create: `api/routes/realtime.py`
- Create: `api/routes/snapshot.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write the failing test for /api/realtime**

```python
# tests/test_api.py
from unittest.mock import patch
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_realtime_returns_200():
    with patch("api.routes.realtime.fetch_taipei", return_value=[]):
        with patch("api.routes.realtime.fetch_ntpc", return_value=[]):
            res = client.get("/api/realtime")
    assert res.status_code == 200
    data = res.json()
    assert "records" in data
    assert "count" in data
    assert "fetched_at" in data


def test_realtime_returns_records():
    mock_tp = [{"source": "taipei", "road_id": "1", "road_name": "test",
                "district": "中山區", "total_spots": 10, "available_spots": 3,
                "usage_rate": 0.7, "latitude": None, "longitude": None}]
    with patch("api.routes.realtime.fetch_taipei", return_value=mock_tp):
        with patch("api.routes.realtime.fetch_ntpc", return_value=[]):
            res = client.get("/api/realtime")
    data = res.json()
    assert data["count"] == 1
    assert data["records"][0]["road_name"] == "test"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'api.main'`

- [ ] **Step 3: Create api/routes/realtime.py**

```python
from datetime import datetime
from fastapi import APIRouter
from data.fetcher import fetch_taipei, fetch_ntpc

router = APIRouter(prefix="/api")


@router.get("/realtime")
def get_realtime():
    """Fetch real-time parking data from both cities."""
    tp = fetch_taipei()
    ntpc = fetch_ntpc()
    all_records = tp + ntpc
    return {
        "records": all_records,
        "count": len(all_records),
        "fetched_at": datetime.now().isoformat(),
    }
```

- [ ] **Step 4: Create api/routes/snapshot.py**

```python
from fastapi import APIRouter
from sqlalchemy import text
from api.database import get_engine

router = APIRouter(prefix="/api")


@router.get("/snapshots/status")
def get_snapshot_status():
    """Return snapshot collection statistics."""
    engine = get_engine()
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM snapshots")).scalar() or 0
        latest = conn.execute(
            text("SELECT MAX(snapshot_time) FROM snapshots")
        ).scalar()
        days = conn.execute(
            text("SELECT COUNT(DISTINCT date(snapshot_time)) FROM snapshots")
        ).scalar() or 0
        today_count = conn.execute(
            text("SELECT COUNT(*) FROM snapshots WHERE date(snapshot_time) = date('now')")
        ).scalar() or 0
    return {
        "total_records": total,
        "latest_snapshot": latest,
        "days_collected": days,
        "today_snapshots": today_count,
    }
```

- [ ] **Step 5: Create api/main.py**

```python
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
    """Initialize DB and start snapshot scheduler on startup."""
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
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_api.py -v`
Expected: Both tests PASS.

- [ ] **Step 7: Smoke-test the API server**

Run: `uvicorn api.main:app --reload --port 8000`

Open browser: `http://localhost:8000/docs`
Expected: FastAPI Swagger UI with `/api/realtime` and `/api/snapshots/status` endpoints.

Test: `http://localhost:8000/api/realtime`
Expected: JSON with `records`, `count`, `fetched_at`.

- [ ] **Step 8: Commit**

```bash
git add api/main.py api/routes/realtime.py api/routes/snapshot.py tests/test_api.py
git commit -m "feat: add FastAPI app with realtime and snapshot status endpoints"
```

---

## Task 9: OPR Analysis Module

**Files:**
- Create: `analysis/opr.py`
- Create: `tests/test_opr.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_opr.py
import pandas as pd
from analysis.opr import daily_opr_summary, hourly_pattern, week_over_week


def make_sample_df():
    """Create a sample snapshot DataFrame for testing."""
    rows = []
    # 3 days × 2 districts × 4 snapshots/day
    for day_offset in range(3):
        date = f"2026-06-0{day_offset + 1}"
        for hour in [8, 12, 16, 20]:
            for district, rate in [("大安區", 0.85), ("板橋區", 0.65)]:
                rows.append({
                    "date": date,
                    "district": district,
                    "hour": hour,
                    "day_of_week": day_offset,  # Mon, Tue, Wed
                    "is_holiday": 0,
                    "is_weekend": 0,
                    "usage_rate": rate + (hour - 12) * 0.01,  # slight variation by hour
                    "snapshot_time": pd.Timestamp(f"{date} {hour}:00:00"),
                    "weather_main": "clear",
                    "road_name": f"{district}路段1",
                    "source": "taipei",
                })
    return pd.DataFrame(rows)


def test_daily_opr_summary_shape():
    df = make_sample_df()
    result = daily_opr_summary(df)
    # 3 days × 2 districts = 6 rows
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
    # Should include both districts
    assert len(result) >= 4  # at least 4 hours


def test_week_over_week():
    df = make_sample_df()
    df["snapshot_time"] = pd.to_datetime(df["snapshot_time"])
    result = week_over_week(df)
    assert "week" in result.columns
    assert "district" in result.columns
    assert "usage_rate" in result.columns
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_opr.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'analysis.opr'`

- [ ] **Step 3: Implement analysis/opr.py**

```python
import pandas as pd
from sqlalchemy import text
from datetime import datetime, timedelta
from api.database import get_engine


def get_snapshot_df(days: int = 14) -> pd.DataFrame:
    """Read recent snapshots from the database."""
    engine = get_engine()
    since = (datetime.now() - timedelta(days=days)).isoformat()
    df = pd.read_sql(
        "SELECT * FROM snapshots WHERE snapshot_time > :since ORDER BY snapshot_time",
        engine,
        params={"since": since},
    )
    if len(df) == 0:
        return df
    df["snapshot_time"] = pd.to_datetime(df["snapshot_time"])
    df["date"] = df["snapshot_time"].dt.date.astype(str)
    return df


def daily_opr_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Daily OPR summary per district."""
    return (
        df.groupby(["date", "district"])
        .agg(
            avg_usage=("usage_rate", "mean"),
            peak_usage=("usage_rate", "max"),
            min_usage=("usage_rate", "min"),
            sample_count=("usage_rate", "count"),
        )
        .reset_index()
        .round(3)
    )


def hourly_pattern(df: pd.DataFrame, district: str = None) -> pd.DataFrame:
    """24-hour usage rate pattern, split by weekday vs holiday."""
    if district:
        df = df[df["district"] == district]
    return (
        df.groupby(["hour", "is_holiday"])["usage_rate"]
        .mean()
        .reset_index()
        .round(3)
    )


def week_over_week(df: pd.DataFrame) -> pd.DataFrame:
    """Week-over-week usage comparison by district."""
    df = df.copy()
    df["week"] = df["snapshot_time"].dt.isocalendar().week.astype(int)
    return (
        df.groupby(["week", "district"])["usage_rate"]
        .mean()
        .reset_index()
        .round(3)
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_opr.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add analysis/opr.py tests/test_opr.py
git commit -m "feat: add OPR analysis module (daily summary, hourly pattern, WoW)"
```

---

## Task 10: Anomaly Detection Module

**Files:**
- Create: `analysis/anomaly.py`
- Create: `tests/test_anomaly.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_anomaly.py
import pandas as pd
from analysis.anomaly import anomaly_detect


def make_anomaly_df():
    """Create DataFrame with 7 days of normal data + 1 anomalous reading today."""
    rows = []
    # 6 days of history: 大安區 at hour 14 → usage_rate ~0.80 (std ~0.02)
    for day in range(1, 7):
        rows.append({
            "date": f"2026-06-0{day}",
            "district": "大安區",
            "road_name": "忠孝東路",
            "hour": 14,
            "usage_rate": 0.80 + (day % 3) * 0.01,
            "is_holiday": 0,
        })
    # Today: anomalously high
    rows.append({
        "date": "2026-06-07",
        "district": "大安區",
        "road_name": "忠孝東路",
        "hour": 14,
        "usage_rate": 0.98,  # way above 0.80 average
        "is_holiday": 0,
    })
    # Today: normal reading for 板橋區
    rows.append({
        "date": "2026-06-07",
        "district": "板橋區",
        "road_name": "文化路",
        "hour": 14,
        "usage_rate": 0.60,
        "is_holiday": 0,
    })
    # History for 板橋區
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
    # Should find 大安區 as anomalous
    assert len(result) >= 1
    assert "大安區" in result["district"].values


def test_anomaly_detect_excludes_normal():
    df = make_anomaly_df()
    result = anomaly_detect(df, today="2026-06-07", sigma=2.0)
    # 板橋區 is normal, should not appear
    assert "板橋區" not in result["district"].values


def test_anomaly_detect_has_z_score():
    df = make_anomaly_df()
    result = anomaly_detect(df, today="2026-06-07", sigma=2.0)
    assert "z_score" in result.columns
    # 大安區's z_score should be positive (above average)
    da = result[result["district"] == "大安區"]
    assert da.iloc[0]["z_score"] > 2.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_anomaly.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'analysis.anomaly'`

- [ ] **Step 3: Implement analysis/anomaly.py**

```python
import pandas as pd
from datetime import datetime


def anomaly_detect(
    df: pd.DataFrame, today: str = None, sigma: float = 2.0
) -> pd.DataFrame:
    """Detect anomalous districts where today's usage deviates > N sigma from historical mean.

    Args:
        df: Snapshot DataFrame with columns: date, district, hour, usage_rate, road_name
        today: Date string 'YYYY-MM-DD'. Defaults to today.
        sigma: Number of standard deviations for anomaly threshold.

    Returns:
        DataFrame of anomalous readings with z_score column.
    """
    if today is None:
        today = datetime.now().date().isoformat()

    today_df = df[df["date"] == today]
    if today_df.empty:
        return pd.DataFrame()

    # Historical baseline (excluding today)
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
    # Minimum std to avoid division by near-zero
    hist_stats["hist_std"] = hist_stats["hist_std"].clip(lower=0.01)

    merged = today_df.merge(hist_stats, on=["district", "hour"], how="inner")
    if merged.empty:
        return pd.DataFrame()

    merged["z_score"] = (merged["usage_rate"] - merged["hist_mean"]) / merged["hist_std"]

    anomalies = merged[merged["z_score"].abs() > sigma].sort_values(
        "z_score", ascending=False
    )
    return anomalies
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_anomaly.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add analysis/anomaly.py tests/test_anomaly.py
git commit -m "feat: add z-score anomaly detection module"
```

---

## Task 11: OPR API Routes

**Files:**
- Create: `api/routes/opr.py`
- Modify: `api/main.py` (add router)

- [ ] **Step 1: Create api/routes/opr.py**

```python
from fastapi import APIRouter, Query
from analysis.opr import get_snapshot_df, daily_opr_summary, hourly_pattern, week_over_week
from analysis.anomaly import anomaly_detect

router = APIRouter(prefix="/api/opr")


@router.get("/daily")
def get_daily_summary(days: int = Query(default=14, ge=1, le=90)):
    """Daily OPR summary per district."""
    df = get_snapshot_df(days=days)
    if df.empty:
        return {"data": [], "message": "No snapshot data yet"}
    summary = daily_opr_summary(df)
    return {"data": summary.to_dict(orient="records")}


@router.get("/hourly")
def get_hourly_pattern(
    days: int = Query(default=14, ge=1, le=90),
    district: str = Query(default=None),
):
    """24-hour usage pattern, optionally filtered by district."""
    df = get_snapshot_df(days=days)
    if df.empty:
        return {"data": [], "message": "No snapshot data yet"}
    pattern = hourly_pattern(df, district=district)
    return {"data": pattern.to_dict(orient="records")}


@router.get("/wow")
def get_week_over_week(days: int = Query(default=14, ge=1, le=90)):
    """Week-over-week usage comparison."""
    df = get_snapshot_df(days=days)
    if df.empty:
        return {"data": [], "message": "No snapshot data yet"}
    wow = week_over_week(df)
    return {"data": wow.to_dict(orient="records")}


@router.get("/anomalies")
def get_anomalies(days: int = Query(default=14, ge=1, le=90), sigma: float = 2.0):
    """Detect anomalous districts today."""
    df = get_snapshot_df(days=days)
    if df.empty:
        return {"data": [], "message": "No snapshot data yet"}
    anomalies = anomaly_detect(df, sigma=sigma)
    return {"data": anomalies.to_dict(orient="records")}
```

- [ ] **Step 2: Register the router in api/main.py**

Add this import and registration to `api/main.py`:

```python
from api.routes import realtime, snapshot, opr
# ...
app.include_router(opr.router)
```

- [ ] **Step 3: Verify the API server starts and /docs shows all routes**

Run: `uvicorn api.main:app --reload --port 8000`

Open: `http://localhost:8000/docs`
Expected: Swagger UI shows `/api/opr/daily`, `/api/opr/hourly`, `/api/opr/wow`, `/api/opr/anomalies` in addition to previous routes.

- [ ] **Step 4: Commit**

```bash
git add api/routes/opr.py api/main.py
git commit -m "feat: add OPR analysis API routes"
```

---

## Task 12: Streamlit Dashboard — Real-time Map Page

**Files:**
- Create: `dashboard/app.py`
- Create: `dashboard/pages/1_即時地圖.py`

- [ ] **Step 1: Create dashboard/app.py**

```python
import streamlit as st

st.set_page_config(
    page_title="停車 OPR 分析平台",
    page_icon="🅿️",
    layout="wide",
)

st.title("停車 OPR 分析平台")
st.markdown("台北市 + 新北市路邊停車即時數據與營運績效分析")

st.markdown("""
### 功能頁面

- **即時地圖** — 新北市停車使用率地圖 + 全區統計
- **OPR 分析** — 每日彙總、時段模式、週環比
- **異常偵測** — 今日使用率異常路段警示

👈 從左側選單選擇頁面
""")
```

- [ ] **Step 2: Create dashboard/pages/1_即時地圖.py**

```python
import streamlit as st
import pydeck as pdk
import pandas as pd
import httpx

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="即時停車地圖", layout="wide")
st.title("即時停車使用率")


@st.cache_data(ttl=120)
def load_realtime():
    try:
        res = httpx.get(f"{API_BASE}/api/realtime", timeout=15)
        res.raise_for_status()
        return pd.DataFrame(res.json()["records"])
    except Exception as e:
        st.error(f"無法連線 API: {e}")
        return pd.DataFrame()


df = load_realtime()

if df.empty:
    st.warning("無法取得即時資料，請確認 API 是否啟動")
    st.stop()

# Status bar
col_status1, col_status2, col_status3, col_refresh = st.columns([1, 1, 1, 1])
with col_status1:
    st.metric("資料筆數", len(df))
with col_status2:
    st.metric("整體使用率", f"{df['usage_rate'].mean():.1%}")
with col_status3:
    taipei_count = len(df[df["source"] == "taipei"])
    ntpc_count = len(df[df["source"] == "ntpc"])
    st.metric("台北/新北", f"{taipei_count} / {ntpc_count}")
with col_refresh:
    if st.button("🔄 重新整理"):
        st.cache_data.clear()
        st.rerun()

st.divider()

# Layout: map left, stats right
col_map, col_stats = st.columns([2, 1])


def usage_to_color(rate):
    if rate >= 0.80:
        return [229, 57, 53, 200]  # Red
    elif rate >= 0.60:
        return [251, 140, 0, 200]  # Orange
    else:
        return [67, 160, 71, 200]  # Green


with col_map:
    st.subheader("新北市停車使用率地圖")
    df_map = df[
        (df["latitude"].notna())
        & (df["longitude"].notna())
        & (df["source"] == "ntpc")
    ].copy()

    if not df_map.empty:
        df_map["color"] = df_map["usage_rate"].apply(usage_to_color)
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_map,
            get_position=["longitude", "latitude"],
            get_color="color",
            get_radius=50,
            pickable=True,
        )
        view = pdk.ViewState(latitude=25.02, longitude=121.47, zoom=11, pitch=0)
        st.pydeck_chart(
            pdk.Deck(
                layers=[layer],
                initial_view_state=view,
                tooltip={"text": "{road_name}\n使用率: {usage_rate}"},
                map_style="light",
            )
        )
    else:
        st.info("無座標資料可顯示")

    st.caption("🔴 ≥80%　🟠 ≥60%　🟢 <60%")

with col_stats:
    st.subheader("各區使用率排行")
    district_stats = (
        df.groupby("district")["usage_rate"]
        .mean()
        .sort_values(ascending=False)
    )
    for district, rate in district_stats.head(12).items():
        icon = "🔴" if rate >= 0.80 else "🟡" if rate >= 0.60 else "🟢"
        st.write(f"{icon} **{district}**：{rate:.1%}")
```

- [ ] **Step 3: Test the dashboard**

Start API first: `uvicorn api.main:app --port 8000`
Then in another terminal: `streamlit run dashboard/app.py`

Expected: Browser opens with the main page. Click "即時地圖" in the sidebar. Should see:
- Status metrics at top
- New Taipei scatter map on the left
- District ranking on the right

- [ ] **Step 4: Commit**

```bash
git add dashboard/app.py dashboard/pages/1_即時地圖.py
git commit -m "feat: add Streamlit dashboard with real-time map page"
```

---

## Task 13: Streamlit Dashboard — OPR Analysis Page

**Files:**
- Create: `dashboard/pages/2_OPR分析.py`

- [ ] **Step 1: Create dashboard/pages/2_OPR分析.py**

```python
import streamlit as st
import plotly.express as px
import pandas as pd
import httpx

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="OPR 分析", layout="wide")
st.title("OPR 統計分析")

days = st.slider("分析天數", min_value=3, max_value=90, value=14)


@st.cache_data(ttl=300)
def fetch_opr(endpoint, params=None):
    try:
        res = httpx.get(f"{API_BASE}/api/opr/{endpoint}", params=params, timeout=15)
        res.raise_for_status()
        data = res.json()
        if data.get("message"):
            return pd.DataFrame(), data["message"]
        return pd.DataFrame(data["data"]), None
    except Exception as e:
        return pd.DataFrame(), str(e)


tab1, tab2, tab3 = st.tabs(["每日彙總", "時段模式", "週環比"])

with tab1:
    df, msg = fetch_opr("daily", {"days": days})
    if msg:
        st.warning(msg)
    elif not df.empty:
        fig = px.line(
            df,
            x="date",
            y="avg_usage",
            color="district",
            title="每日平均使用率趨勢",
            labels={"avg_usage": "使用率", "date": "日期"},
        )
        fig.update_yaxes(tickformat=".0%", range=[0, 1])
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(
            df.sort_values(["date", "avg_usage"], ascending=[False, False]),
            use_container_width=True,
        )

with tab2:
    districts_df, _ = fetch_opr("daily", {"days": days})
    if not districts_df.empty:
        district_list = sorted(districts_df["district"].unique())
        district = st.selectbox("選擇行政區", district_list)
        pattern_df, msg = fetch_opr("hourly", {"days": days, "district": district})
        if msg:
            st.warning(msg)
        elif not pattern_df.empty:
            pattern_df["is_holiday"] = pattern_df["is_holiday"].map(
                {0: "平日", 1: "假日"}
            )
            fig = px.line(
                pattern_df,
                x="hour",
                y="usage_rate",
                color="is_holiday",
                title=f"{district} — 24 小時使用率模式",
                labels={"usage_rate": "使用率", "hour": "小時", "is_holiday": "類型"},
                color_discrete_map={"平日": "#1565c0", "假日": "#e53935"},
            )
            fig.update_yaxes(tickformat=".0%")
            fig.update_xaxes(dtick=1)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("尚無資料")

with tab3:
    wow_df, msg = fetch_opr("wow", {"days": days})
    if msg:
        st.warning(msg)
    elif not wow_df.empty:
        fig = px.bar(
            wow_df,
            x="district",
            y="usage_rate",
            color="week",
            barmode="group",
            title="週環比使用率對比",
        )
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)
```

- [ ] **Step 2: Test the page**

With API and Streamlit running, click "OPR分析" in sidebar.
- If no snapshot data yet: should show "No snapshot data yet" warning
- If data exists: should show charts and table

- [ ] **Step 3: Commit**

```bash
git add dashboard/pages/2_OPR分析.py
git commit -m "feat: add OPR analysis dashboard page"
```

---

## Task 14: Streamlit Dashboard — Anomaly Detection Page

**Files:**
- Create: `dashboard/pages/3_異常偵測.py`

- [ ] **Step 1: Create dashboard/pages/3_異常偵測.py**

```python
import streamlit as st
import pandas as pd
import httpx

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="異常偵測", layout="wide")
st.title("異常偵測")
st.caption("偵測今日使用率與歷史均值差異超過 2σ 的路段")

sigma = st.slider("異常門檻 (σ)", min_value=1.0, max_value=4.0, value=2.0, step=0.5)


@st.cache_data(ttl=300)
def fetch_anomalies(sigma_val):
    try:
        res = httpx.get(
            f"{API_BASE}/api/opr/anomalies",
            params={"days": 14, "sigma": sigma_val},
            timeout=15,
        )
        res.raise_for_status()
        data = res.json()
        if data.get("message"):
            return pd.DataFrame(), data["message"]
        return pd.DataFrame(data["data"]), None
    except Exception as e:
        return pd.DataFrame(), str(e)


anomalies, msg = fetch_anomalies(sigma)

if msg:
    st.warning(msg)
elif anomalies.empty:
    st.success("今日無異常路段 ✓")
else:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("異常路段數", len(anomalies))
    with col2:
        high = len(anomalies[anomalies["z_score"] > 0])
        st.metric("高於均值", high)
    with col3:
        low = len(anomalies[anomalies["z_score"] < 0])
        st.metric("低於均值", low)

    st.divider()

    for _, row in anomalies.iterrows():
        z = row["z_score"]
        direction = "高於" if z > 0 else "低於"
        if z > 0:
            st.error(
                f"**{row['district']} {row.get('road_name', '')}**\n\n"
                f"目前 {row['usage_rate']:.1%}，歷史均值 {row.get('hist_mean', 0):.1%}\n\n"
                f"`+{abs(z):.1f}σ` — 異常{direction}歷史均值"
            )
        else:
            st.warning(
                f"**{row['district']} {row.get('road_name', '')}**\n\n"
                f"目前 {row['usage_rate']:.1%}，歷史均值 {row.get('hist_mean', 0):.1%}\n\n"
                f"`-{abs(z):.1f}σ` — 異常{direction}歷史均值"
            )
```

- [ ] **Step 2: Test the page**

With API and Streamlit running, click "異常偵測" in sidebar.
Expected: Shows anomaly results or "今日無異常路段" if insufficient data.

- [ ] **Step 3: Commit**

```bash
git add dashboard/pages/3_異常偵測.py
git commit -m "feat: add anomaly detection dashboard page"
```

---

## Task 15: Run All Tests + Final Verification

**Files:**
- No new files

- [ ] **Step 1: Run the full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS (districts: 5, fetcher: 7, opr: 5, anomaly: 3, api: 2 = 22 total).

- [ ] **Step 2: Run the full application stack**

Terminal 1: `uvicorn api.main:app --port 8000`
Terminal 2: `streamlit run dashboard/app.py`

Walk through each page:
1. Main page loads
2. 即時地圖: map displays, stats show
3. OPR分析: tabs work (data may be sparse if just started)
4. 異常偵測: page renders

- [ ] **Step 3: Trigger a manual snapshot and verify data flows**

Run: `python -c "from data.snapshot import save_snapshot; save_snapshot()"`

Then check snapshot status via API:
Run: `curl http://localhost:8000/api/snapshots/status`
Expected: `total_records` > 0.

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: address issues found during integration testing"
```

---

## Task 16: Deployment Setup

**Files:**
- Create: `README.md`
- Create: `Procfile` (optional for Streamlit Cloud)

- [ ] **Step 1: Create README.md**

```markdown
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
```

- [ ] **Step 2: Set up Neon PostgreSQL**

1. Go to https://neon.tech and create a free-tier project
2. Copy the connection string: `postgresql://user:pass@host/dbname?sslmode=require`
3. Add to `.env`: `DATABASE_URL=postgresql://...`
4. Run: `python -c "from api.database import init_db; init_db(); print('Neon DB ready')"`

- [ ] **Step 3: Deploy to Streamlit Community Cloud**

1. Push to GitHub (public repo)
2. Go to https://share.streamlit.io
3. Select repo, main file: `dashboard/app.py`
4. Add Secrets:
   ```
   DATABASE_URL = "postgresql://..."
   CWA_API_KEY = "your_key"
   ```
5. Note: The Streamlit app needs to call the FastAPI backend. For Streamlit Cloud, consider running FastAPI within the same process or using a deployed FastAPI backend on a platform like Render.

**Important deployment note:** Streamlit Cloud only runs Streamlit. The FastAPI backend and APScheduler need a separate host. Options:
- **Simplest:** Refactor dashboard pages to call `data/fetcher.py` and `analysis/opr.py` directly (bypass API for the dashboard), and keep FastAPI + scheduler on Render free tier.
- **Alternative:** Run everything on Render with a `Procfile`.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup and deployment instructions"
```

---

## Task 17: Streamlit Direct-DB Mode (Deployment Compatibility)

**Files:**
- Modify: `dashboard/pages/1_即時地圖.py`
- Modify: `dashboard/pages/2_OPR分析.py`
- Modify: `dashboard/pages/3_異常偵測.py`

Streamlit Cloud can't host FastAPI. Refactor dashboard pages to import Python modules directly when `API_BASE` is not set, falling back to direct function calls.

- [ ] **Step 1: Add a helper for data access mode**

Create `dashboard/data_access.py`:

```python
import os
import pandas as pd
import httpx

API_BASE = os.getenv("API_BASE", "")


def get_realtime_df() -> pd.DataFrame:
    """Get real-time data — via API if available, otherwise direct fetch."""
    if API_BASE:
        try:
            res = httpx.get(f"{API_BASE}/api/realtime", timeout=15)
            res.raise_for_status()
            return pd.DataFrame(res.json()["records"])
        except Exception:
            pass
    # Direct mode
    from data.fetcher import fetch_taipei, fetch_ntpc
    tp = fetch_taipei()
    ntpc = fetch_ntpc()
    return pd.DataFrame(tp + ntpc)


def get_opr_data(endpoint: str, params: dict = None) -> tuple[pd.DataFrame, str | None]:
    """Get OPR data — via API if available, otherwise direct computation."""
    if API_BASE:
        try:
            res = httpx.get(f"{API_BASE}/api/opr/{endpoint}", params=params, timeout=15)
            res.raise_for_status()
            data = res.json()
            if data.get("message"):
                return pd.DataFrame(), data["message"]
            return pd.DataFrame(data["data"]), None
        except Exception:
            pass
    # Direct mode
    from analysis.opr import get_snapshot_df, daily_opr_summary, hourly_pattern, week_over_week
    days = (params or {}).get("days", 14)
    df = get_snapshot_df(days=days)
    if df.empty:
        return pd.DataFrame(), "尚無快照資料"
    if endpoint == "daily":
        return daily_opr_summary(df), None
    elif endpoint == "hourly":
        return hourly_pattern(df, district=(params or {}).get("district")), None
    elif endpoint == "wow":
        return week_over_week(df), None
    return pd.DataFrame(), "Unknown endpoint"


def get_anomalies(days: int = 14, sigma: float = 2.0) -> tuple[pd.DataFrame, str | None]:
    """Get anomaly data — via API if available, otherwise direct computation."""
    if API_BASE:
        try:
            res = httpx.get(
                f"{API_BASE}/api/opr/anomalies",
                params={"days": days, "sigma": sigma},
                timeout=15,
            )
            res.raise_for_status()
            data = res.json()
            if data.get("message"):
                return pd.DataFrame(), data["message"]
            return pd.DataFrame(data["data"]), None
        except Exception:
            pass
    # Direct mode
    from analysis.opr import get_snapshot_df
    from analysis.anomaly import anomaly_detect
    df = get_snapshot_df(days=days)
    if df.empty:
        return pd.DataFrame(), "尚無快照資料"
    result = anomaly_detect(df, sigma=sigma)
    return result, None
```

- [ ] **Step 2: Update dashboard pages to use data_access.py**

Replace the `httpx` calls in each page with imports from `dashboard.data_access`:

In `1_即時地圖.py`, replace the `load_realtime()` function:
```python
from dashboard.data_access import get_realtime_df

@st.cache_data(ttl=120)
def load_realtime():
    return get_realtime_df()
```

In `2_OPR分析.py`, replace `fetch_opr()`:
```python
from dashboard.data_access import get_opr_data

@st.cache_data(ttl=300)
def fetch_opr(endpoint, params=None):
    return get_opr_data(endpoint, params)
```

In `3_異常偵測.py`, replace `fetch_anomalies()`:
```python
from dashboard.data_access import get_anomalies as _get_anomalies

@st.cache_data(ttl=300)
def fetch_anomalies(sigma_val):
    return _get_anomalies(days=14, sigma=sigma_val)
```

- [ ] **Step 3: Test both modes**

Direct mode (no API): `streamlit run dashboard/app.py`
API mode: Set `API_BASE=http://localhost:8000`, run both servers.

Both should produce the same dashboard.

- [ ] **Step 4: Commit**

```bash
git add dashboard/data_access.py dashboard/pages/
git commit -m "feat: add dual data-access mode for Streamlit Cloud compatibility"
```

---

## Task 18: Final Polish and Deploy

- [ ] **Step 1: Run full test suite one last time**

Run: `pytest tests/ -v`
Expected: All 22 tests PASS.

- [ ] **Step 2: Review git log for clean history**

Run: `git log --oneline`
Expected: Clean, descriptive commit messages with no merge conflicts.

- [ ] **Step 3: Push to GitHub**

```bash
git remote add origin <your-github-repo-url>
git push -u origin main
```

- [ ] **Step 4: Deploy FastAPI to Render (free tier)**

1. Create a `render.yaml` or use Render dashboard
2. Set environment variables: `DATABASE_URL`, `CWA_API_KEY`
3. Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`

- [ ] **Step 5: Deploy Streamlit to Streamlit Cloud**

1. Connect GitHub repo on share.streamlit.io
2. Main file: `dashboard/app.py`
3. Set secrets: `DATABASE_URL`, `CWA_API_KEY`, `API_BASE` (Render URL)

- [ ] **Step 6: Verify live deployment**

Open the Streamlit Cloud URL. Check:
- 即時地圖 loads with real data
- OPR 分析 shows data (if snapshots have been running)
- 異常偵測 page renders

---

## Summary

| Task | Description | Est. Time |
|------|-------------|-----------|
| 1 | Project scaffolding | 15 min |
| 2 | Database schema + connection | 20 min |
| 3 | District code mappings | 15 min |
| 4 | Taipei XML fetcher | 30 min |
| 5 | New Taipei CSV fetcher | 30 min |
| 6 | Weather + holiday helpers | 15 min |
| 7 | Snapshot system | 20 min |
| 8 | FastAPI app + realtime route | 30 min |
| 9 | OPR analysis module | 30 min |
| 10 | Anomaly detection module | 20 min |
| 11 | OPR API routes | 15 min |
| 12 | Streamlit — map page | 30 min |
| 13 | Streamlit — OPR page | 30 min |
| 14 | Streamlit — anomaly page | 20 min |
| 15 | Integration testing | 30 min |
| 16 | Deployment setup + README | 30 min |
| 17 | Dual data-access mode | 20 min |
| 18 | Final polish + deploy | 45 min |
| **Total** | | **~7 hours** |
