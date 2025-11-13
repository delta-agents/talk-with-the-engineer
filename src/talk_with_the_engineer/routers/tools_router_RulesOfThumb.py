from fastapi import APIRouter
from fastmcp import FastMCP
from talk_with_the_engineer.utils.docstring_generator import auto_docstring
from talk_with_the_engineer.models import (
    HoldInputGivenH,
    HoldInputGivenArea,
    HoldOutput,
    DischargeInputGivenH,
    DischargeInputGivenDischarge,
    DischargeOutput,
    StoreInputGivenArea,
    StoreInputGivenH,
    StoreOutput,
)

from talk_with_the_engineer.tools import (
    calculate_hold_given_h as calculate_hold_given_h_pydantic_ai,
)
from talk_with_the_engineer.tools import (
    calculate_hold_given_area as calculate_hold_given_area_pydantic_ai,
)
from talk_with_the_engineer.tools import (
    calculate_store_given_area as calculate_store_given_area_pydantic_ai,
)
from talk_with_the_engineer.tools import (
    calculate_store_given_h as calculate_store_given_h_pydantic_ai,
)
from talk_with_the_engineer.tools import (
    calculate_discharge_given_h as calculate_discharge_given_h_pydantic_ai,
)
from talk_with_the_engineer.tools import (
    calculate_discharge_given_discharge as calculate_discharge_given_discharge_pydantic_ai,
)

# Import tool functions and their models
from talk_with_the_engineer.routers.setup_connections import get_runtime_ctx


router = APIRouter()
mcp = FastMCP(name="RulesOfThumb")


# TOOLS FOR HOLD/RETENTION/VASTHOUDEN
# calculate_hold_given_h tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/hold_given_h")
@auto_docstring(
    "Tool used to calculate the holding capacity of a water system given the available height in the canal."
)
async def calculate_hold_given_h(
    input: HoldInputGivenH,
) -> HoldOutput:
    ctx = get_runtime_ctx()
    return await calculate_hold_given_h_pydantic_ai(ctx, input)


# calculate_hold_given_area tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/hold_given_area")
@auto_docstring(
    "Tool used to calculate the holding capacity of a water system given the available area."
)
async def calculate_hold_given_area(
    input: HoldInputGivenArea,
) -> HoldOutput:
    ctx = get_runtime_ctx()
    return await calculate_hold_given_area_pydantic_ai(ctx, input)


# TOOLS FOR STORAGE/BERGEN
# calculate_store_given_h tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/store_given_h")
@auto_docstring(
    "Tool used to calculate the storage capacity of a water system (area of open water) given the available height in the canal."
)
async def calculate_store_given_h(
    input: StoreInputGivenH,
) -> StoreOutput:
    ctx = get_runtime_ctx()
    return await calculate_store_given_h_pydantic_ai(ctx, input)

# calculate_store_given_area tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/store_given_area")
@auto_docstring(
    "Tool used to calculate the water level reduction that can be achieved with a given storage capacity (area of open water)."
)
async def calculate_store_given_area(
    input: StoreInputGivenArea,
) -> StoreOutput:
    ctx = get_runtime_ctx()
    return await calculate_store_given_area_pydantic_ai(ctx, input)


# TOOLS FOR DISCHARGE/AFVOEREN
# calculate_discharge_given_h tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/discharge_given_h")
@auto_docstring(
    "Tool used to calculate the discharge capacity of a water system given the available height in the canal."
)
async def calculate_discharge_given_h(
    input: DischargeInputGivenH,
) -> DischargeOutput:
    ctx = get_runtime_ctx()
    return await calculate_discharge_given_h_pydantic_ai(ctx, input)

# calculate_discharge_given_discharge tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/discharge_given_discharge")
@auto_docstring(
    "Tool used to calculate the water level reduction that can be achieved with a given discharge capacity."
)
async def calculate_discharge_given_discharge(
    input: DischargeInputGivenDischarge,
) -> DischargeOutput:
    ctx = get_runtime_ctx()
    return await calculate_discharge_given_discharge_pydantic_ai(ctx, input)