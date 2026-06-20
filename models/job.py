import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base



class JobStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"  # add this
    SUCCESS = "success"
    FAILED = "failed"

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        default=JobStatus.PENDING,
    )
    row_count_raw: Mapped[int] = mapped_column(Integer)
    row_count_clean: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, filename={self.filename}, status={self.status})>"
        


class JobSummary(Base):
    __tablename__ = "job_summaries"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    total_spend_inr: Mapped[float] = mapped_column(Float)
    total_spend_usd: Mapped[float] = mapped_column(Float)
    top_merchants: Mapped[str] = mapped_column(Text)  # store JSON as string
    anomaly_count: Mapped[int] = mapped_column(Integer)
    narrative: Mapped[str] = mapped_column(Text)
    risk_level: Mapped[str] = mapped_column(String)
