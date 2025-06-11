import pandas as pd
import os
import sqlite3


def load_people(path="data/people_industry.csv"):
    updated_path = "data/updated_people.xlsx"

    if os.path.exists(updated_path):
        df = pd.read_excel(updated_path, sheet_name="People")
    else:
        df = pd.read_csv(path)

    # Ensure 'Status' column exists, default to "open"
    if "Status" not in df.columns:
        df["Status"] = "open"
    else:
        df["Status"] = df["Status"].fillna("open")

    # Create a unique identifier per person
    df["Client ID"] = df["Name"].str.strip() + " @ " + df["Company"].str.strip()
    df = df.drop_duplicates(subset="Client ID", keep="first")

    conn = sqlite3.connect("crm.db")

    overrides_df = pd.read_sql_query("SELECT * FROM industry_overrides", conn)

    # --- Load status + last contacted ---
    status_df = pd.read_sql("SELECT * FROM client_status", conn)
    status_df.rename(
        columns={
            "client_id": "Client ID",
            "status": "Client Status",
            "last_contacted": "Last Contacted",
        },
        inplace=True,
    )
    status_df["Client ID"] = status_df["Client ID"].astype(str)

    # --- Load call logs ---
    logs_df = pd.read_sql_query("SELECT * FROM logs", conn)
    logs_df.rename(
        columns={
            "client_id": "Client ID",
            "note": "Call Note",
            "timestamp": "Call Timestamp",
        },
        inplace=True,
    )
    logs_df["Client ID"] = logs_df["Client ID"].astype(str)

    conn.close()

    overrides_df.rename(columns={"client_id": "Client ID"}, inplace=True)

    # Merge override if any
    if not overrides_df.empty:
        df = df.merge(overrides_df, on="Client ID", how="left")
        # Use override if available, else fallback to auto-assigned
        df["LLM_Industry"] = df["overridden_industry"].combine_first(df["LLM_Industry"])
        df.drop(columns=["overridden_industry"], inplace=True, errors="ignore")

    # --- Merge in status ---
    if not status_df.empty:
        df = df.merge(status_df, on="Client ID", how="left")
        df["Status"] = df["Client Status"].combine_first(df["Status"])
        df.drop(columns=["Client Status"], inplace=True, errors="ignore")
    # --- Merge in latest contact date from logs (optional alternative to status table) ---
    if not logs_df.empty:
        latest_contact = (
            logs_df.groupby("Client ID")["Call Timestamp"]
            .max()
            .reset_index()
            .rename(columns={"Call Timestamp": "Latest Contacted"})
        )
        df = df.merge(latest_contact, on="Client ID", how="left")

    return df, logs_df


df, logs = load_people()  # .columns


def save_people(df, path="data/updated_people.xlsx"):
    with pd.ExcelWriter(path, engine="openpyxl", mode="w") as writer:
        df.to_excel(writer, sheet_name="People", index=False)


def load_companies(path="data/companies_geocoded.csv"):
    com_df = pd.read_csv(path)
    com_df = com_df.rename(columns={"Revenue (in Millions)": "Revenue"})

    return com_df
