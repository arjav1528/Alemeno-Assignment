import json

from fastapi.exceptions import HTTPException
import pandas as pd
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from db.database import get_db
from lib.anomaly import detect_anomalies
from lib.cleaning import clean_transactions
from lib.process import process_job
from models.job import Job, JobStatus, JobSummary
from models.transaction import Currency, Transaction, TxnStatus

router = APIRouter(prefix="/jobs")


@router.get("/")
def read_jobs(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    return query.all()

@router.delete("/")
def delete_job(db: Session = Depends(get_db)):
    try:
        jobs = db.query(Job).all()
        for job in jobs:
            db.delete(job)
            db.commit()
        return {"message": "Jobs deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/status")
def read_job_status(job_id: int, db: Session = Depends(get_db)):
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            return {"status": job.status}
        raise HTTPException(status_code=404, detail="Job not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/{job_id}/results")
def get_job_results(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == JobStatus.PENDING:
        raise HTTPException(status_code=202, detail="Job is still processing")

    if job.status == JobStatus.FAILED:
        raise HTTPException(status_code=500, detail=f"Job failed: {job.error_message}")

    try:
        transactions = db.query(Transaction).filter(Transaction.job_id == job_id).all()
        anomalies = [t for t in transactions if t.is_anomaly]
        summary = db.query(JobSummary).filter(JobSummary.job_id == job_id).first()

        category_spend = {}
        for t in transactions:
            cat = t.category or "Uncategorised"
            category_spend[cat] = category_spend.get(cat, 0) + t.amount

        return {
            "job": {"id": job.id, "status": job.status, "filename": job.filename},
            "transactions": [
                {"txn_id": t.txn_id, "date": t.date, "merchant": t.merchant,
                 "amount": t.amount, "currency": t.currency, "status": t.status,
                 "category": t.category, "account_id": t.account_id}
                for t in transactions
            ],
            "anomalies": [
                {"txn_id": t.txn_id, "amount": t.amount, "merchant": t.merchant,
                 "reason": t.anomaly_reason}
                for t in anomalies
            ],
            "category_breakdown": category_spend,
            "summary": {
                "total_spend_inr": summary.total_spend_inr,
                "total_spend_usd": summary.total_spend_usd,
                "top_merchants": json.loads(summary.top_merchants),
                "anomaly_count": summary.anomaly_count,
                "narrative": summary.narrative,
                "risk_level": summary.risk_level,
            } if summary else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch results: {str(e)}")


@router.post("/upload")
def upload_job(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        df = pd.read_csv(
            file.file,
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
        filename = file.filename
        job = Job(
            row_count_raw=row_count_raw,
            row_count_clean=row_count_clean,
            filename=filename,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

    except Exception as e:
        db.rollback()
        return {
            "message": "Failed to upload job",
            "error": str(e),
        }

    df = detect_anomalies(df)

    try:
        for row in df.to_dict(orient="records"):
            currency_value = str(row.get("currency")).upper()
            status_value = str(row.get("status")).upper()
            transaction = Transaction(
                job_id=job.id,
                txn_id=row.get("txn_id"),
                date=row.get("date"),
                merchant=row.get("merchant"),
                amount=float(row["amount"]),
                currency=Currency[currency_value],
                status=TxnStatus[status_value],
                category=row.get("category"),
                account_id=row.get("account_id"),
                is_anomaly=bool(row.get("is_anomaly", False)),
                anomaly_reason=row.get("anomaly_reason"),
                notes=row.get("notes"),
            )
            db.add(transaction)

        db.commit()
        process_job(job, df, db)

        return {"message": "Job uploaded successfully", "job_id": job.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
