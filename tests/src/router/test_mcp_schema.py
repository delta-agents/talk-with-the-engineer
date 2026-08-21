"""Wat een LLM van de MCP-tools te zien krijgt.

De tools zijn alleen bruikbaar als hun beschrijving en argumentschema kloppen: daar leest
een model uit hoe het moet aanroepen en welke waarden geldig zijn. Deze module test dat
contract, niet de berekening.
"""

import json
import re

import pytest
from fastmcp import Client

from talk_with_the_engineer.models import (
    DischargeInputGivenDischarge,
    DischargeInputGivenH,
    RetentionInputGivenArea,
    RetentionInputGivenH,
    StoreInputGivenArea,
    StoreInputGivenH,
)
from talk_with_the_engineer.routers.tools_router_RulesOfThumb import mcp
from tests.utils_tests import setup_dot_env

TOOL_INPUT_MODELS = {
    "calculate_retention_given_h": RetentionInputGivenH,
    "calculate_retention_given_area": RetentionInputGivenArea,
    "calculate_store_given_h": StoreInputGivenH,
    "calculate_store_given_area": StoreInputGivenArea,
    "calculate_discharge_given_h": DischargeInputGivenH,
    "calculate_discharge_given_discharge": DischargeInputGivenDischarge,
}


async def _tools():
    async with Client(mcp) as client:
        return {tool.name: tool for tool in await client.list_tools()}


@pytest.mark.asyncio
async def test_every_tool_has_a_description_that_says_what_it_does():
    for name, tool in (await _tools()).items():
        assert tool.description, name
        # de eerste regel komt van auto_docstring en moet de maatregel benoemen
        first_line = tool.description.splitlines()[0]
        assert len(first_line) > 30, f"{name}: {first_line!r}"
        assert "water" in first_line.lower(), f"{name}: {first_line!r}"


@pytest.mark.asyncio
async def test_argument_schema_is_nested_under_input():
    """De tools nemen één argument `input` met het volledige model erin."""
    for name, tool in (await _tools()).items():
        schema = tool.inputSchema
        assert set(schema["properties"]) == {"input"}, name
        assert "properties" in schema["properties"]["input"], name


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", sorted(TOOL_INPUT_MODELS))
async def test_argument_schema_matches_the_pydantic_model(tool_name):
    """Elk veld van het invoermodel komt in het schema terecht, met beschrijving."""
    tool = (await _tools())[tool_name]
    schema_fields = tool.inputSchema["properties"]["input"]["properties"]
    model_fields = TOOL_INPUT_MODELS[tool_name].model_fields

    assert set(schema_fields) == set(model_fields), tool_name
    without_description = [
        field for field, spec in schema_fields.items() if not spec.get("description")
    ]
    assert not without_description, f"{tool_name}: {without_description}"


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", sorted(TOOL_INPUT_MODELS))
async def test_constrained_fields_state_their_allowed_values(tool_name):
    """De toegestane waarden staan in de beschrijving, zodat een model ze kan lezen.

    Ze staan er als tekst en niet als JSON-Schema `enum`; zie de opmerking in
    test_allowed_values_are_prose_not_schema.
    """
    tool = (await _tools())[tool_name]
    fields = tool.inputSchema["properties"]["input"]["properties"]
    for field, expected in (
        ("return_period", "0.5"),
        ("time_of_year", "winter"),
        ("length_event_hrs", "48.0"),
        ("rainfall_regime", "LL"),
        ("name_rainfall_pattern", "p1c"),
        ("days_to_discharge", "2"),
    ):
        assert expected in fields[field]["description"], f"{tool_name}.{field}"


@pytest.mark.asyncio
async def test_units_are_in_the_field_descriptions():
    """Zonder eenheid is een getal onbruikbaar; die hoort in de beschrijving."""
    tool = (await _tools())["calculate_store_given_h"]
    fields = tool.inputSchema["properties"]["input"]["properties"]
    assert "m3/s" in fields["discharge_capacity_m3_per_sec"]["description"]
    assert "hectare" in fields["area_ha"]["description"].lower()
    assert "meters" in fields["delta_h_available"]["description"]


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", sorted(TOOL_INPUT_MODELS))
async def test_the_example_in_the_description_is_actually_accepted(tool_name):
    """Het voorbeeld moet werken als je het letterlijk overneemt.

    Eerder werd het voorbeeld gegenereerd uit de veldtypes: "example_value" voor elke
    string en 10 voor elk getal. Dat leverde zes ongeldige velden op en de tool wees het
    af - een LLM die het overnam kreeg dus een foutmelding. De voorbeelden zijn nu
    vastgelegd in `model_config` van de invoermodellen, en deze test bewijst dat ze
    geldig zijn.
    """
    setup_dot_env()
    tool = (await _tools())[tool_name]
    match = re.search(r"```json\n(.*?)\n```", tool.description, re.S)
    assert match, f"{tool_name} heeft geen voorbeeld in de beschrijving"

    example = json.loads(match.group(1))
    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, example)
    assert result.content


@pytest.mark.asyncio
async def test_output_fields_are_documented_in_the_description():
    """De uitvoervelden staan in de beschrijving, inclusief de statusbetekenis."""
    description = (await _tools())["calculate_store_given_h"].description
    for expected in (
        "state_before",
        "state_after",
        "dh_reduction_m",
        "feasible_dh_min_m",
        "cost",
        "no_measure_needed",  # de betekenis van status, niet alleen de naam
        "infeasible",
    ):
        assert expected in description, expected


@pytest.mark.asyncio
async def test_no_field_is_left_undocumented_in_the_description():
    """`No description provided` betekent dat een veld zonder uitleg doorkomt."""
    for name, tool in (await _tools()).items():
        assert "No description provided" not in tool.description, name
        assert "unknown," not in tool.description, name


@pytest.mark.asyncio
async def test_allowed_values_are_prose_not_schema():
    """Vastleggen dat de beperkingen nog niet als `enum` in het schema staan.

    De toegestane waarden zitten in de veldbeschrijving en worden afgedwongen door
    validators. Een MCP-client kan ze daardoor niet valideren en een model dat op het
    schema gestuurd wordt kan nog steeds een ongeldige waarde genereren.

    Zouden de velden `Literal[...]` worden, dan zet pydantic ze als `enum` in het schema
    en valideert het native. Deze test valt dan om, en dat is het signaal dat de
    verbetering is doorgevoerd - niet dat er iets stuk is.
    """
    fields = (await _tools())["calculate_store_given_h"].inputSchema["properties"][
        "input"
    ]["properties"]
    constrained = ("time_of_year", "rainfall_regime", "length_event_hrs", "days_to_discharge")
    assert not any("enum" in fields[field] for field in constrained)
