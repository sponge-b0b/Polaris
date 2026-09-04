from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from application.services.base.service_request import ServiceRequest
from application.services.base.service_result import ServiceResult

RequestPayloadT = TypeVar("RequestPayloadT")
ResultPayloadT = TypeVar("ResultPayloadT")


@runtime_checkable
class ApplicationService[RequestPayloadT, ResultPayloadT](
    Protocol,
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
class ValidatingApplicationService[RequestPayloadT](
    Protocol,
):
    """
    Optional service extension for request-specific validation.
    """

    async def validate_request(
        self,
        request: ServiceRequest[RequestPayloadT],
    ) -> tuple[str, ...]: ...
