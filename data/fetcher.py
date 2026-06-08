import io
import xml.etree.ElementTree as ET
import pandas as pd
import httpx
from data.districts import extract_district_taipei, extract_district_ntpc

TAIPEI_URL = "https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_roadquery.xml"
NTPC_URL = "https://data.ntpc.gov.tw/api/datasets/54a507c4-c038-41b5-bf60-bbecb9d052c6/csv/file"


def parse_taipei_xml(xml_content: str) -> list[dict]:
    root = ET.fromstring(xml_content)
    records = []
    for road in root.iter("ROAD"):
        road_id = road.findtext("roadSegID") or ""
        road_name = road.findtext("roadSegName") or ""

        occupied = 0
        available = 0
        for cell in road.iter("cell"):
            status = cell.findtext("cellStatus")
            if status == "1":
                occupied += 1
            elif status == "2":
                available += 1

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
    try:
        res = httpx.get(TAIPEI_URL, timeout=30)
        res.raise_for_status()
        return parse_taipei_xml(res.text)
    except Exception as e:
        print(f"[fetch_taipei] Failed: {e}")
        return []


def parse_ntpc_csv(csv_content: str) -> list[dict]:
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
    try:
        res = httpx.get(NTPC_URL, timeout=30)
        res.raise_for_status()
        return parse_ntpc_csv(res.text)
    except Exception as e:
        print(f"[fetch_ntpc] Failed: {e}")
        return []
