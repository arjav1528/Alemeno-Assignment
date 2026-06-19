import pandas as pd
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from db.database import get_db
from lib.anomaly import detect_anomalies
from lib.cleaning import clean_transactions
from models.job import Job
from models.transaction import Currency, Transaction, TxnStatus

router = APIRouter(prefix="/jobs")


@router.get("/")
def read_jobs(db: Session = Depends(get_db)):
    try:
        jobs = db.query(Job).all()
        return jobs
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()


@router.delete("/")
def delete_job(db: Session = Depends(get_db)):
    try:
        jobs = db.query(Job).all()
        for job in jobs:
            db.delete(job)
            db.commit()
        return {"message": "Jobs deleted successfully"}
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()


@router.get("/{job_id}/status")
def read_job_status(job_id: int, db: Session = Depends(get_db)):
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            return {"status": job.status}
        return {"error": "Job not found"}
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()


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

        return {"message": "Job uploaded successfully", "job_id": job.id}
    except Exception as e:
        db.rollback()
        return {
            "message": "Failed to add transactions",
            "error": str(e),
        }
    finally:
        db.close()
