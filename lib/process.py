import json
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from lib.llm import classify_transactions, generate_summary
from models.job import Job, JobStatus, JobSummary
from models.transaction import Transaction


def process_job(job: Job, df, db: Session):
    try:
        uncategorized = df[df["category"] == "Uncategorised"]
        if len(uncategorized) > 0:
            try:
                batch = [
                    {
                        "txn_id": r["txn_id"] or str(idx),
                        "merchant": r["merchant"],
                        "amount": r["amount"],
                    }
                    for idx, r in uncategorized.iterrows()
                ]
                classifications = classify_transactions(batch)
                for txn_id, category in classifications.items():
                    db.query(Transaction).filter(
                        Transaction.job_id == job.id, Transaction.txn_id == txn_id
                    ).update({"llm_category": category, "category": category})
                db.commit()
            except Exception as e:
                db.rollback()
                db.query(Transaction).filter(
                    Transaction.job_id == job.id,
                    Transaction.category == "Uncategorised",
                ).update({"llm_failed": True})
                db.commit()
                print(f"LLM classification failed: {e}")

        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        stats = {
            "total_spend_inr": float(df[df["currency"] == "INR"]["amount"].sum()),
            "total_spend_usd": float(df[df["currency"] == "USD"]["amount"].sum()),
            "top_merchants": df.groupby("merchant")["amount"]
            .sum()
            .nlargest(3)
            .index.tolist(),
            "anomaly_count": int(df["is_anomaly"].sum()),
            "total_transactions": len(df),
        }
        try:
            summary_data = generate_summary(stats)
            summary = JobSummary(
                job_id=job.id,
                total_spend_inr=summary_data["total_spend_inr"],
                total_spend_usd=summary_data["total_spend_usd"],
                top_merchants=json.dumps(summary_data["top_merchants"]),
                anomaly_count=summary_data["anomaly_count"],
                narrative=summary_data["narrative"],
                risk_level=summary_data["risk_level"],
            )
            db.add(summary)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"LLM summary failed: {e}")

        job.status = JobStatus.SUCCESS
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        db.rollback()
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.commit()
        print(f"Job processing failed: {e}")
