from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, String, func,JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class WorkflowStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkflowStepStatus(str, Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[WorkflowStatus] = mapped_column(
        SqlEnum(WorkflowStatus),
        nullable=False,
        default=WorkflowStatus.CREATED,
    )

    input_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("files.id"),
        nullable=True,
        index=True,
    )

    config: Mapped[dict | None] = mapped_column(
    JSON,
    nullable=True,
    ) 

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    steps: Mapped[list["WorkflowStep"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
    )
    


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("workflows.id"),
        nullable=False,
        index=True,
    )

    job_id: Mapped[int | None] = mapped_column(
        ForeignKey("jobs.id"),
        nullable=True,
        index=True,
    )

    step_name: Mapped[str] = mapped_column(String(100), nullable=False)

    step_order: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[WorkflowStepStatus] = mapped_column(
        SqlEnum(WorkflowStepStatus),
        nullable=False,
        default=WorkflowStepStatus.PENDING,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workflow: Mapped[Workflow] = relationship(
        back_populates="steps",
    )