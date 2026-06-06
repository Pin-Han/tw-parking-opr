import math
import streamlit as st
import pydeck as pdk
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dashboard.data_access import get_realtime_df
from streamlit_js_eval import get_geolocation

st.set_page_config(page_title="Live Parking Map", layout="wide")
st.title("Live Parking Occupancy")
st.caption("Real-time street parking data from Taipei and New Taipei City government APIs, refreshed every 2 minutes.")


def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate distance in km between two GPS points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@st.cache_data(ttl=120)
def load_realtime():
    return get_realtime_df()


df = load_realtime()

if df.empty:
    st.warning("Unable to fetch real-time data. Please check if the API is running.")
    st.stop()

# Get user location
loc = get_geolocation()
user_lat = None
user_lng = None
if loc and isinstance(loc, dict) and "coords" in loc:
    user_lat = loc["coords"].get("latitude")
    user_lng = loc["coords"].get("longitude")

# Summary metrics
col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
with col1:
    st.metric("Total Segments", f"{len(df):,}")
with col2:
    st.metric("Avg Occupancy", f"{df['usage_rate'].mean():.1%}")
with col3:
    high_occ = len(df[df["usage_rate"] >= 0.8])
    st.metric("High Occupancy (≥80%)", f"{high_occ:,}")
with col4:
    total_spots = df["total_spots"].sum()
    total_avail = df["available_spots"].sum()
    st.metric("Available Spots", f"{total_avail:,} / {total_spots:,}")
with col5:
    if st.button("Refresh"):
        st.cache_data.clear()
        st.rerun()

st.divider()


def usage_to_color(rate):
    if rate >= 0.80:
        return [229, 57, 53, 200]
    elif rate >= 0.60:
        return [251, 140, 0, 200]
    else:
        return [67, 160, 71, 200]


# Prepare map data
df_map = df[
    (df["latitude"].notna())
    & (df["longitude"].notna())
    & (df["source"] == "ntpc")
].copy()

# Determine map center and zoom
if user_lat and user_lng:
    map_lat, map_lng, map_zoom = user_lat, user_lng, 14
    location_status = f"Centered on your location ({user_lat:.4f}, {user_lng:.4f})"
else:
    map_lat, map_lng, map_zoom = 25.02, 121.47, 11
    location_status = "Showing full area — allow location access to center on you"

col_map, col_stats = st.columns([5, 3])

with col_map:
    st.subheader("Parking Map")
    st.caption(location_status)

    if not df_map.empty:
        df_map["color"] = df_map["usage_rate"].apply(usage_to_color)
        df_map["occupancy_pct"] = (df_map["usage_rate"] * 100).round(1).astype(str) + "%"

        layers = [
            pdk.Layer(
                "ScatterplotLayer",
                data=df_map,
                get_position=["longitude", "latitude"],
                get_color="color",
                get_radius=50,
                pickable=True,
            ),
        ]

        # Add user location marker
        if user_lat and user_lng:
            user_point = pd.DataFrame([{
                "latitude": user_lat, "longitude": user_lng, "label": "You",
            }])
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                data=user_point,
                get_position=["longitude", "latitude"],
                get_color=[0, 120, 255, 220],
                get_radius=120,
                pickable=True,
            ))

        view = pdk.ViewState(latitude=map_lat, longitude=map_lng, zoom=map_zoom, pitch=0)
        st.pydeck_chart(
            pdk.Deck(
                layers=layers,
                initial_view_state=view,
                tooltip={"text": "{road_name}\nOccupancy: {occupancy_pct}"},
                map_style="light",
            )
        )
    else:
        st.info("No coordinate data available for map display.")

    st.caption("🔵 You　🔴 ≥80%　🟠 ≥60%　🟢 <60%")

with col_stats:
    # If we have user location, show nearby spots first
    if user_lat and user_lng and not df_map.empty:
        st.subheader("Nearby Parking")
        df_nearby = df_map.copy()
        df_nearby["distance_km"] = df_nearby.apply(
            lambda r: haversine_km(user_lat, user_lng, r["latitude"], r["longitude"]), axis=1
        )
        df_nearby = df_nearby.sort_values("distance_km")
        nearby = df_nearby[df_nearby["distance_km"] <= 3].head(10)

        if nearby.empty:
            st.info("No parking segments within 3 km.")
        else:
            for _, row in nearby.iterrows():
                rate = row["usage_rate"]
                color = "🔴" if rate >= 0.80 else "🟡" if rate >= 0.60 else "🟢"
                dist = row["distance_km"]
                dist_str = f"{dist * 1000:.0f}m" if dist < 1 else f"{dist:.1f}km"
                st.markdown(
                    f"{color} **{row['road_name']}** — {rate:.1%}  \n"
                    f"<small style='color:gray'>{dist_str} away · "
                    f"{int(row['available_spots'])} available / {int(row['total_spots'])} total</small>",
                    unsafe_allow_html=True,
                )

        with st.expander("All Districts"):
            district_stats = (
                df.groupby("district")
                .agg(avg_rate=("usage_rate", "mean"), available=("available_spots", "sum"), total=("total_spots", "sum"))
                .sort_values("avg_rate", ascending=False)
            )
            for district, row in district_stats.iterrows():
                rate = row["avg_rate"]
                color = "🔴" if rate >= 0.80 else "🟡" if rate >= 0.60 else "🟢"
                st.markdown(
                    f"{color} **{district}** — {rate:.1%}  \n"
                    f"<small style='color:gray'>{int(row['available'])} / {int(row['total'])} spots</small>",
                    unsafe_allow_html=True,
                )
    else:
        st.subheader("District Ranking")
        district_stats = (
            df.groupby("district")
            .agg(avg_rate=("usage_rate", "mean"), available=("available_spots", "sum"), total=("total_spots", "sum"))
            .sort_values("avg_rate", ascending=False)
        )
        for district, row in district_stats.iterrows():
            rate = row["avg_rate"]
            color = "🔴" if rate >= 0.80 else "🟡" if rate >= 0.60 else "🟢"
            st.markdown(
                f"{color} **{district}** — {rate:.1%}  \n"
                f"<small style='color:gray'>{int(row['available'])} / {int(row['total'])} spots</small>",
                unsafe_allow_html=True,
            )
