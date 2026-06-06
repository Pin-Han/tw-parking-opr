import os
import httpx
from dotenv import load_dotenv

load_dotenv()

CWA_URL = (
    "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"
    "?Authorization={key}&locationName={location}&elementName=Wx"
)


def get_weather(location: str = "臺北市") -> dict:
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
