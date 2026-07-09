from __future__ import annotations

from typing import Generic
from typing import Protocol
from typing import TypeVar
from typing import runtime_checkable

from application.services.base.service_request import ServiceRequest
from application.services.base.service_result import ServiceResult

RequestPayloadT = TypeVar("RequestPayloadT")
ResultPayloadT = TypeVar("ResultPayloadT")


@runtime_checkable
class ApplicationService(
    Protocol,
    Generic[RequestPayloadT, ResultPayloadT],
):
    """
    Base contract for orchestrated application services.
    """

    service_name: str

    async def run(
        self,
        request: ServiceRequest[RequestPayloadT],
    ) -> ServiceResult[ResultPayloadT]: ...

    async def _execute(
        self,
        request: RequestPayloadT,
    ) -> ResultPayloadT: ...


@runtime_checkable
class ValidatingApplicationService(
    Protocol,
    Generic[RequestPayloadT],
):
    """
    Optional service extension for request-specific validation.
    """

    async def validate_request(
        self,
        request: ServiceRequest[RequestPayloadT],
    ) -> tuple[str, ...]: ...
