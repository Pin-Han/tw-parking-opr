import streamlit as st
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dashboard.data_access import get_anomalies as _get_anomalies

st.set_page_config(page_title="Anomaly Detection", layout="wide")
st.title("Anomaly Detection")

with st.expander("How does this work?", expanded=False):
    st.markdown("""
This page compares **today's parking occupancy** for each district and hour
against the **historical average** for the same district and hour over the past 14 days.

If today's value deviates more than a set number of standard deviations (σ) from
the historical mean, it is flagged as an anomaly.

**Example:** 大安區 typically has 82% occupancy at 2 PM (std dev 3%).
If today it suddenly jumps to 95%, that's `(95% - 82%) / 3% = +4.3σ` — far beyond
the 2σ threshold, so it gets flagged.

**What anomalies can mean:**
- **Unusually high** — nearby event, construction rerouting traffic, data spike
- **Unusually low** — road closure, parking meter maintenance, data outage

Adjust the σ threshold below: higher = only flag extreme deviations, lower = more sensitive.
""")

sigma = st.slider("Anomaly Threshold (σ)", min_value=1.0, max_value=4.0, value=2.0, step=0.5)


@st.cache_data(ttl=300)
def fetch_anomalies(sigma_val):
    return _get_anomalies(days=14, sigma=sigma_val)


anomalies, msg = fetch_anomalies(sigma)

if msg:
    st.warning(msg)
elif anomalies.empty:
    st.success("No anomalies detected today ✓")
else:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Anomalous Segments", len(anomalies))
    with col2:
        high = len(anomalies[anomalies["z_score"] > 0])
        st.metric("Above Average", high)
    with col3:
        low = len(anomalies[anomalies["z_score"] < 0])
        st.metric("Below Average", low)

    st.divider()

    for _, row in anomalies.iterrows():
        z = row["z_score"]
        direction = "above" if z > 0 else "below"
        if z > 0:
            st.error(
                f"**{row['district']} {row.get('road_name', '')}**\n\n"
                f"Current: {row['usage_rate']:.1%} — Historical avg: {row.get('hist_mean', 0):.1%}\n\n"
                f"`+{abs(z):.1f}σ` {direction} historical average"
            )
        else:
            st.warning(
                f"**{row['district']} {row.get('road_name', '')}**\n\n"
                f"Current: {row['usage_rate']:.1%} — Historical avg: {row.get('hist_mean', 0):.1%}\n\n"
                f"`-{abs(z):.1f}σ` {direction} historical average"
            )
