from __future__ import annotations

import pytest

from interfaces.cli.output import render_workflow_output_bundle
from interfaces.cli.output.workflow_output_renderer import (
    render_workflow_output_bundle as render_generic_workflow_output_bundle,
)
from tests.unit.interfaces.cli.output.test_workflow_output_renderer import (
    _morning_report_envelope,
)


def test_governed_output_facade_rejects_raw_morning_report() -> None:
    with pytest.raises(
        ValueError,
        match="cannot bypass governed presentation",
    ):
        render_workflow_output_bundle(
            _morning_report_envelope(),
            output_format=None,
            raw=True,
        )


def test_generic_output_renderer_rejects_morning_report_direct_import() -> None:
    with pytest.raises(
        ValueError,
        match="requires the governed presentation renderer",
    ):
        render_generic_workflow_output_bundle(
            _morning_report_envelope(),
            output_format="pdf",
        )
