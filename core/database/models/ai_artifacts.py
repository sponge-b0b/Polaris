from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from core.database.base import Base


class AiPromptProgramArtifactModel(Base):
    """Approved prompt/program artifact used by AI runtime and optimization flows."""

    __tablename__ = "ai_prompt_program_artifacts"
    __table_args__ = (
        UniqueConstraint(
            "artifact_name",
            "artifact_version",
            "target_component",
            name="uq_ai_prompt_program_artifacts_name_version_target",
        ),
        CheckConstraint(
            "artifact_type IN ("
            "'source_controlled_prompt', "
            "'langfuse_prompt', "
            "'dspy_program', "
            "'dspy_compiled_prompt'"
            ")",
            name="ck_ai_prompt_program_artifacts_type",
        ),
        CheckConstraint(
            "approval_status IN ('draft', 'approved', 'rejected', 'inactive')",
            name="ck_ai_prompt_program_artifacts_approval_status",
        ),
        CheckConstraint(
            "deepeval_score_summary IS NULL OR "
            "jsonb_typeof(deepeval_score_summary) = 'object'",
            name="ck_ai_prompt_program_artifacts_deepeval_summary_object",
        ),
        CheckConstraint(
            "approval_status != 'approved' OR "
            "(approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name="ck_ai_prompt_program_artifacts_approved_identity",
        ),
        CheckConstraint(
            "active = false OR approval_status = 'approved'",
            name="ck_ai_prompt_program_artifacts_active_requires_approved",
        ),
    )

    artifact_id: Mapped[str] = mapped_column(String, primary_key=True)
    artifact_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    artifact_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    artifact_version: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target_component: Mapped[str] = mapped_column(String, nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    provider_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    prompt_reference: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False, index=True)
    evaluation_dataset_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("evaluation_datasets.dataset_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    evaluation_run_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("evaluation_runs.run_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    deepeval_score_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    langfuse_trace_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    approval_status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="draft",
        index=True,
    )
    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_ai_prompt_program_artifacts_active_target",
    AiPromptProgramArtifactModel.target_component,
    AiPromptProgramArtifactModel.artifact_type,
    AiPromptProgramArtifactModel.active,
)
Index(
    "idx_ai_prompt_program_artifacts_evaluation",
    AiPromptProgramArtifactModel.evaluation_dataset_id,
    AiPromptProgramArtifactModel.evaluation_run_id,
)
