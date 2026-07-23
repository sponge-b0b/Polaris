from __future__ import annotations

import logging

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from domain.macro.models import MacroDataSnapshot, MacroIndicatorObservation
from integration.clients.macro.fred_macro_client import (
    FredMacroClient,
    FredSeriesObservation,
)
from integration.providers.provider_telemetry import record_provider_call

logger = logging.getLogger(__name__)

_MACRO_SERIES: tuple[tuple[str, str, str], ...] = (
    ("cpi", "CPIAUCSL", "inflation"),
    ("core_cpi", "CPILFESL", "inflation"),
    ("pce", "PCEPI", "inflation"),
    ("fed_funds_rate", "FEDFUNDS", "rates"),
    ("treasury_2y", "DGS2", "rates"),
    ("treasury_10y", "DGS10", "rates"),
    ("unemployment_rate", "UNRATE", "labor"),
    ("m2_money_supply", "M2SL", "liquidity"),
    ("vix", "VIXCLS", "volatility"),
)


class LiveMacroProvider:
    def __init__(
        self,
        macro_client: FredMacroClient,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:
        self.macro_client = macro_client
        self.telemetry = telemetry

    async def get_macro_snapshot(self) -> MacroDataSnapshot:
        return await record_provider_call(
            telemetry=self.telemetry,
            provider_name=self.__class__.__name__,
            operation="get_macro_snapshot",
            call=self._load_macro_snapshot,
            attributes={
                "vendor": "fred",
                "series_count": len(_MACRO_SERIES),
            },
        )

    async def _load_macro_snapshot(self) -> MacroDataSnapshot:
        observations = await self.macro_client.get_latest_observations(
            tuple(series_id for _, series_id, _ in _MACRO_SERIES)
        )
        observations_by_id = {
            observation.series_id: observation for observation in observations
        }

        values: dict[str, float | None] = {}
        failed_fields: list[str] = []
        indicator_observations: list[MacroIndicatorObservation] = []
        for field_name, series_id, indicator_category in _MACRO_SERIES:
            observation = observations_by_id.get(series_id)
            if observation is None:
                observation = FredSeriesObservation(
                    series_id=series_id,
                    value=None,
                    error_type="MissingObservation",
                    error_message="FRED batch response omitted the requested series.",
                )

            values[field_name] = observation.value
            if not observation.failed:
                if (
                    observation.value is not None
                    and observation.observation_timestamp is not None
                ):
                    indicator_observations.append(
                        MacroIndicatorObservation(
                            indicator_name=field_name,
                            value=observation.value,
                            observation_timestamp=observation.observation_timestamp,
                            source="fred",
                            indicator_category=indicator_category,
                            region="US",
                        )
                    )
                continue

            failed_fields.append(field_name)
            logger.warning(
                "Macro provider series failed",
                extra={
                    "macro_field": field_name,
                    "fred_series_id": series_id,
                    "error_type": observation.error_type,
                    "error_message": observation.error_message,
                },
            )

        if len(failed_fields) == len(_MACRO_SERIES):
            raise RuntimeError("All macro provider series failed.")

        return MacroDataSnapshot(
            cpi=values["cpi"],
            core_cpi=values["core_cpi"],
            pce=values["pce"],
            fed_funds_rate=values["fed_funds_rate"],
            treasury_2y=values["treasury_2y"],
            treasury_10y=values["treasury_10y"],
            unemployment_rate=values["unemployment_rate"],
            m2_money_supply=values["m2_money_supply"],
            vix=values["vix"],
            failed_fields=tuple(failed_fields),
            observations=tuple(indicator_observations),
        )
