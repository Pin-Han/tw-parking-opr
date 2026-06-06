import streamlit as st

st.set_page_config(
    page_title="停車 OPR 分析平台",
    page_icon="🅿️",
    layout="wide",
)

st.title("停車 OPR 分析平台")
st.markdown("台北市 + 新北市路邊停車即時數據與營運績效分析")

st.markdown("""
### 功能頁面

- **即時地圖** — 新北市停車使用率地圖 + 全區統計
- **OPR 分析** — 每日彙總、時段模式、週環比
- **異常偵測** — 今日使用率異常路段警示

👈 從左側選單選擇頁面
""")
