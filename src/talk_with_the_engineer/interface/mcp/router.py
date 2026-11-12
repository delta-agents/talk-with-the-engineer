from fastapi import APIRouter
from fastmcp import FastMCP
from talk_with_the_engineer.utils.docstring_generator import auto_docstring
from talk_with_the_engineer.interface.schemas.allocation import (
    AllocationInput,
    AllocationOutput,
)
from talk_with_the_engineer.interface.schemas.cascade import (
    CascadeInput,
    CascadeOutput,
)
from talk_with_the_engineer.interface.schemas.discharge import (
    DischargeInputGivenDischarge,
    DischargeInputGivenH,
    DischargeOutput,
)
from talk_with_the_engineer.interface.schemas.optimize import (
    OptimizeInput,
    OptimizeOutput,
)
from talk_with_the_engineer.interface.schemas.read_me import (
    ReadMeInput,
    ReadMeOutput,
)
from talk_with_the_engineer.interface.schemas.retain import (
    RetentionInputGivenArea,
    RetentionInputGivenH,
    RetentionOutput,
)
from talk_with_the_engineer.interface.schemas.store import (
    StoreInputGivenArea,
    StoreInputGivenH,
    StoreOutput,
)
from talk_with_the_engineer.interface.schemas.supply import (
    SupplyInputGivenH,
    SupplyInputGivenSupply,
    SupplyOutput,
)

# De toolfuncties zelf. De `_pydantic_ai`-achtervoegsels bestaan omdat de MCP-wrappers
# hieronder dezelfde namen dragen: de wrapper is wat een client ziet, de geimporteerde
# functie is wat er rekent.
from talk_with_the_engineer.interface.tools.allocation import (
    calculate_allocation_given_shortage as calculate_allocation_given_shortage_pydantic_ai,
)
from talk_with_the_engineer.interface.tools.cascade import (
    calculate_cascade_given_excess as calculate_cascade_given_excess_pydantic_ai,
)
from talk_with_the_engineer.interface.tools.discharge import (
    calculate_discharge_given_discharge as calculate_discharge_given_discharge_pydantic_ai,
)
from talk_with_the_engineer.interface.tools.discharge import (
    calculate_discharge_given_h as calculate_discharge_given_h_pydantic_ai,
)
from talk_with_the_engineer.interface.tools.find_package import (
    find_package_given_protection as find_package_given_protection_pydantic_ai,
)
from talk_with_the_engineer.interface.tools.read_me import (
    read_me as read_me_pydantic_ai,
)
from talk_with_the_engineer.interface.tools.retain import (
    calculate_retention_given_area as calculate_retention_given_area_pydantic_ai,
)
from talk_with_the_engineer.interface.tools.retain import (
    calculate_retention_given_h as calculate_retention_given_h_pydantic_ai,
)
from talk_with_the_engineer.interface.tools.store import (
    calculate_store_given_area as calculate_store_given_area_pydantic_ai,
)
from talk_with_the_engineer.interface.tools.store import (
    calculate_store_given_h as calculate_store_given_h_pydantic_ai,
)
from talk_with_the_engineer.interface.tools.supply import (
    calculate_supply_given_h as calculate_supply_given_h_pydantic_ai,
)
from talk_with_the_engineer.interface.tools.supply import (
    calculate_supply_given_supply as calculate_supply_given_supply_pydantic_ai,
)

from talk_with_the_engineer.interface.mcp.connections import get_runtime_ctx
from talk_with_the_engineer.interface.mcp.errors import as_tool_error


router = APIRouter()
mcp = FastMCP(name="RulesOfThumb")


# DE HANDLEIDING BIJ DEZE TOOLSET
# read_me tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/read_me")
@auto_docstring(
    "Read the manual for this toolset BEFORE relying on its answers. Four modules, ask for "
    "what you need: 'bronnen' (where the numbers come from - STOWA rainfall and drought "
    "statistics, cost sources, validation), 'vuistregels' (what the model does with them, "
    "and which assumptions drive the outcome), 'gebruik' (which tool answers which "
    "question), and 'terugkoppelen' (how to report the answer without changing its meaning "
    "- including what you must NOT read without checking `status`, and the strict "
    "distinction between waterstand and peil). Call it with no modules for a short index. "
    "This is guidance for you as the caller, not an answer for the user."
)
@as_tool_error
async def read_me(input: ReadMeInput) -> ReadMeOutput:
    ctx = get_runtime_ctx()
    return await read_me_pydantic_ai(ctx, input)


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
# calculate_cascade_given_excess tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/cascade_given_excess")
@auto_docstring(
    "Tool for WATER EXCESS at system scale: calculate the water levels across a cascade "
    "of water systems that drain into each other, and find where the drainage is binding "
    "- which pump cannot keep up, or where a downstream level blocks upstream discharge."
)
@as_tool_error
async def calculate_cascade_given_excess(
    input: CascadeInput,
) -> CascadeOutput:
    ctx = get_runtime_ctx()
    return await calculate_cascade_given_excess_pydantic_ai(ctx, input)


# TOOL FOR AN ALLOCATION QUESTION / VERDELINGSVRAAG
# calculate_allocation_given_shortage tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/allocation_given_shortage")
@auto_docstring(
    "Tool for WATER SHORTAGE at system scale: work out who gets water and who falls "
    "short when several areas draw from the same finite source, following the Dutch legal "
    "priority order (verdringingsreeks)."
)
@as_tool_error
async def calculate_allocation_given_shortage(
    input: AllocationInput,
) -> AllocationOutput:
    ctx = get_runtime_ctx()
    return await calculate_allocation_given_shortage_pydantic_ai(ctx, input)


# TOOL FOR A PACKAGE QUESTION / PAKKETVRAAG
# find_package_given_protection tool registration
@mcp.tool()
@router.post("/tools.RulesOfThumb/find_package_given_protection")
@auto_docstring(
    "Tool for a PACKAGE question: which COMBINATION of measures brings a water system to a "
    "required protection level, and what it costs. Use it as soon as there is more than one "
    "requirement, instead of orchestrating the single-measure tools yourself: the "
    "requirements share one scarce quantity and cannot be optimised separately. Three "
    "requirements, at least one of them: `max_dh_total_m` the inundation norm, "
    "`min_storage_mm` the storage under target level, and `max_shortfall_mm` the unmet "
    "demand after a drought - the only one that needs a drought, and the only one in which "
    "an intake counts. It answers with the region and not just the point, so never report "
    "`best` without `ranges` and `priceless` beside it, and read `status` first. Takes "
    'seconds. Manual: `read_me(modules=["pakketzoeker"])`.'
)
@as_tool_error
async def find_package_given_protection(
    input: OptimizeInput,
) -> OptimizeOutput:
    ctx = get_runtime_ctx()
    return await find_package_given_protection_pydantic_ai(ctx, input)


# --- gezondheidscheck bij het opstarten ---------------------------------------------


def warm_up() -> None:
    """Lees de twee databestanden in voordat de eerste aanroep binnenkomt.

    Dit is een GEZONDHEIDSCHECK en geen snelheidsmaatregel. Beide bestanden zitten achter
    een `lru_cache` en worden anders pas bij het eerste gebruik geladen; ontbreekt er een of
    is er een stuk, dan blijkt dat nu bij het opstarten en niet pas bij de eerste vraag van
    een gebruiker.

    Nagemeten kost het laden 2 ms voor de neerslagpatronen en 1 ms voor de droogtestatistiek
    - tegen 1,6 s voor het importeren van deze module, dat toch al bij het opstarten
    gebeurt. Er valt in dit pad dus geen wachttijd te winnen; wat het oplevert is dat een
    kapot bestand een opstartfout wordt.
    """
    from talk_with_the_engineer.core.stats.drought import (
        load_drought_statistics,
    )
    from talk_with_the_engineer.core.stats.rainfall import (
        load_rainfall_patterns,
    )

    load_rainfall_patterns()
    load_drought_statistics()


warm_up()
