"""Canonical presentation and external-sink application contracts."""

from application.presentation.governed_result import (
    GovernedPresentationProjection,
    GovernedPresentationResult,
)
from application.presentation.sink_decision import (
    PresentationSinkDecision,
    PresentationSinkDecisionService,
    PresentationSinkDisposition,
)

__all__ = [
    "GovernedPresentationProjection",
    "GovernedPresentationResult",
    "PresentationSinkDecision",
    "PresentationSinkDecisionService",
    "PresentationSinkDisposition",
]
