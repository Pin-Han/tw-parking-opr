import streamlit as st
import pydeck as pdk
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dashboard.data_access import get_realtime_df

st.set_page_config(page_title="即時停車地圖", layout="wide")
st.title("即時停車使用率")


@st.cache_data(ttl=120)
def load_realtime():
    return get_realtime_df()


df = load_realtime()

if df.empty:
    st.warning("無法取得即時資料，請確認 API 是否啟動")
    st.stop()

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

col_map, col_stats = st.columns([2, 1])


def usage_to_color(rate):
    if rate >= 0.80:
        return [229, 57, 53, 200]
    elif rate >= 0.60:
        return [251, 140, 0, 200]
    else:
        return [67, 160, 71, 200]


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
