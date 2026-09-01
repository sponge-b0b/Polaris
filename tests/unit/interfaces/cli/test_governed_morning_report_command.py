from __future__ import annotations

import pytest
import typer

from interfaces.cli.commands.morning_report_command import morning_report


def test_morning_report_raw_output_cannot_bypass_governed_presentation() -> None:
    with pytest.raises(
        typer.BadParameter,
        match="cannot bypass governed morning-report presentation",
    ):
        morning_report(
            symbol="SPY",
            output_format=None,
            output=None,
            raw=True,
            plugin_dirs=[],
        )
