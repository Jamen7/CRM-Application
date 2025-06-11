# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from modules.load_data import load_people, load_companies, save_people
import sqlite3

# from datetime import datetime

from datetime import datetime

st.info("App reloaded successfully at: " + str(datetime.now()))

LOG_FILE = "logs.csv"


def init_db():
    conn = sqlite3.connect("crm.db")
    cursor = conn.cursor()

    # Table to store client status and last contacted date
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS client_status (
        client_id TEXT PRIMARY KEY,
        status TEXT DEFAULT 'open',
        last_contacted TEXT
    )
    """
    )

    # Table to store log notes
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT,
        note TEXT,
        timestamp TEXT
    )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS industry_overrides (
            client_id TEXT PRIMARY KEY,
            overridden_industry TEXT
        )
    """
    )

    conn.commit()
    conn.close()


init_db()


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


def get_recent_contact_metrics(filtered_client_ids, days=7):
    logs = load_logs()
    if logs.empty or not filtered_client_ids:
        return 0

    # Convert to datetime
    logs["Date"] = pd.to_datetime(logs["Date"], errors="coerce")

    # Filter logs to only relevant client IDs
    logs = logs[logs["Client ID"].isin(filtered_client_ids)]

    # Get latest contact date per client
    latest_contact = logs.groupby("Client ID")["Date"].max().reset_index()

    # Filter based on recent days
    cutoff = pd.Timestamp.today() - pd.Timedelta(days=days)
    recent_contacts = latest_contact[latest_contact["Date"] >= cutoff]

    return len(recent_contacts)


def get_latest_contact_dates():
    logs = load_logs()
    if logs.empty:
        return pd.DataFrame(columns=["Client ID", "Last Contacted"])

    logs["Date"] = pd.to_datetime(logs["Date"], errors="coerce")
    latest = logs.groupby("Client ID")["Date"].max().reset_index()
    latest.rename(columns={"Date": "Last Contacted"}, inplace=True)
    return latest


def update_status(client_id, new_status):
    conn = sqlite3.connect("crm.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO client_status (client_id, status)
        VALUES (?, ?)
        ON CONFLICT(client_id) DO UPDATE SET status=excluded.status
    """,
        (client_id, new_status),
    )
    conn.commit()
    conn.close()


def log_call(client_id, note):
    conn = sqlite3.connect("crm.db")
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        "INSERT INTO logs (client_id, note, timestamp) VALUES (?, ?, ?)",
        (client_id, note, timestamp),
    )

    cursor.execute(
        """
        INSERT INTO client_status (client_id, last_contacted)
        VALUES (?, ?)
        ON CONFLICT(client_id) DO UPDATE SET last_contacted=excluded.last_contacted
    """,
        (client_id, timestamp),
    )

    conn.commit()
    conn.close()


def get_status_and_logs():
    conn = sqlite3.connect("crm.db")
    status_df = pd.read_sql_query("SELECT * FROM client_status", conn)
    logs_df = pd.read_sql_query("SELECT * FROM logs", conn)
    conn.close()

    # Rename columns to prevent conflict
    status_df.rename(
        columns={
            "status": "Status",
            "last_contacted": "Last Contacted",
            "client_id": "Client ID",
        },
        inplace=True,
    )

    # logs_df.rename(
    #     columns={"note": "Call Note", "timestamp": "Call Timestamp"}, inplace=True
    # )

    return status_df, logs_df


def show_companies_tab(companies):
    st.title("🏢 Companies")

    # Sidebar or top-level filters
    industries = sorted(companies["Industry"].dropna().unique())
    selected_industries = st.multiselect(
        "Filter by Industry", industries, default=industries
    )

    keyword = st.text_input("Search by keyword (e.g. name)")

    min_rev, max_rev = companies["Revenue"].min(), companies["Revenue"].max()
    revenue_range = st.slider(
        "Filter by Revenue",
        min_value=float(min_rev),
        max_value=float(max_rev),
        value=(float(min_rev), float(max_rev)),
    )

    # Apply filters
    filtered_df = companies[
        companies["Industry"].isin(selected_industries)
        & companies["Revenue"].between(revenue_range[0], revenue_range[1])
    ]

    if keyword:
        filtered_df = filtered_df[
            companies["Company Name"].str.contains(keyword, case=False)
            | companies["Address"].str.contains(keyword, case=False)
        ]

    # selected_industry = st.selectbox(
    #     "Filter companies on map by industry", companies["Industry"].unique()
    # )

    # map_df = companies[companies["Industry"] == selected_industry]

    # KPI cards
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🏢 Companies", len(filtered_df))
    with col2:
        st.metric("💰 Total Revenue", f"${filtered_df['Revenue'].sum():,.0f}")

    # Placeholder for Map (e.g. using lat/lon)
    # if "Latitude" in filtered_df and "Longitude" in filtered_df:
    #     map_df = filtered_df.dropna(subset=["Latitude", "Longitude"])
    #     st.map(map_df.rename(columns={"Latitude": "lat", "Longitude": "lon"}))

    st.subheader("📍 Company Locations")
    map_df = filtered_df.dropna(subset=["Latitude", "Longitude"])

    fig1 = px.scatter_mapbox(
        map_df,
        lat="Latitude",
        lon="Longitude",
        hover_name="Company Name",
        hover_data={
            "Industry": True,
            "Revenue": ":,.2f",
            "Address": True,
            "Latitude": False,  # Hide lat
            "Longitude": False,
        },
        color="Industry",
        size_max=10,
        zoom=1,
        height=500,
    )

    fig1.update_layout(
        mapbox_style="open-street-map", margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )

    st.plotly_chart(fig1, use_container_width=True)

    # Revenue by industry
    st.subheader("Revenue by Industry")
    rev_by_industry = (
        filtered_df.groupby("Industry")["Revenue"]
        .sum()
        .reset_index()
        .sort_values(by="Revenue", ascending=False)
    )
    fig = px.bar(
        rev_by_industry, x="Industry", y="Revenue", title="Revenue by Industry"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Company list
    st.subheader("Company List")
    st.dataframe(filtered_df)

    # Optional: expand for company details


def show_clients_tab(people):

    if st.button("🔄 Refresh"):
        st.experimental_rerun()

    col_title, col_metric1, col_metric2 = st.columns([4, 1, 1])

    with col_title:
        st.title("CRM - Clients Dashboard")

    with col_metric1:
        st.metric("Total Clients", len(people))

    with col_metric2:
        st.metric("Total Unique Companies", people["Company"].nunique())

    # Filters
    st.sidebar.header("Filters")
    industry = st.sidebar.selectbox(
        "LLM Industry",
        ["All"] + sorted(people["LLM_Industry"].dropna().unique().tolist()),
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
    met1, met2 = st.columns(2)
    with met1:
        st.metric("\U0001f9d1\u200d\U0001f4bc Filtered Clients", len(filtered))
    with met2:
        st.metric("\U0001f3e2 Unique Filtered Companies", filtered["Company"].nunique())

    filtered_client_ids = filtered["Client ID"].unique().tolist()
    met5, met6 = st.columns(2)

    with met5:
        st.metric(
            "👥 Contacted in last 7 days",
            get_recent_contact_metrics(filtered_client_ids, 7),
        )

    with met6:
        st.metric(
            "📆 Contacted in last 30 days",
            get_recent_contact_metrics(filtered_client_ids, 30),
        )

    # Simulate row selection with a selectbox to choose a client
    # st.subheader("\U0001f9d1\u200d\U0001f4bc Select a Client for Action")

    # if not filtered.empty:
    #     selected_client = st.selectbox(
    #         "Choose client", options=filtered["Client ID"].unique()
    #     )

    #     client_row = filtered[filtered["Client ID"] == selected_client].iloc[0]

    #     # Two-column layout for client details
    #     col1, col2 = st.columns(2)

    #     with col1:
    #         st.markdown(f"**Company:** {client_row['Company']}")
    #         st.markdown(f"**Job Title:** {client_row['Title']}")
    #         st.markdown(
    #             f"**Total Industry Revenue:** {client_row['Total Industry Revenue']}"
    #         )

    #     with col2:
    #         st.markdown(f"**Current Status:** {client_row['Status']}")
    #         st.markdown(f"**Current LLM Industry:** {client_row['LLM_Industry']}")
    #         st.markdown(f"**Last Contated Date:** {client_row['Last Contacted']}")

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

    st.subheader("🛠️ Select a Client for Action")
    selected_client = st.selectbox(
        "\U0001f9d1\u200d\U0001f4bc Choose a client:",
        options=filtered["Client ID"].unique(),
    )

    if selected_client:
        person_info = filtered[filtered["Client ID"] == selected_client].iloc[0]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**Name:** {person_info['Name']}")
            st.markdown(f"**Company:** {person_info['Company']}")
            st.markdown(f"**Job Title:** {person_info['Title']}")

        with col2:
            st.markdown(f"**Current Status:** {person_info.get('Status', 'open')}")
            st.markdown(f"**Current LLM Industry:** {person_info['LLM_Industry']}")
            st.markdown(
                f"**Total Industry Revenue:** {person_info['Total Industry Revenue']}"
            )
            st.markdown(
                f"**Last Contated Date:** {person_info.get('Last Contacted', 'N/A')}"
            )

        left_col, right_col = st.columns(2)

        # 🪪 Status Update (Left Column)
        with left_col:
            st.markdown("#### Update Status")
            status_options = [
                "open",
                "contacted",
                "engaged",
                "negotiation",
                "won",
                "lost",
                "on hold",
            ]
            new_status = st.selectbox("Select new status", status_options)
            if st.button("\U00002757 Update Status"):
                update_status(selected_client, new_status)
                st.success(f"Updated status to: {new_status}")

        # 🏷️ Industry Override (Right Column)
        with right_col:
            st.markdown("#### 🏭 Review/Override LLM Industry")
            new_industry = st.text_input("Enter correct industry", "")

            if st.button("💾 Save Industry Override"):
                if new_industry:
                    conn = sqlite3.connect("crm.db")
                    conn.execute(
                        "REPLACE INTO industry_overrides (client_id, overridden_industry) VALUES (?, ?)",
                        (selected_client, new_industry),
                    )
                    conn.commit()
                    conn.close()
                    st.success("Industry updated!")

        # st.write("Selected client:", selected_client)

        # st.markdown("**Review/Override Industry**")
        # new_industry = st.text_input("Enter correct industry", key="industry_input")
        # if (
        #     st.button("\U00002705 Confirm Industry Update", key="industry_button")
        #     and new_industry
        # ):
        #     people.loc[people["Client ID"] == selected_client, "LLM_Industry"] = (
        #         new_industry
        #     )
        #     save_people(people)
        #     st.success(
        #         f"✅ Industry updated to **{new_industry}** for {client_row['Client ID']}."
        #     )

    # --- Log Note ---
    with st.expander("📝 Log a Call/Note"):
        note = st.text_area("Add a note", height=100)
        if st.button("📌 Save Note"):
            if note.strip():
                log_call(selected_client, note)
                st.success("Note logged and last contacted updated.")
            else:
                st.warning("Please enter a note before saving.")

    # --- Show log history ---
    st.markdown("### 📚 Communication History")
    history = logs_df[logs_df["client_id"] == selected_client]
    if not history.empty:
        st.dataframe(
            history.sort_values("timestamp", ascending=False), use_container_width=True
        )
    else:
        st.info("No interaction logs yet for this client.")

    # st.subheader("\U0001f6e0\U0000fe0f Actions")

    # st.subheader("📞 Log Call / Note")

    # note = st.text_area("Add a note or call summary")
    # note_date = st.date_input("Date of contact", value=datetime.date.today())

    # if st.button("Save Note"):
    #     if note.strip():
    #         save_log_entry(selected_client, note, note_date)
    #         st.success("Note logged successfully!")
    #     else:
    #         st.warning("Please write a note before saving.")

    # st.markdown("### 📋 Communication History")

    # logs = load_logs()
    # client_logs = logs[logs["Client ID"] == selected_client]

    # if client_logs.empty:
    #     st.info("No notes logged yet for this client.")
    # else:
    #     st.dataframe(client_logs.sort_values(by="Date", ascending=False))

    # with st.expander("📞 Log Call / Note"):
    #     note = st.text_area("Add a note or call summary")
    #     note_date = st.date_input("Date of contact", value=datetime.date.today())

    #     if st.button("Save Note"):
    #         if note.strip():
    #             save_log_entry(selected_client, note, note_date)
    #             st.success("Note logged successfully!")
    #         else:
    #             st.warning("Please write a note before saving.")

    # with st.expander("📋 Communication History"):
    #     logs = load_logs()
    #     if filtered.empty:
    #         st.warning("⚠️ No results match the current filter.")
    #     else:
    #         client_logs = logs[logs["Client ID"] == selected_client]

    #         if client_logs.empty:
    #             st.info("No notes logged yet for this client.")
    #         else:
    #             st.dataframe(client_logs.sort_values(by="Date", ascending=False))

    # Charts
    if filtered.empty:
        st.warning("⚠️ No results match the current filter.")
    else:
        status_counts = filtered["Status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]

    box1, box2 = st.columns(2)

    with box1:
        chart_type = st.selectbox(
            "📊 Select Chart Type for Client Status",
            options=["Bar Chart", "Donut Pie Chart"],
            index=0,
        )

    bar, lin = st.columns(2)

    if filtered.empty:
        st.warning("⚠️ No results match the current filter.")
    else:
        with bar:
            if chart_type == "Bar Chart":
                fig_bar = px.bar(
                    status_counts,
                    x="Count",
                    y="Status",
                    orientation="h",
                    color="Status",
                    text="Count",
                    color_discrete_sequence=px.colors.qualitative.Safe,
                    title="📊 Client Status Overview (Bar)",
                )
                fig_bar.update_layout(yaxis_title="", xaxis_title="Clients")
                st.plotly_chart(fig_bar, use_container_width=True)

            elif chart_type == "Donut Pie Chart":
                fig_pie = px.pie(
                    status_counts,
                    names="Status",
                    values="Count",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Safe,
                    title="🧭 Client Status Distribution (Donut)",
                )
                st.plotly_chart(fig_pie, use_container_width=True)

    # fig_status_pie = px.pie(
    #     status_counts,
    #     values="Count",
    #     names="Status",
    #     title="🧭 Client Status Distribution",
    #     hole=0.4,  # for donut style
    # )

    # st.plotly_chart(fig_status_pie, use_container_width=True)

    # Merge latest contact info
    latest_contacts_df = get_latest_contact_dates()
    # if filtered.empty:
    #     st.warning("⚠️ No results match the current filter.")
    # else:
    #     filtered = filtered.merge(latest_contacts_df, on="Client ID", how="left")
    #     trend_df = (
    #         filtered.dropna(subset=["Last Contacted"])
    #         .groupby([pd.Grouper(key="Last Contacted", freq="W-MON"), "Status"])
    #         .size()
    #         .reset_index(name="Count")
    #         .sort_values("Last Contacted")
    #     )
    #     with lin:
    #         fig_trend = px.line(
    #             trend_df,
    #             x="Last Contacted",
    #             y="Count",
    #             color="Status",
    #             markers=True,
    #             title="📅 Weekly Contacted Clients by Status",
    #         )

    #         fig_trend.update_layout(xaxis_title="Week", yaxis_title="Client Count")
    #         st.plotly_chart(fig_trend, use_container_width=True)

    if filtered.empty:
        st.warning("⚠️ No results match the current filter.")
    else:
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
    if filtered.empty:
        st.warning("⚠️ No results match the current filter.")
    else:
        st.dataframe(filtered, use_container_width=True)


st.set_page_config(layout="wide")

# Load data
people = load_people()
companies = load_companies()  # Your companies dataset

industry_revenue = companies.groupby("Industry")["Revenue"].sum().reset_index().round(2)
industry_revenue.rename(columns={"Revenue": "Total Industry Revenue"}, inplace=True)

if "Total Industry Revenue" not in people.columns:
    people = people.merge(
        industry_revenue, how="left", left_on="LLM_Industry", right_on="Industry"
    ).drop(columns=["Industry"])

if "Industry" in people.columns:
    people = people.drop(columns=["Industry"])

# people.columns

# Drop existing columns if present
for col in ["Status", "Last Contacted"]:
    if col in people.columns:
        people.drop(columns=col, inplace=True)


status_df, logs_df = get_status_and_logs()
people = people.merge(status_df, on="Client ID", how="left")

tab = st.sidebar.radio("Navigate", ["Clients", "Companies"])
# if tab == "Companies":
#     show_companies_tab()

# Clear and isolate page layout
st.markdown("---")
st.markdown("<style>body {overflow-x: hidden;}</style>", unsafe_allow_html=True)

if tab == "Clients":
    # st.markdown("## Clients")
    show_clients_tab(people)
    st.markdown("<div style='height:200px;'></div>", unsafe_allow_html=True)

elif tab == "Companies":
    # st.markdown("## Companies")
    show_companies_tab(companies)
    st.markdown("<div style='height:200px;'></div>", unsafe_allow_html=True)
