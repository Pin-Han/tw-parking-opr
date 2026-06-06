import streamlit as st
import pydeck as pdk
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dashboard.data_access import get_realtime_df

st.set_page_config(page_title="Live Parking Map", layout="wide")
st.title("Live Parking Occupancy")
st.caption("Real-time street parking data from Taipei and New Taipei City government APIs, refreshed every 2 minutes.")


@st.cache_data(ttl=120)
def load_realtime():
    return get_realtime_df()


df = load_realtime()

if df.empty:
    st.warning("Unable to fetch real-time data. Please check if the API is running.")
    st.stop()

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


col_map, col_stats = st.columns([5, 3])

with col_map:
    st.subheader("New Taipei City Map")
    df_map = df[
        (df["latitude"].notna())
        & (df["longitude"].notna())
        & (df["source"] == "ntpc")
    ].copy()

    if not df_map.empty:
        df_map["color"] = df_map["usage_rate"].apply(usage_to_color)
        df_map["occupancy_pct"] = (df_map["usage_rate"] * 100).round(1).astype(str) + "%"
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
                tooltip={"text": "{road_name}\nOccupancy: {occupancy_pct}"},
                map_style="light",
            )
        )
    else:
        st.info("No coordinate data available for map display.")

    st.caption("🔴 ≥80%　🟠 ≥60%　🟢 <60%")

with col_stats:
    st.subheader("District Ranking")

    district_stats = (
        df.groupby("district")
        .agg(
            avg_rate=("usage_rate", "mean"),
            total=("total_spots", "sum"),
            available=("available_spots", "sum"),
            segments=("road_id", "count"),
        )
        .sort_values("avg_rate", ascending=False)
    )

    for district, row in district_stats.iterrows():
        rate = row["avg_rate"]
        if rate >= 0.80:
            color = "🔴"
        elif rate >= 0.60:
            color = "🟡"
        else:
            color = "🟢"
        st.markdown(
            f"{color} **{district}** — {rate:.1%}  \n"
            f"<small style='color:gray'>{int(row['available'])} available / {int(row['total'])} total spots</small>",
            unsafe_allow_html=True,
        )
