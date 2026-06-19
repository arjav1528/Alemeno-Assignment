
import pandas as pd

DOMESTIC_MERCHANTS = {"Swiggy", "Ola", "IRCTC", "Zomato", "Jio Recharge", "Flipkart"}

def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    df["is_anomaly"] = False
    df["anomaly_reason"] = None

    medians = df.groupby("account_id")["amount"].median()

    for idx, row in df.iterrows():
        reasons = []
        median = medians[row["account_id"]]
        if row["amount"] > 3 * median:
            reasons.append(f"Amount {row['amount']} exceeds 3x account median ({median:.2f})")
        if row["currency"] == "USD" and row["merchant"] in DOMESTIC_MERCHANTS:
            reasons.append(f"USD with domestic merchant {row['merchant']}")
        if reasons:
            df.at[idx, "is_anomaly"] = True
            df.at[idx, "anomaly_reason"] = "; ".join(reasons)

    return df