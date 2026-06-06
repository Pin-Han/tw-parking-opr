import streamlit as st
import plotly.express as px
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dashboard.data_access import get_opr_data

st.set_page_config(page_title="OPR Analysis", layout="wide")
st.title("OPR Analysis")

days = st.slider("Analysis Period (days)", min_value=3, max_value=90, value=14)


@st.cache_data(ttl=300)
def fetch_opr(endpoint, params=None):
    return get_opr_data(endpoint, params)


tab1, tab2, tab3 = st.tabs(["Daily Summary", "Hourly Pattern", "Week-over-Week"])

with tab1:
    df, msg = fetch_opr("daily", {"days": days})
    if msg:
        st.warning(msg)
    elif not df.empty:
        # Ensure date is treated as string category, not datetime
        df["date"] = df["date"].astype(str)

        fig = px.line(
            df, x="date", y="avg_usage", color="district",
            title="Daily Average Occupancy Rate by District",
            labels={"avg_usage": "Occupancy Rate", "date": "Date", "district": "District"},
        )
        fig.update_yaxes(tickformat=".0%", range=[0, 1])
        fig.update_xaxes(type="category")
        st.plotly_chart(fig, use_container_width=True)

        # Format table for display
        display_df = df.rename(columns={
            "date": "Date",
            "district": "District",
            "avg_usage": "Avg Occupancy",
            "peak_usage": "Peak Occupancy",
            "min_usage": "Min Occupancy",
            "sample_count": "Samples",
        })
        for col in ["Avg Occupancy", "Peak Occupancy", "Min Occupancy"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"{x:.1%}")
        st.dataframe(
            display_df.sort_values(["Date", "Avg Occupancy"], ascending=[False, False]),
            use_container_width=True,
        )

with tab2:
    districts_df, _ = fetch_opr("daily", {"days": days})
    if not districts_df.empty:
        district_list = sorted(districts_df["district"].unique())
        district = st.selectbox("Select District", district_list)
        pattern_df, msg = fetch_opr("hourly", {"days": days, "district": district})
        if msg:
            st.warning(msg)
        elif not pattern_df.empty:
            pattern_df["is_holiday"] = pattern_df["is_holiday"].map({0: "Weekday", 1: "Holiday"})
            fig = px.line(
                pattern_df, x="hour", y="usage_rate", color="is_holiday",
                title=f"{district} — 24-Hour Occupancy Pattern",
                labels={"usage_rate": "Occupancy Rate", "hour": "Hour", "is_holiday": "Day Type"},
                color_discrete_map={"Weekday": "#1565c0", "Holiday": "#e53935"},
            )
            fig.update_yaxes(tickformat=".0%")
            fig.update_xaxes(dtick=1)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data available yet.")

with tab3:
    wow_df, msg = fetch_opr("wow", {"days": days})
    if msg:
        st.warning(msg)
    elif not wow_df.empty:
        wow_df["week"] = wow_df["week"].astype(str)
        fig = px.bar(
            wow_df, x="district", y="usage_rate", color="week",
            barmode="group", title="Week-over-Week Occupancy Comparison",
            labels={"usage_rate": "Occupancy Rate", "district": "District", "week": "Week"},
        )
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)
