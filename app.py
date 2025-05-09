# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from modules.load_data import load_people, load_companies


st.set_page_config(layout="wide")

# Load data
people = load_people()
companies = load_companies()

# Ensure 'Status' column exists, default to "open"
# if "Status" not in people.columns:
#     people["Status"] = "open"
# else:
#     people["Status"] = people["Status"].fillna("open")

st.title("CRM - Clients Dashboard")

# Filters
st.sidebar.header("Filters")
industry = st.sidebar.selectbox(
    "LLM Industry", ["All"] + sorted(people["LLM_Industry"].dropna().unique().tolist())
)
status = st.sidebar.multiselect(
    "Status", people["Status"].unique(), default=people["Status"].unique()
)

# Apply filters
filtered = people.copy()
if industry != "All":
    filtered = filtered[filtered["LLM_Industry"] == industry]
if status:
    filtered = filtered[filtered["Status"].isin(status)]

# Metrics
st.metric("Total Clients", len(filtered))
st.metric("Unique Companies", filtered["Company"].nunique())

# Charts
personnel_counts = filtered["Company"].value_counts().reset_index()
personnel_counts.columns = ["Company", "Count"]
fig = px.bar(
    personnel_counts,
    x="Count",
    y="Company",
    orientation="h",
    title="Personnel per Company",
)
st.plotly_chart(fig, use_container_width=True)

# Table
st.subheader("Client List")
st.dataframe(filtered, use_container_width=True)
