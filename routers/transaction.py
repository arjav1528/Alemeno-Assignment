from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from models.transaction import Transaction

router = APIRouter(prefix="/transactions")


@router.get("/")
async def get_transactions(db: Session = Depends(get_db)):
    try:
        transactions = db.query(Transaction).all()
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
