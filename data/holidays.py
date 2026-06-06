import httpx

_holiday_cache: dict[int, set[str]] = {}


def get_holiday_set(year: int) -> set[str]:
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
    date_str = f"{year}{month:02d}{day:02d}"
    return date_str in get_holiday_set(year)
