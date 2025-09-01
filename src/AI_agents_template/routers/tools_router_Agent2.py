from fastapi import APIRouter
from fastmcp import FastMCP
from AI_agents_template.utils.docstring_generator import auto_docstring
from AI_agents_template.models import (
    Example2Input,
    Example2Output,
)
from AI_agents_template.tools import example2_tool

# Import tool functions and their models
from AI_agents_template.routers.setup_connections import get_runtime_ctx

router = APIRouter()
mcp = FastMCP(name="Agent2")


# describe_timeseries tool registration
@mcp.tool()
@router.post("/tools.agent2/example2")
@auto_docstring("Example2")
async def example2_mcp(
    input: Example2Input,
) -> Example2Output:
    # TODO: add authentication passing to the get_runtime
    ctx = get_runtime_ctx()
    return await example2_tool(ctx, input)
