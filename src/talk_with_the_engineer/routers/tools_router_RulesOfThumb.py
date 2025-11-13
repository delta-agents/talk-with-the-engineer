from fastapi import APIRouter
from fastmcp import FastMCP
from talk_with_the_engineer.utils.docstring_generator import auto_docstring
from talk_with_the_engineer.models import (
    HoldInput,
    HoldOutput,
    DischargeInput,
    DischargeOutput,
    StoreInputGivenArea,
    StoreInputGivenH,
    StoreOutput,
)
from talk_with_the_engineer.tools import hold_tool, discharge_tool
from talk_with_the_engineer.tools import (
    calculate_store_given_area as calculate_store_given_area_pydantic_ai,
)
from talk_with_the_engineer.tools import (
    calculate_store_given_h as calculate_store_given_h_pydantic_ai,
)


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
@auto_docstring(
    "Tool used to calculate the storage capacity of a water system given the available area."
)
async def calculate_store_given_area(
    input: StoreInputGivenArea,
) -> StoreOutput:
    ctx = get_runtime_ctx()
    return await calculate_store_given_area_pydantic_ai(ctx, input)


@mcp.tool()
@router.post("/tools.RulesOfThumb/store")
@auto_docstring(
    "Tool used to calculate the storage capacity of a water system given the available height in the canal."
)
async def calculate_store_given_h(
    input: StoreInputGivenH,
) -> StoreOutput:
    ctx = get_runtime_ctx()
    return await calculate_store_given_h_pydantic_ai(ctx, input)


# describe_timeseries tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/discharge")
@auto_docstring("Tool used to calculate the discharge capacity of a water system.")
async def discharge_mcp(
    input: DischargeInput,
) -> DischargeOutput:
    ctx = get_runtime_ctx()
    return await discharge_tool(ctx, input)
