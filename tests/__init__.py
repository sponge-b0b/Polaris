from __future__ import annotations

import importlib
import sys

_SUPPORT_MODULE_ALIASES = {
    "binding_support": "tests.application.evidence.binding_support",
    "configuration_support": "tests.domain.configuration.configuration_support",
    "evidence_support": "tests.application.evidence.evidence_support",
    "sufficiency_support": "tests.domain.evidence.sufficiency_support",
}

for _legacy_name, _canonical_name in _SUPPORT_MODULE_ALIASES.items():
    sys.modules[f"{__name__}.{_legacy_name}"] = importlib.import_module(_canonical_name)
