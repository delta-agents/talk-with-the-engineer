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
async def test_all_eleven_tools_are_registered():
    async with Client(mcp) as client:
        names = {tool.name for tool in await client.list_tools()}
    assert names == {
        # de handleiding: geen berekening, maar uitleg over de andere tien
        "read_me",
        "calculate_retention_given_h",
        "calculate_retention_given_area",
        "calculate_store_given_h",
        "calculate_store_given_area",
        "calculate_discharge_given_h",
        "calculate_discharge_given_discharge",
        "calculate_supply_given_h",
        "calculate_supply_given_supply",
        "calculate_cascade_given_excess",
        "calculate_allocation_given_shortage",
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


@pytest.mark.asyncio
async def test_an_internal_model_never_leaks_its_class_name():
    """Een ruwe validatiedump uit de toolbody is geen foutmelding maar een lek.

    `days_to_retain_discharge: -5` liep door tot in `PolderState` en gaf "1 validation error
    for PolderState / days_to_retain / Input should be greater than or equal to 0", met een
    link naar errors.pydantic.dev erachter. De interne klassenaam en een veldnaam die niet
    is wat de beller invulde, in het Engels, met een verwijzing waar een waterbeheerder
    niets aan heeft. Zie B12 in bevindingenrapport-vuistregels-deel-2.md.

    De weigering staat nu op het invoermodel, met een Nederlandse melding; `as_tool_error`
    is het vangnet eronder voor alles wat daar doorheen zou glippen.
    """
    setup_dot_env()
    payload = {
        "return_period": 100,
        "area_ha": 4000,
        "percentage_open_water": 3.5,
        "discharge_capacity_m3_per_sec": 5,
        "delta_h_available": 1.0,
        "days_to_retain_discharge": -5,
    }
    async with Client(mcp) as client:
        with pytest.raises(ToolError) as excinfo:
            await client.call_tool("calculate_retention_given_h", {"input": payload})

    message = str(excinfo.value)
    assert "PolderState" not in message
    assert "errors.pydantic.dev" not in message
    assert "days_to_retain_discharge" in message
    assert "kan niet negatief zijn" in message


def test_the_lower_bound_on_the_delay_is_visible_in_the_schema():
    """Weigeren is goed; er van tevoren voor waarschuwen is beter.

    Zelfde afweging als bij `delta_area_ha`: de grens staat als `minimum` in het schema,
    zodat een client hem ziet voordat hij de aanroep verstuurt, maar niet als `ge=` - dat
    zou aan de MCP-grens juist weer een ruwe validatiedump opleveren.
    """
    from talk_with_the_engineer.models import (
        RetentionInputGivenArea,
        RetentionInputGivenH,
    )

    for model in (RetentionInputGivenH, RetentionInputGivenArea):
        field = model.model_json_schema()["properties"]["days_to_retain_discharge"]
        assert field["minimum"] == 0


def test_the_data_assets_are_read_at_startup_and_not_at_first_use():
    """Een ontbrekend databestand hoort bij het opstarten op te vallen, niet bij een vraag.

    Beide bestanden zitten achter een `lru_cache`, dus ze werden pas bij het eerste gebruik
    geladen. Dat is nagemeten en kost samen 3 ms - dus het verklaart de vier minuten uit B9
    niet, en die hang had een andere oorzaak buiten deze code. Wat het wel oplevert is dat
    een stuk of ontbrekend bestand een opstartfout wordt in plaats van een toolfout.
    """
    from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_drought import (
        _load_drought_statistics,
    )
    from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_rainfall import (
        _load_rainfall_patterns,
    )

    # het importeren van de router heeft `warm_up()` al gedraaid; de caches zijn dus gevuld
    assert _load_rainfall_patterns.cache_info().currsize == 1
    assert _load_drought_statistics.cache_info().currsize == 1
