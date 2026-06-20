import io

import pandas as pd

from celery_app import celery
from db.database import SessionLocal
from lib.anomaly import detect_anomalies
from lib.cleaning import clean_transactions
from lib.process import process_job
from models.job import Job, JobStatus
from models.transaction import Currency, Transaction, TxnStatus


@celery.task(name="tasks.process_csv")
def process_csv(job_id: int, csv_data: str):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {"error": "Job not found"}

        job.status = JobStatus.PROCESSING
        db.commit()

        df = pd.read_csv(
            io.StringIO(csv_data),
            usecols=[
                "txn_id",
                "date",
                "merchant",
                "amount",
                "currency",
                "status",
                "category",
                "account_id",
                "notes",
            ],
        )

        row_count_raw = len(df)
        df = clean_transactions(df)
        row_count_clean = len(df)

        job.row_count_raw = row_count_raw
        job.row_count_clean = row_count_clean
        db.commit()

        df = detect_anomalies(df)

        for row in df.to_dict(orient="records"):
            transaction = Transaction(
                job_id=job.id,
                txn_id=row.get("txn_id"),
                date=row.get("date"),
                merchant=row.get("merchant"),
                amount=float(row["amount"]),
                currency=Currency[str(row.get("currency")).upper()],
                status=TxnStatus[str(row.get("status")).upper()],
                category=row.get("category"),
                account_id=row.get("account_id"),
                is_anomaly=bool(row.get("is_anomaly", False)),
                anomaly_reason=row.get("anomaly_reason"),
                notes=row.get("notes"),
            )
            db.add(transaction)
        db.commit()

        process_job(job, df, db)
        return {"job_id": job.id, "status": "completed"}

    except Exception as e:
        db.rollback()
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            db.commit()
        return {"error": str(e)}
    finally:
        db.close()
