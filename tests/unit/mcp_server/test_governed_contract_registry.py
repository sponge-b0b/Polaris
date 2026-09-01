from mcp_server.contracts import TOOL_OUTPUT_MODELS
from mcp_server.contracts.rag_presentation import RagAskResponse


def test_rag_tool_output_registry_uses_governed_response_contract() -> None:
    assert TOOL_OUTPUT_MODELS["polaris_rag_ask"] is RagAskResponse
