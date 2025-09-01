from fastapi import APIRouter
from fastmcp import FastMCP
from skip_the_engineer.utils.docstring_generator import auto_docstring
from skip_the_engineer.models import (
    Example2Input,
    Example2Output,
)
from skip_the_engineer.tools import example2_tool

# Import tool functions and their models
from skip_the_engineer.routers.setup_connections import get_runtime_ctx

router = APIRouter()
mcp = FastMCP(name="Prerequisites")


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
