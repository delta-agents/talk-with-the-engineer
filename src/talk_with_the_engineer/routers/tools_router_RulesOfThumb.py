from fastapi import APIRouter
from fastmcp import FastMCP
from talk_with_the_engineer.utils.docstring_generator import auto_docstring
from talk_with_the_engineer.models import (
    HoldInput,
    HoldOutput,
    DisposeInput,
    DisposeOutput,
    StoreInput,
    StoreOutput,
)
from talk_with_the_engineer.tools import hold_tool, store_tool, dispose_tool

# Import tool functions and their models
from talk_with_the_engineer.routers.setup_connections import get_runtime_ctx


router = APIRouter()
mcp = FastMCP(name="RulesOfThumb")


# describe the hold tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/hold")
@auto_docstring("Tool used to calculate the holding capacity of a water system.")
async def hold_mcp(
    input: HoldInput,
) -> HoldOutput:
    ctx = get_runtime_ctx()
    return await hold_tool(ctx, input)


# describe_timeseries tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/store")
@auto_docstring("Tool used to calculate the storage capacity of a water system.")
async def store_mcp(
    input: StoreInput,
) -> StoreOutput:
    ctx = get_runtime_ctx()
    return await store_tool(ctx, input)


# describe_timeseries tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/dispose")
@auto_docstring("Tool used to calculate the disposal capacity of a water system.")
async def dispose_mcp(
    input: DisposeInput,
) -> DisposeOutput:
    ctx = get_runtime_ctx()
    return await dispose_tool(ctx, input)
