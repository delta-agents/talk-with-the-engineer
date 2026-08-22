"""De MCP-route: foutmeldingen moeten de aanroeper bereiken.

Dit is de route die een LLM daadwerkelijk gebruikt, dus hier telt het meest dat een
afgewezen aanroep uitlegt wélke waarden geldig zijn. FastMCP garandeert dat alleen voor
`ToolError`; andere excepties gaan door de generieke handler, die ze afhankelijk van
`mask_error_details` kan inslikken. Daarom zet `as_tool_error` de `ModelRetry` uit de
toolbody om.
"""

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from talk_with_the_engineer.routers.tools_router_RulesOfThumb import mcp
from tests.utils_tests import setup_dot_env

VALID_INPUT = {
    "return_period": 100,
    "time_of_year": "winter",
    "length_event_hrs": 96.0,
    "area_ha": 4000,
    "percentage_open_water": 3.5,
    "discharge_capacity_m3_per_sec": 5,
    "area_available_ha": 200,
}


@pytest.mark.asyncio
async def test_valid_call_over_mcp():
    setup_dot_env()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "calculate_store_given_area", {"input": VALID_INPUT}
        )
        assert result.content


@pytest.mark.asyncio
async def test_all_nine_tools_are_registered():
    async with Client(mcp) as client:
        names = {tool.name for tool in await client.list_tools()}
    assert names == {
        "calculate_retention_given_h",
        "calculate_retention_given_area",
        "calculate_store_given_h",
        "calculate_store_given_area",
        "calculate_discharge_given_h",
        "calculate_discharge_given_discharge",
        "calculate_supply_given_h",
        "calculate_supply_given_supply",
        "calculate_region_given_storm",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "override, expected_in_message",
    [
        ({"area_available_ha": 8000}, "niet mogelijk in dit watersysteem"),
    ],
)
async def test_tool_body_rejection_reaches_the_caller(override, expected_in_message):
    """Een ModelRetry uit de toolbody komt als ToolError met alleen het bericht terug.

    Zonder `as_tool_error` ging dit door de generieke handler van FastMCP, die het
    bericht afhankelijk van de instellingen kan inslikken.
    """
    setup_dot_env()
    async with Client(mcp) as client:
        with pytest.raises(ToolError) as excinfo:
            await client.call_tool(
                "calculate_store_given_area", {"input": {**VALID_INPUT, **override}}
            )
    message = str(excinfo.value)
    assert expected_in_message in message
    # geen "Error calling tool"-omhulsel: dit is de ToolError zelf
    assert not message.startswith("Error calling tool")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "override, expected_in_message",
    [
        ({"return_period": 7}, "Input should be 0.5"),
        ({"length_event_hrs": 100.0}, "Input should be 48.0, 96.0 or 192.0"),
        ({"percentage_open_water": -50}, "Input should be greater than 0"),
        ({"time_of_year": "lente"}, "Input should be 'winter' or 'summer'"),
        # stond eerder als ModelRetry in de toolbody; sinds area_available_ha ge=0 heeft
        # wijst het schema hem af, en dus met een veldpad erbij
        ({"area_available_ha": -5}, "greater than or equal to 0"),
    ],
)
async def test_schema_rejection_reaches_the_caller(override, expected_in_message):
    """Ook invoer die het schema afwijst moet uitleg opleveren.

    Die fouten ontstaan bij het omzetten van de argumenten naar het model, dus vóór
    `as_tool_error`; FastMCP rapporteert ze zelf. Sinds de beperkingen als `Literal` in
    het type staan is dat een echte pydantic-validatiefout, met de toegestane waarden
    erin. Deze test legt vast dat die tekst doorkomt.
    """
    setup_dot_env()
    async with Client(mcp) as client:
        with pytest.raises(ToolError) as excinfo:
            await client.call_tool(
                "calculate_store_given_area", {"input": {**VALID_INPUT, **override}}
            )
    assert expected_in_message in str(excinfo.value)
