from io import StringIO

import numpy as np
import pandas as pd


def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:

    df = df.drop_duplicates()
    # print(f"There are {len(df)} transactions before cleaning.")

    def parse_date(d):
        if pd.isna(d):
            return None
        for fmt in ("%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"):
            try:
                return pd.to_datetime(d, format=fmt).strftime("%Y-%m-%d")
            except:
                continue

        return None

    df["date"] = df["date"].apply(parse_date)

    df["amount"] = (
        df["amount"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
        .astype(float)
    )
    df["status"] = df["status"].str.upper().str.strip()
    df["currency"] = df["currency"].str.upper().str.strip()

    df["category"] = df["category"].fillna("Uncategorised")
    df["category"] = df["category"].replace("", "Uncategorised")

    df["txn_id"] = df["txn_id"].where(df["txn_id"].notna(), None)
    df["notes"] = df["notes"].where(df["notes"].notna(), None)

    df = df.dropna(
        subset=["amount", "currency", "status", "date", "merchant", "account_id"]
    )
    df = df.astype(object).where(pd.notna(df), None)

    return df
