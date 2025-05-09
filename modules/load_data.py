import pandas as pd


def load_people(path="data/crm_test_case_data.xlsx"):
    df = pd.read_csv("data/people_industry.csv")

    # Ensure 'Status' column exists, default to "open"
    if "Status" not in df.columns:
        df["Status"] = "open"
    else:
        df["Status"] = df["Status"].fillna("open")

    return df


def load_companies(path="data/crm_test_case_data.xlsx"):
    return pd.read_excel(path, sheet_name="Companies")
