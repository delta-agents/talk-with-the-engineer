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
async def test_the_description_stays_within_its_budget():
    """Kort genoeg om niet afgekapt te worden door een comprimerende client.

    De vorige generator zette de hele parameterlijst in de description, liep op tot 5600
    tekens en verloor daar juist het verplichte `delta_h_available` mee.
    """
    from talk_with_the_engineer.utils.docstring_generator import MAX_DESCRIPTION_CHARS

    for name, tool in (await _tools()).items():
        assert len(tool.description) <= MAX_DESCRIPTION_CHARS, (
            f"{name}: {len(tool.description)} tekens"
        )


@pytest.mark.asyncio
async def test_the_description_asks_for_omission_and_names_no_values():
    """De description is een instructie, geen documentatie.

    Deze test eiste eerder het omgekeerde: `percentage_open_water=2` moest erin staan,
    zodat de waarde ook een client bereikte die het schema uitkleedt. Gemeten gevolg: een
    agent nam dat rijtje veld=waarde over in zijn aanroep. Daarmee was server-side elk
    veld opgegeven, bleef `assumptions` bij elke aanroep leeg, en las het antwoord de
    standaardwaarden voor als gekozen invoer.

    De waarden horen dus in het schema en in het antwoord; hier alleen de gedragsregel.
    """
    from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
        FIELD_FALLBACKS,
    )

    for name, tool in (await _tools()).items():
        assert "assumptions" in tool.description, name
        assert "laat het weg" in tool.description, name

        spelled_out = [
            f"{field}={value}"
            for field, value in FIELD_FALLBACKS.items()
            if f"{field}={value}" in tool.description
        ]
        assert not spelled_out, f"{name}: {spelled_out}"


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", sorted(TOOL_INPUT_MODELS))
async def test_the_example_is_the_minimal_call(tool_name):
    """Het voorbeeld doet weglaten voor, niet invullen.

    Het was een volledig gevulde aanroep, met een test eronder die bewees dat hij
    letterlijk werkt - dus expliciet bedoeld om overgenomen te worden. Daarmee modelleerde
    het precies het gedrag dat `assumptions` onmogelijk maakt. Wat een veld mag bevatten
    staat in de `enum` van het schema en niet in het voorbeeld.
    """
    from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
        FIELD_FALLBACKS,
    )

    tool = (await _tools())[tool_name]
    match = re.search(r"```json\n(.*?)\n```", tool.description, re.S)
    assert match, tool_name

    example = json.loads(match.group(1))["input"]
    assert not set(example) & set(FIELD_FALLBACKS), tool_name


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
async def test_constrained_fields_carry_their_enum_in_the_schema(tool_name):
    """De toegestane waarden staan in het schema, niet alleen in de beschrijving.

    Daarmee kan een MCP-client ze valideren en kan een model dat op het schema gestuurd
    wordt geen ongeldige waarde meer genereren. Eerder stonden ze als tekst in de
    veldbeschrijving en werden ze door eigen validators afgedwongen.
    """
    tool = (await _tools())[tool_name]
    fields = tool.inputSchema["properties"]["input"]["properties"]
    for field, expected in (
        (
            "return_period",
            [
                0.5,
                1.0,
                2.0,
                5.0,
                10.0,
                20.0,
                25.0,
                50.0,
                100.0,
                200.0,
                250.0,
                500.0,
                1000.0,
            ],
        ),
        ("time_of_year", ["winter", "summer"]),
        ("length_event_hrs", [48.0, 96.0, 192.0]),
        ("rainfall_regime", ["LL", "L", "R", "H"]),
        ("name_rainfall_pattern", ["p_0", "p1a", "p1b", "p1c", "p1d", "p2a", "p2b"]),
        ("days_to_discharge", [2, 3, 4]),
        ("language", ["nl", "en"]),
    ):
        assert fields[field]["enum"] == expected, f"{tool_name}.{field}"


@pytest.mark.asyncio
async def test_numeric_bounds_are_in_the_schema():
    """Ook de grenzen die geen opsomming zijn horen in het schema."""
    fields = (await _tools())["calculate_store_given_h"].inputSchema["properties"][
        "input"
    ]["properties"]
    assert fields["percentage_open_water"]["exclusiveMinimum"] == 0
    assert fields["percentage_open_water"]["maximum"] == 100


@pytest.mark.asyncio
async def test_units_are_in_the_field_descriptions():
    """Zonder eenheid is een getal onbruikbaar; die hoort in de beschrijving."""
    tool = (await _tools())["calculate_store_given_h"]
    fields = tool.inputSchema["properties"]["input"]["properties"]
    assert "m3/s" in fields["discharge_capacity_m3_per_sec"]["description"]
    assert "hectare" in fields["area_ha"]["description"].lower()
    assert "[m]" in fields["delta_h_available"]["description"]


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
async def test_output_fields_are_documented_in_the_output_schema():
    """De uitvoervelden staan in het uitvoerschema, inclusief de statusbetekenis.

    Deze stonden eerder als proza in de description, bijgeschreven door `auto_docstring`.
    Dat dupliceerde `outputSchema`, dat FastMCP toch al meestuurt, en blies de description
    op tot ruim 5600 tekens - waarna clients hem afkapten. Het schema is de bron.
    """
    output_schema = (await _tools())["calculate_store_given_h"].outputSchema
    for expected in (
        "state_before",
        "state_after",
        "dh_reduction_m",
        "feasible_dh_min_m",
        "cost",
    ):
        assert expected in output_schema["properties"], expected

    # de betekenis van status, niet alleen de veldnaam
    assert set(output_schema["properties"]["status"]["enum"]) == {
        "exact",
        "no_measure_needed",
        "infeasible",
    }


def _undocumented_fields(schema, path=""):
    """Elk pad naar een veld zonder `description`, recursief door geneste objecten."""
    missing = []
    for name, field in (schema.get("properties") or {}).items():
        where = f"{path}.{name}" if path else name
        if "description" not in field:
            missing.append(where)
        missing.extend(_undocumented_fields(field, where))
    return missing


@pytest.mark.asyncio
async def test_no_field_is_left_undocumented_in_the_schemas():
    """Een veld zonder beschrijving is een veld dat de lezer moet raden.

    Bewaakte eerder de description; die bevat de velden niet meer, dus de test zou
    voortaan altijd slagen zonder iets te controleren. Nu staat hij op de schema's zelf,
    in- en uitvoer.
    """
    for name, tool in (await _tools()).items():
        inputs = tool.inputSchema["properties"]["input"]
        assert not _undocumented_fields(inputs), f"{name} invoer"
        assert not _undocumented_fields(tool.outputSchema), f"{name} uitvoer"


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", sorted(TOOL_INPUT_MODELS))
async def test_the_fallback_fields_advertise_no_default(tool_name):
    """Geen `default` in het schema voor de velden die de tool zelf invult.

    Een geadverteerde standaardwaarde is precies wat een client in de aanroep zet voordat
    hij hem verstuurt - gemeten bij Claude Code - en dan weet de server niet meer wat de
    beller heeft weggelaten en blijft `assumptions` leeg. De waarde staat in de
    veldbeschrijving en in de tooldescription, waar hij niets kan veroorzaken.
    """
    from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
        FIELD_FALLBACKS,
    )

    fields = (await _tools())[tool_name].inputSchema["properties"]["input"][
        "properties"
    ]
    advertised = {
        field: fields[field]["default"]
        for field in FIELD_FALLBACKS
        if field in fields and "default" in fields[field]
    }
    assert not advertised, f"{tool_name}: {advertised}"


@pytest.mark.asyncio
async def test_the_assumptions_survive_the_mcp_transport():
    """Een kale aanroep over de echte transportlaag meldt zijn aannames.

    De andere tests in `test_uitlegbaarheid.py` bouwen het invoermodel in Python en kunnen
    per constructie niet zien wat er tussen client en server met de payload gebeurt - juist
    daar ging het mis.
    """
    setup_dot_env()
    from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
        FIELD_FALLBACKS,
    )

    bare = {
        "area_ha": 4000,
        "discharge_capacity_m3_per_sec": 5,
        "return_period": 100,
        "delta_h_available": 1.0,
    }
    async with Client(mcp) as client:
        result = await client.call_tool("calculate_store_given_h", {"input": bare})

    reported = {a["field"] for a in result.structured_content["assumptions"]}
    assert reported == set(FIELD_FALLBACKS) - {"days_to_retain_discharge"}
    assert (
        "Aangenomen omdat ze niet zijn opgegeven"
        in (result.structured_content["description"])
    )


@pytest.mark.asyncio
async def test_the_kind_of_optimum_says_which_quantity_it_is_about():
    """De veldnaam noemt de grootheid, want alleen de naam reist altijd mee.

    Het veld heette `optimum_kind` en stond in de uitvoer tussen `feasible_dh_min_m` en
    `dh_with_measure_m`, terwijl `magnitude_at_optimum_*` in `data` zit. Een agent las
    `upper_bound` daardoor als een uitspraak over de gevraagde waterstand: "de 1,00 m is
    hier een bovengrens". Dat is de verkeerde grootheid - het gaat over de maatvoering.
    Een beschrijving had dat ook kunnen rechtzetten, maar die haalt niet elke client door.
    """
    output_schema = (await _tools())["calculate_store_given_h"].outputSchema
    fields = output_schema["properties"]

    assert "magnitude_optimum_kind" in fields
    assert "optimum_kind" not in fields

    description = fields["magnitude_optimum_kind"]["description"]
    assert "magnitude_at_optimum" in description
    assert "feasible_dh_min_m" in description
