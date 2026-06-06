import streamlit as st
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dashboard.data_access import get_anomalies as _get_anomalies

st.set_page_config(page_title="異常偵測", layout="wide")
st.title("異常偵測")
st.caption("偵測今日使用率與歷史均值差異超過 2σ 的路段")

sigma = st.slider("異常門檻 (σ)", min_value=1.0, max_value=4.0, value=2.0, step=0.5)


@st.cache_data(ttl=300)
def fetch_anomalies(sigma_val):
    return _get_anomalies(days=14, sigma=sigma_val)


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
