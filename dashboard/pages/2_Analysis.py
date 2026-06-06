import streamlit as st
import plotly.express as px
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dashboard.data_access import get_opr_data

st.set_page_config(page_title="Analysis", layout="wide")
st.title("Parking Analysis")
st.caption("Insights derived from parking snapshots collected every 30 minutes.")

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
        df["date"] = df["date"].astype(str)

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        district_avg = df.groupby("district")["avg_usage"].mean().sort_values(ascending=False)
        with col1:
            st.metric("Overall Avg Occupancy", f"{district_avg.mean():.1%}")
        with col2:
            st.metric("Busiest District", district_avg.index[0], f"{district_avg.iloc[0]:.1%}")
        with col3:
            st.metric("Quietest District", district_avg.index[-1], f"{district_avg.iloc[-1]:.1%}")
        with col4:
            st.metric("Days Analyzed", df["date"].nunique())

        st.divider()

        # District filter — default top 5
        default_top5 = list(district_avg.head(5).index)
        selected = st.multiselect(
            "Select districts to display",
            options=list(district_avg.index),
            default=default_top5,
        )

        if selected:
            filtered = df[df["district"].isin(selected)]
            fig = px.line(
                filtered, x="date", y="avg_usage", color="district",
                title="Daily Average Occupancy Rate",
                labels={"avg_usage": "Occupancy Rate", "date": "Date", "district": "District"},
            )
            fig.update_yaxes(tickformat=".0%", range=[0, 1])
            fig.update_xaxes(type="category")
            fig.update_layout(height=420, legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("View detailed data table"):
                display_df = filtered.rename(columns={
                    "date": "Date", "district": "District",
                    "avg_usage": "Avg Occupancy", "peak_usage": "Peak Occupancy",
                    "min_usage": "Min Occupancy", "sample_count": "Samples",
                })
                for col in ["Avg Occupancy", "Peak Occupancy", "Min Occupancy"]:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"{x:.1%}")
                st.dataframe(
                    display_df.sort_values(["Date", "Avg Occupancy"], ascending=[False, False]),
                    use_container_width=True, hide_index=True,
                )
        else:
            st.info("Select at least one district to see the chart.")

with tab2:
    districts_df, _ = fetch_opr("daily", {"days": days})
    if not districts_df.empty:
        district = st.selectbox("Select District", sorted(districts_df["district"].unique()))
        pattern_df, msg = fetch_opr("hourly", {"days": days, "district": district})
        if msg:
            st.warning(msg)
        elif not pattern_df.empty:
            pattern_df["is_holiday"] = pattern_df["is_holiday"].map({0: "Weekday", 1: "Holiday"})
            fig = px.line(
                pattern_df, x="hour", y="usage_rate", color="is_holiday",
                title=f"{district} — 24-Hour Occupancy Pattern",
                labels={"usage_rate": "Occupancy Rate", "hour": "Hour of Day", "is_holiday": "Day Type"},
                color_discrete_map={"Weekday": "#1565c0", "Holiday": "#e53935"},
            )
            fig.update_yaxes(tickformat=".0%", range=[0, 1])
            fig.update_xaxes(dtick=1, range=[-0.5, 23.5])
            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)

            # Key insights
            weekday = pattern_df[pattern_df["is_holiday"] == "Weekday"]
            if not weekday.empty:
                peak = weekday.loc[weekday["usage_rate"].idxmax()]
                off_peak = weekday.loc[weekday["usage_rate"].idxmin()]
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Weekday Peak Hour", f"{int(peak['hour'])}:00", f"{peak['usage_rate']:.1%}")
                with col2:
                    st.metric("Weekday Off-Peak Hour", f"{int(off_peak['hour'])}:00", f"{off_peak['usage_rate']:.1%}")
    else:
        st.warning("No data available yet.")

with tab3:
    wow_df, msg = fetch_opr("wow", {"days": days})
    if msg:
        st.warning(msg)
    elif not wow_df.empty:
        wow_df["week"] = "Week " + wow_df["week"].astype(str)
        # Top 8 districts for readability
        top8 = wow_df.groupby("district")["usage_rate"].mean().nlargest(8).index
        wow_filtered = wow_df[wow_df["district"].isin(top8)]
        fig = px.bar(
            wow_filtered, x="district", y="usage_rate", color="week",
            barmode="group", title="Week-over-Week Occupancy (Top 8 Districts)",
            labels={"usage_rate": "Occupancy Rate", "district": "District", "week": "Week"},
        )
        fig.update_yaxes(tickformat=".0%", range=[0, 1])
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)
