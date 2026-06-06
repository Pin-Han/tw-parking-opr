import streamlit as st
import plotly.express as px
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dashboard.data_access import get_opr_data

st.set_page_config(page_title="OPR 分析", layout="wide")
st.title("OPR 統計分析")

days = st.slider("分析天數", min_value=3, max_value=90, value=14)


@st.cache_data(ttl=300)
def fetch_opr(endpoint, params=None):
    return get_opr_data(endpoint, params)


tab1, tab2, tab3 = st.tabs(["每日彙總", "時段模式", "週環比"])

with tab1:
    df, msg = fetch_opr("daily", {"days": days})
    if msg:
        st.warning(msg)
    elif not df.empty:
        fig = px.line(
            df, x="date", y="avg_usage", color="district",
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
            pattern_df["is_holiday"] = pattern_df["is_holiday"].map({0: "平日", 1: "假日"})
            fig = px.line(
                pattern_df, x="hour", y="usage_rate", color="is_holiday",
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
            wow_df, x="district", y="usage_rate", color="week",
            barmode="group", title="週環比使用率對比",
        )
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)
