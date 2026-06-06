import streamlit as st

st.set_page_config(
    page_title="Parking OPR Analytics",
    page_icon="🅿️",
    layout="wide",
)

st.title("Parking OPR Analytics")
st.markdown("Real-time street parking usage & operational performance reports for Taipei + New Taipei City")

st.markdown("""
### Pages

- **Live Map** — Real-time parking occupancy map for New Taipei City + district rankings
- **OPR Analysis** — Daily summary, hourly patterns, week-over-week comparison
- **Anomaly Detection** — Alerts for districts deviating from historical usage patterns

👈 Select a page from the sidebar
""")
