from __future__ import annotations

import logging
from typing import Any

import pytest

from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.events.telemetry_exception_details import (
    TelemetryExceptionDetails,
)
from core.telemetry.events.telemetry_event import TelemetryEventLevel
from core.telemetry.logging import TelemetryLogger


@pytest.mark.asyncio
async def test_telemetry_logger_emits_structured_log_extra(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger_name = "polaris.telemetry.test"
    telemetry_logger = TelemetryLogger(
        logger_name=logger_name,
    )
    event = TelemetryEvent(
        event_id="event-1",
        event_type="runtime.workflow.completed",
        source="runtime",
        level=TelemetryEventLevel.INFO,
        workflow_id="morning_report",
        execution_id="execution-1",
        runtime_id="runtime-1",
        node_name="technical_node",
        correlation_id="correlation-1",
        trace_id="trace-1",
        span_id="span-1",
        parent_span_id="parent-span-1",
        duration_seconds=1.25,
        success=True,
        error_count=0,
        tags=("runtime", "workflow"),
        attributes={
            "operation": "run_workflow",
        },
        payload={
            "status": "succeeded",
        },
    )

    with caplog.at_level(
        logging.INFO,
        logger=logger_name,
    ):
        await telemetry_logger.emit(
            event,
        )

    records = [record for record in caplog.records if record.name == logger_name]

    assert len(records) == 1
    record = records[0]
    telemetry = getattr(
        record,
        "telemetry",
    )

    assert isinstance(
        telemetry,
        dict,
    )

    structured = telemetry
    assert structured["event_id"] == "event-1"
    assert structured["event_type"] == "runtime.workflow.completed"
    assert structured["source"] == "runtime"
    assert structured["severity"] == "info"
    assert structured["level"] == "info"
    assert structured["workflow_id"] == "morning_report"
    assert structured["execution_id"] == "execution-1"
    assert structured["runtime_id"] == "runtime-1"
    assert structured["node_name"] == "technical_node"
    assert structured["correlation_id"] == "correlation-1"
    assert structured["trace_id"] == "trace-1"
    assert structured["span_id"] == "span-1"
    assert structured["parent_span_id"] == "parent-span-1"
    assert structured["duration_seconds"] == 1.25
    assert structured["success"] is True
    assert structured["error_count"] == 0
    assert structured["tags"] == [
        "runtime",
        "workflow",
    ]
    assert structured["attributes"] == {
        "operation": "run_workflow",
    }
    assert structured["payload"] == {
        "status": "succeeded",
    }
    assert getattr(record, "event_id") == "event-1"
    assert getattr(record, "event_type") == "runtime.workflow.completed"
    assert getattr(record, "severity") == "info"
    assert getattr(record, "workflow_id") == "morning_report"
    assert getattr(record, "execution_id") == "execution-1"
    assert getattr(record, "runtime_id") == "runtime-1"
    assert getattr(record, "node_name") == "technical_node"
    assert getattr(record, "correlation_id") == "correlation-1"
    assert getattr(record, "trace_id") == "trace-1"
    assert getattr(record, "span_id") == "span-1"
    assert getattr(record, "parent_span_id") == "parent-span-1"

    message = record.getMessage()
    assert "runtime.workflow.completed" in message
    assert "event_id=event-1" in message
    assert "trace_id=trace-1" in message
    assert "span_id=span-1" in message
    assert "correlation_id=correlation-1" in message


@pytest.mark.asyncio
async def test_telemetry_logger_can_omit_payload_and_attributes(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger_name = "polaris.telemetry.test.omit"
    telemetry_logger = TelemetryLogger(
        logger_name=logger_name,
        include_payload=False,
        include_attributes=False,
    )

    with caplog.at_level(
        logging.WARNING,
        logger=logger_name,
    ):
        await telemetry_logger.emit(
            TelemetryEvent(
                event_type="runtime.system.warning",
                source="runtime",
                level=TelemetryEventLevel.WARNING,
                attributes={
                    "operation": "emit",
                },
                payload={
                    "warning": "subscriber failed",
                },
            )
        )

    telemetry = getattr(
        caplog.records[-1],
        "telemetry",
    )

    assert isinstance(
        telemetry,
        dict,
    )

    structured: dict[str, Any] = telemetry
    assert "payload" not in structured
    assert "attributes" not in structured


@pytest.mark.asyncio
async def test_telemetry_logger_redacts_nested_secrets_without_mutating_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger_name = "polaris.telemetry.test.redaction"
    telemetry_logger = TelemetryLogger(logger_name=logger_name)
    event = TelemetryEvent(
        event_type="integration.provider.failed",
        source="integration",
        level=TelemetryEventLevel.ERROR,
        attributes={
            "api_key": "secret-key",
            "token_count": 42,
        },
        payload={
            "request": {
                "authorization": "Bearer secret-token",
                "url": "https://example.test/data",
            },
        },
    )

    with caplog.at_level(logging.ERROR, logger=logger_name):
        await telemetry_logger.emit(event)

    structured = getattr(caplog.records[-1], "telemetry")
    assert structured["attributes"]["api_key"] == "[REDACTED]"
    assert structured["attributes"]["token_count"] == 42
    assert structured["payload"]["request"]["authorization"] == "[REDACTED]"
    assert event.attributes["api_key"] == "secret-key"


@pytest.mark.asyncio
async def test_telemetry_logger_renders_sanitized_traceback_exactly_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger_name = "polaris.telemetry.test.exception"
    telemetry_logger = TelemetryLogger(logger_name=logger_name)

    try:
        raise RuntimeError("password=super-secret")
    except RuntimeError as error:
        exception_details = TelemetryExceptionDetails.from_exception(error)

    event = TelemetryEvent(
        event_id="event-exception",
        event_type="application.service.failed",
        source="application",
        level=TelemetryEventLevel.ERROR,
        trace_id="trace-exception",
        span_id="span-exception",
        correlation_id="correlation-exception",
        exception_details=exception_details,
    )

    with caplog.at_level(logging.ERROR, logger=logger_name):
        await telemetry_logger.emit(event)

    record = caplog.records[-1]
    message = record.getMessage()
    structured = getattr(record, "telemetry")

    assert message.count("Traceback (most recent call last):") == 1
    assert "super-secret" not in message
    assert "password=[REDACTED]" in message
    assert record.exc_info is None
    assert structured["exception_details"] == {
        "exception_type": "RuntimeError",
        "message": "password=[REDACTED]",
        "stack_trace_truncated": False,
    }
    assert "stack_trace" not in structured["exception_details"]
    assert "super-secret" not in str(structured)
