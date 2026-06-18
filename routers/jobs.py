from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from models.job import Job

router = APIRouter(prefix="/jobs")


@router.get("/")
def read_jobs(db: Session = Depends(get_db)):
    try:
        jobs = db.query(Job).all()
        return jobs
    except Exception as e:
        return {"error": str(e)}


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


@router.get("/{job_id}/status")
def read_job_status(job_id: int, db: Session = Depends(get_db)):
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            return {"status": job.status}
        return {"error": "Job not found"}
    except Exception as e:
        return {"error": str(e)}
