from fastapi import APIRouter
from fastmcp import FastMCP
from talk_with_the_engineer.utils.docstring_generator import auto_docstring
from talk_with_the_engineer.models import (
    RetentionInputGivenH,
    RetentionInputGivenArea,
    RetentionOutput,
    DischargeInputGivenH,
    DischargeInputGivenDischarge,
    DischargeOutput,
    StoreInputGivenArea,
    StoreInputGivenH,
    StoreOutput,
    AllocationInput,
    AllocationOutput,
    RegionInput,
    RegionOutput,
    SupplyInputGivenH,
    SupplyInputGivenSupply,
    SupplyOutput,
)

from talk_with_the_engineer.tools import (
    calculate_retention_given_h as calculate_retention_given_h_pydantic_ai,
)
from talk_with_the_engineer.tools import (
    calculate_retention_given_area as calculate_retention_given_area_pydantic_ai,
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
from talk_with_the_engineer.tools import (
    calculate_region_given_storm as calculate_region_given_storm_pydantic_ai,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.allocation import (
    calculate_allocation_given_drought as calculate_allocation_given_drought_pydantic_ai,
)
from talk_with_the_engineer.tools import (
    calculate_supply_given_h as calculate_supply_given_h_pydantic_ai,
)
from talk_with_the_engineer.tools import (
    calculate_supply_given_supply as calculate_supply_given_supply_pydantic_ai,
)

# Import tool functions and their models
from talk_with_the_engineer.routers.mcp_errors import as_tool_error
from talk_with_the_engineer.routers.setup_connections import get_runtime_ctx


router = APIRouter()
mcp = FastMCP(name="RulesOfThumb")


# TOOLS FOR RETENTION/VASTHOUDEN
# calculate_retention_given_h tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/retention_given_h")
@auto_docstring(
    "Tool used to calculate the change in retention capacity of a water system given the change in water level."
)
@as_tool_error
async def calculate_retention_given_h(
    input: RetentionInputGivenH,
) -> RetentionOutput:
    ctx = get_runtime_ctx()
    return await calculate_retention_given_h_pydantic_ai(ctx, input)


# calculate_retention_given_area tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/retention_given_area")
@auto_docstring(
    "Tool used to calculate the change in retention capacity of a water system given the change in retention area."
)
@as_tool_error
async def calculate_retention_given_area(
    input: RetentionInputGivenArea,
) -> RetentionOutput:
    ctx = get_runtime_ctx()
    return await calculate_retention_given_area_pydantic_ai(ctx, input)


# TOOLS FOR STORAGE/BERGEN
# calculate_store_given_h tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/store_given_h")
@auto_docstring(
    "Tool used to calculate the change in storage capacity of a water system (area of open water) given the change in waterlevel."
)
@as_tool_error
async def calculate_store_given_h(
    input: StoreInputGivenH,
) -> StoreOutput:
    ctx = get_runtime_ctx()
    return await calculate_store_given_h_pydantic_ai(ctx, input)


# calculate_store_given_area tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/store_given_area")
@auto_docstring(
    "Tool used to calculate the change in water level that can be achieved with a given change in storage capacity (area of open water)."
)
@as_tool_error
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
    "Tool used to calculate the change in discharge capacity of a water system given the change in waterlevel."
)
@as_tool_error
async def calculate_discharge_given_h(
    input: DischargeInputGivenH,
) -> DischargeOutput:
    ctx = get_runtime_ctx()
    return await calculate_discharge_given_h_pydantic_ai(ctx, input)


# calculate_discharge_given_discharge tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/discharge_given_discharge")
@auto_docstring(
    "Tool used to calculate the change in water level that can be achieved with a given change in discharge capacity."
)
@as_tool_error
async def calculate_discharge_given_discharge(
    input: DischargeInputGivenDischarge,
) -> DischargeOutput:
    ctx = get_runtime_ctx()
    return await calculate_discharge_given_discharge_pydantic_ai(ctx, input)


# TOOLS FOR SUPPLY/AANVOEREN
# calculate_supply_given_h tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/supply_given_h")
@auto_docstring(
    "Tool used to calculate the intake capacity a water system needs to cover a "
    "precipitation deficit without drawing the level down too far."
)
@as_tool_error
async def calculate_supply_given_h(
    input: SupplyInputGivenH,
) -> SupplyOutput:
    ctx = get_runtime_ctx()
    return await calculate_supply_given_h_pydantic_ai(ctx, input)


# calculate_supply_given_supply tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/supply_given_supply")
@auto_docstring(
    "Tool used to calculate what a given intake capacity does to the water level and to "
    "the unmet water demand during a precipitation deficit."
)
@as_tool_error
async def calculate_supply_given_supply(
    input: SupplyInputGivenSupply,
) -> SupplyOutput:
    ctx = get_runtime_ctx()
    return await calculate_supply_given_supply_pydantic_ai(ctx, input)


# TOOL FOR A SYSTEM QUESTION / SYSTEEMVRAAG
# calculate_region_given_storm tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/region_given_storm")
@auto_docstring(
    "Tool used to calculate the water levels across a group of water systems that drain "
    "into each other, and to find where the coupling between them is binding."
)
@as_tool_error
async def calculate_region_given_storm(
    input: RegionInput,
) -> RegionOutput:
    ctx = get_runtime_ctx()
    return await calculate_region_given_storm_pydantic_ai(ctx, input)


# TOOL FOR AN ALLOCATION QUESTION / VERDELINGSVRAAG
# calculate_allocation_given_drought tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/allocation_given_drought")
@auto_docstring(
    "Tool used to work out who gets water and who falls short when several areas draw "
    "from the same finite source during a drought, following the Dutch legal priority "
    "order (verdringingsreeks)."
)
@as_tool_error
async def calculate_allocation_given_drought(
    input: AllocationInput,
) -> AllocationOutput:
    ctx = get_runtime_ctx()
    return await calculate_allocation_given_drought_pydantic_ai(ctx, input)
