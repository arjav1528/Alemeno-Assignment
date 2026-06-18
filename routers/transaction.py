from fastapi import APIRouter, Depends
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
        return {"error": str(e)}
    finally:
        db.close()


@router.delete("/")
async def delete_transaction(db: Session = Depends(get_db)):
    try:
        db.query(Transaction).delete()
        db.commit()
        return {"message": "Transactions deleted successfully"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()
