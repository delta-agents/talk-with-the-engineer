from fastapi import APIRouter
from fastmcp import FastMCP
from skip_the_engineer.utils.docstring_generator import auto_docstring
from skip_the_engineer.models import (
    HoldInput,
    HoldOutput,
)
from skip_the_engineer.tools import hold_tool

# Import tool functions and their models
from skip_the_engineer.routers.setup_connections import get_runtime_ctx

router = APIRouter()
mcp = FastMCP(name="RulesOfThumb")


# describe_timeseries tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/hold")
@auto_docstring("Tool used to calculate the holding capacity of a water system.")
async def hold_mcp(
    input: HoldInput,
) -> HoldOutput:
    ctx = get_runtime_ctx()
    return await hold_tool(ctx, input)
