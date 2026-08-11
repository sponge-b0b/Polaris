from sqlalchemy import CheckConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class GovernedExecutionEvidenceSelectionModel(Base):
    """Durable execution-scoped selection for governed evidence."""

    __tablename__ = "governed_execution_evidence_selections"
    __table_args__ = (
        CheckConstraint(
            "risk_tier IN ('baseline', 'enhanced', 'vigilant')",
            name="ck_governed_execution_evidence_selection_risk_tier",
        ),
    )

    execution_id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_name: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_version: Mapped[str] = mapped_column(String, primary_key=True)
    risk_tier: Mapped[str] = mapped_column(String, nullable=False)
    evidence_id: Mapped[str] = mapped_column(String, nullable=False)


Index(
    "idx_governed_execution_evidence_selection_evidence",
    GovernedExecutionEvidenceSelectionModel.evidence_id,
)
