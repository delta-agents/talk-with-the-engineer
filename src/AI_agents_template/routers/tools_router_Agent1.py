from fastapi import APIRouter
from fastmcp import FastMCP
from AI_agents_template.utils.docstring_generator import auto_docstring
from AI_agents_template.models import (
    Example1Input,
    Example1Output,
)
from AI_agents_template.tools import example1_tool

# Import tool functions and their models
from AI_agents_template.routers.setup_connections import get_runtime_ctx

router = APIRouter()
mcp = FastMCP(name="Agent1")


# describe_timeseries tool registration
@mcp.tool()
@router.post("/tools.agent1/example1")
@auto_docstring("Example1")
async def example1_mcp(
    input: Example1Input,
) -> Example1Output:
    # TODO: add authentication passing to the get_runtime
    ctx = get_runtime_ctx()
    return await example1_tool(ctx, input)
