# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from modules.load_data import load_people, load_companies, save_people

import datetime

LOG_FILE = "logs.csv"


def load_logs():
    try:
        return pd.read_csv(LOG_FILE)
    except FileNotFoundError:
        return pd.DataFrame(
            columns=["Client ID", "Date", "Note"]
        )  # Manually add the columns as headers on the csv file


def save_log_entry(client_id, note, date):
    logs = load_logs()
    new_entry = {"Client ID": client_id, "Date": date, "Note": note}
    logs = pd.concat([logs, pd.DataFrame([new_entry])], ignore_index=True)
    logs.to_csv(LOG_FILE, index=False)


st.set_page_config(layout="wide")

# Load data
people = load_people()
companies = load_companies()


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
met1, met2, met3, met4 = st.columns(4)
with met1:
    st.metric("Filtered Clients", len(filtered))
with met2:
    st.metric("Unique Filtered Companies", filtered["Company"].nunique())
with met3:
    st.metric("Total Clients", len(people))
with met4:
    st.metric("Total Unique Companies", people["Company"].nunique())

# Simulate row selection with a selectbox to choose a client
st.subheader("Select a Client for Action")

if not filtered.empty:
    selected_client = st.selectbox(
        "Choose client", options=filtered["Client ID"].unique()
    )

    client_row = filtered[filtered["Client ID"] == selected_client].iloc[0]

    # Two-column layout for client details
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**Company:** {client_row['Company']}")
        st.markdown(f"**Job Title:** {client_row['Title']}")

    with col2:
        st.markdown(f"**Current Status:** {client_row['Status']}")
        st.markdown(f"**Current LLM Industry:** {client_row['LLM_Industry']}")

# Action buttons
# st.subheader("Actions")

# # Update Status
# status_options = [
#     "open",
#     "contacted",
#     "engaged",
#     "negotiation",
#     "won",
#     "lost",
#     "on hold",
# ]
# new_status = st.selectbox("Update Status", status_options)

# # if st.button("Confirm Status Update"):
# #     people.loc[people["Client ID"] == selected_client, "Status"] = new_status
# #     save_people(people)  # Save after status update
# #     st.success(f"Status updated to **{new_status}** for {selected_client}.")

# # Override LLM Industry
# new_industry = st.text_input("Correct LLM Industry")

# # if st.button("Confirm Industry Update") and new_industry:
# #     people.loc[people["Client ID"] == selected_client, "LLM_Industry"] = new_industry
# #     save_people(people)  # Save after industry update
# #     st.success(f"LLM Industry updated to **{new_industry}** for {selected_client}.")

# col1, col2 = st.columns(2)

# with col1:
#     if st.button("Confirm Status Update"):
#         people.loc[people["Client ID"] == selected_client, "Status"] = new_status
#         save_people(people)
#         st.success(f"Status updated to **{new_status}** for {client_row['Client ID']}.")

# with col2:
#     if st.button("Confirm Industry Update") and new_industry:
#         people.loc[people["Client ID"] == selected_client, "LLM_Industry"] = (
#             new_industry
#         )
#         save_people(people)
#         st.success(
#             f"LLM Industry updated to **{new_industry}** for {client_row['Client ID']}."
#         )


st.subheader("Actions")

left_col, right_col = st.columns(2)

# 🪪 Status Update (Left Column)
with left_col:
    st.markdown("**Update Status**")
    status_options = [
        "open",
        "contacted",
        "engaged",
        "negotiation",
        "won",
        "lost",
        "on hold",
    ]
    new_status = st.selectbox("Select new status", status_options, key="status_select")
    if st.button("Confirm Status Update", key="status_button"):
        people.loc[people["Client ID"] == selected_client, "Status"] = new_status
        save_people(people)
        st.success(
            f"✅ Status updated to **{new_status}** for {client_row['Client ID']}."
        )

# 🏷️ Industry Override (Right Column)
with right_col:
    st.markdown("**Review/Override Industry**")
    new_industry = st.text_input("Enter correct industry", key="industry_input")
    if st.button("Confirm Industry Update", key="industry_button") and new_industry:
        people.loc[people["Client ID"] == selected_client, "LLM_Industry"] = (
            new_industry
        )
        save_people(people)
        st.success(
            f"✅ Industry updated to **{new_industry}** for {client_row['Client ID']}."
        )


st.subheader("📞 Log Call / Note")

note = st.text_area("Add a note or call summary")
note_date = st.date_input("Date of contact", value=datetime.date.today())

if st.button("Save Note"):
    if note.strip():
        save_log_entry(selected_client, note, note_date)
        st.success("Note logged successfully!")
    else:
        st.warning("Please write a note before saving.")


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
