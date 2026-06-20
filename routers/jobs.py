import json

import pandas as pd
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from lib.anomaly import detect_anomalies
from lib.cleaning import clean_transactions
from lib.process import process_job
from models.job import Job, JobStatus, JobSummary
from models.transaction import Currency, Transaction, TxnStatus
from routers import transaction
from tasks import process_csv

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
        db.query(JobSummary).delete()
        db.commit()
        db.query(Transaction).delete()
        db.commit()
        db.query(Job).delete()
        db.commit()
        return {"message": "DB cleared successfully"}
    except Exception as e:
        db.rollback()
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
                {
                    "txn_id": t.txn_id,
                    "date": t.date,
                    "merchant": t.merchant,
                    "amount": t.amount,
                    "currency": t.currency,
                    "status": t.status,
                    "category": t.category,
                    "account_id": t.account_id,
                }
                for t in transactions
            ],
            "anomalies": [
                {
                    "txn_id": t.txn_id,
                    "amount": t.amount,
                    "merchant": t.merchant,
                    "reason": t.anomaly_reason,
                }
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
            }
            if summary
            else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch results: {str(e)}"
        )


@router.post("/upload")
def upload_job(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        csv_data = file.file.read().decode("utf-8")

        job = Job(filename=file.filename, row_count_raw=0)
        db.add(job)
        db.commit()
        db.refresh(job)

        process_csv.delay(job.id, csv_data)  # type: ignore

        return {"message": "Job enqueued successfully", "job_id": job.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
