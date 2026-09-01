from mcp_server.contracts.models import TOOL_INPUT_MODELS
from mcp_server.contracts.models import (
    TOOL_OUTPUT_MODELS as _BASE_TOOL_OUTPUT_MODELS,
)
from mcp_server.contracts.rag_presentation import RagAskResponse
from mcp_server.contracts.structured_outputs import (
    StructuredMcpCustomerAgentResponse,
)

TOOL_OUTPUT_MODELS = {
    **_BASE_TOOL_OUTPUT_MODELS,
    "polaris_rag_ask": RagAskResponse,
}

__all__ = [
    "RagAskResponse",
    "StructuredMcpCustomerAgentResponse",
    "TOOL_INPUT_MODELS",
    "TOOL_OUTPUT_MODELS",
]
