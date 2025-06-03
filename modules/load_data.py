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
    conn.close()

    overrides_df.rename(columns={"client_id": "Client ID"}, inplace=True)

    # Merge override if any
    if not overrides_df.empty:
        people.drop(columns=["LLM_Industry"], inplace=True, errors="ignore")
        people = people.merge(overrides_df, on="Client ID", how="left")
        # Use override if available, else fallback to auto-assigned
        people["LLM_Industry"] = people["overridden_industry"].fillna(
            people["LLM_Industry"]
        )
        people.drop(columns=["overridden_industry"], inplace=True, errors="ignore")

    return df


def save_people(df, path="data/updated_people.xlsx"):
    with pd.ExcelWriter(path, engine="openpyxl", mode="w") as writer:
        df.to_excel(writer, sheet_name="People", index=False)


def load_companies(path="data/companies_geocoded.csv"):
    com_df = pd.read_csv(path)
    com_df = com_df.rename(columns={"Revenue (in Millions)": "Revenue"})

    return com_df
