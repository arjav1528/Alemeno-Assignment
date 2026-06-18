import enum

from sqlalchemy import Boolean, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class Currency(enum.Enum):
    USD = "USD"
    EUR = "EUR"
    INR = "INR"


class TxnStatus(enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    txn_id: Mapped[str | None] = mapped_column(String, nullable=True)
    date: Mapped[str] = mapped_column(String)
    merchant: Mapped[str] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, values_callable=lambda enum_cls: [item.value for item in enum_cls])
    )
    status: Mapped[TxnStatus] = mapped_column(
        Enum(TxnStatus, values_callable=lambda enum_cls: [item.value for item in enum_cls])
    )
    category: Mapped[str] = mapped_column(String)
    account_id: Mapped[str] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    anomaly_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_category: Mapped[str | None] = mapped_column(String, nullable=True)
    llm_failed: Mapped[bool] = mapped_column(Boolean, default=False)
