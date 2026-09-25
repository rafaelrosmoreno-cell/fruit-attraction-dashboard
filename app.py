import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Fruit Attraction 2026",
    page_icon="🍊",
    layout="wide"
)

st.title("🍊 Fruit Attraction 2026")
st.caption("Personal Exhibitor Dashboard · IFEMA Madrid")

df = pd.read_csv("targets.csv")

# KPIs
col1, col2, col3 = st.columns(3)

col1.metric("Companies", len(df))
col2.metric(
    "High Priority",
    len(df[df["priority"] == "High"])
)
col3.metric(
    "Categories",
    df["category"].nunique()
)

st.divider()

# Filters
col1, col2 = st.columns(2)

priority = col1.multiselect(
    "Priority",
    options=df["priority"].unique(),
    default=df["priority"].unique()
)

category = col2.multiselect(
    "Category",
    options=df["category"].unique(),
    default=df["category"].unique()
)

filtered = df[
    (df["priority"].isin(priority))
    & (df["category"].isin(category))
]

st.subheader("🎯 Target Companies")

st.dataframe(
    filtered,
    use_container_width=True,
    hide_index=True
)
