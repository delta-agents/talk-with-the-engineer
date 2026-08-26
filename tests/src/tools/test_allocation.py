"""De tiende tool: een verdelingsvraag over meerdere gebieden.

Wat hier wordt vastgelegd is niet de rekenkern - die staat in `test_allocate.py` en is daar
tegen een LP getoetst - maar de toolgrens: dat de graaf er niet over komt, dat het antwoord
leesbaar is, en dat het onderscheid tussen "de bron is de klem" en "de inlaten zijn de klem"
klopt. Dat laatste is het enige wat deze tool toevoegt aan een reeks losse aanvoervragen, en
het is precies wat een model per gebied niet kan zien.
"""

import pytest
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models import AllocationInput
from talk_with_the_engineer.models.modelset_rules_of_thumb.allocation import MAX_NODES
from talk_with_the_engineer.tools.toolset_rules_of_thumb.allocation import (
    calculate_allocation_given_shortage,
)

MILLION = 1e6

DRINKING_WATER = {
    "name": "drinkwaterinname",
    "area_ha": 500,
    "deficit_mm_per_day": 4,
    "category": 2,
    "intake_capacity_m3_per_sec": 1.0,
    "draws_from": "boezem",
}
IRRIGATION = {
    "name": "beregening",
    "area_ha": 800,
    "deficit_mm_per_day": 4,
    "category": 3,
    "intake_capacity_m3_per_sec": 0.6,
    "draws_from": "boezem",
}
FARMLAND = {
    "name": "landbouwpolder",
    "area_ha": 4000,
    "deficit_mm_per_day": 4,
    "category": 4,
    "intake_capacity_m3_per_sec": 1.5,
    "draws_from": "boezem",
}
BOEZEM = {
    "name": "boezem",
    "area_ha": 8000,
    "deficit_mm_per_day": 0,
    "category": 4,
    "intake_capacity_m3_per_sec": 10.0,
}
SELECTION = [DRINKING_WATER, IRRIGATION, FARMLAND, BOEZEM]


def _input(**overrides) -> AllocationInput:
    return AllocationInput(**{"nodes": SELECTION, "length_days": 30, **overrides})


@pytest.mark.asyncio
async def test_the_legal_order_shows_up_in_the_answer(test_context):
    """Drie miljoen kuub over een vraag van 6,36: landbouw draagt het hele tekort."""
    result = await calculate_allocation_given_shortage(
        test_context, _input(available_source_volume_m3=3 * MILLION)
    )

    assert result.coverage_per_category["2"] == pytest.approx(1.0)
    assert result.coverage_per_category["3"] == pytest.approx(1.0)
    assert result.coverage_per_category["4"] < 0.5
    assert result.binding_category == 4
    assert result.total_granted_m3 == pytest.approx(3 * MILLION)


@pytest.mark.asyncio
async def test_the_answer_says_whether_more_water_would_help(test_context):
    """Het onderscheid dat een model per gebied niet kan maken.

    Bij een krappe bron is het een rantsoeneringsvraag; bij een ruime bron zijn de inlaten
    de klem en helpt meer water niets - dan is het een kunstwerkvraag. Twee verschillende
    adviezen, en de eenpolder-aanvoertools moeten het eerste aannemen omdat ze de bron niet
    zien.
    """
    scarce = await calculate_allocation_given_shortage(
        test_context, _input(available_source_volume_m3=3 * MILLION)
    )
    assert not scarce.binding_is_capacity_not_availability
    assert "bron is de klem" in scarce.description

    plenty = await calculate_allocation_given_shortage(
        test_context, _input(available_source_volume_m3=20 * MILLION)
    )
    assert plenty.binding_is_capacity_not_availability
    assert "inlaten zijn de klem" in plenty.description
    assert "grotere inlaat" in plenty.description


@pytest.mark.asyncio
async def test_an_unlimited_source_reproduces_the_capacity_limited_answer(test_context):
    """Zonder bronvolume is de inlaat de enige grens - de aanname van de aanvoertools.

    Dat is het anker uit WP14.2: laat je het volume weg, dan is dit dezelfde vraag als een
    reeks losse aanvoervragen, en dan hoort er hetzelfde uit te komen.
    """
    unlimited = await calculate_allocation_given_shortage(test_context, _input())
    plenty = await calculate_allocation_given_shortage(
        test_context, _input(available_source_volume_m3=1000 * MILLION)
    )

    assert unlimited.theta is None
    assert unlimited.total_granted_m3 == pytest.approx(plenty.total_granted_m3)
    assert unlimited.binding_is_capacity_not_availability
    # De dekking van de bindende categorie mag er staan; de AANBOD-fractie niet. "bij 314 %
    # van die vraag als aanbod" leest als een fout terwijl het betekent dat de bron ruim is.
    assert "als aanbod" not in unlimited.description
    assert "als aanbod" not in plenty.description
    # bij een krappe bron staat hij er juist wel
    scarce = await calculate_allocation_given_shortage(
        test_context, _input(available_source_volume_m3=3 * MILLION)
    )
    assert "als aanbod" in scarce.description


@pytest.mark.asyncio
async def test_the_staircase_is_in_the_output_and_is_readable(test_context):
    """De trap is de uitlezing, en hij is begrensd: een handvol treden, geen sweep."""
    result = await calculate_allocation_given_shortage(
        test_context, _input(available_source_volume_m3=3 * MILLION)
    )

    assert 2 <= len(result.theta_steps) <= 12, len(result.theta_steps)
    assert result.theta_steps[0].theta_low == pytest.approx(0.0)
    assert result.theta_steps[-1].theta_high == pytest.approx(1.0)
    # de dekking is continu over de treden
    for lower, upper in zip(result.theta_steps, result.theta_steps[1:]):
        assert lower.theta_high == pytest.approx(upper.theta_low)
    # en bij het laagste aanbod krijgt de laagste categorie niets
    assert result.theta_steps[0].coverage_at_high["4"] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_a_step_reports_both_ends_and_says_which_one_you_are_on(test_context):
    """De trede tegensprak het hoofdantwoord, en de caveat moedigde aan hem te gebruiken.

    Er stond per trede één `coverage`, en dat was de dekking op de BOVENgrens. Een beller
    die zijn theta in de trap opzocht - wat de caveat letterlijk aanraadt - las daardoor de
    dekking van de bovenkant van zijn trede in plaats van die bij zijn eigen aanbod: 81 %
    waar 22 % het antwoord was, in een verdelingsvraag met juridische lading.

    Nu staan beide randen erin, is de trede waar het aanbod in valt gemarkeerd, en ligt het
    hoofdantwoord daar per constructie tussenin.
    """
    result = await calculate_allocation_given_shortage(
        test_context, _input(available_source_volume_m3=3 * MILLION)
    )

    current = [step for step in result.theta_steps if step.contains_current_theta]
    assert len(current) == 1
    step = current[0]
    assert step.theta_low <= result.theta <= step.theta_high

    for category, coverage in result.coverage_per_category.items():
        low = step.coverage_at_low[category]
        high = step.coverage_at_high[category]
        assert min(low, high) - 1e-9 <= coverage <= max(low, high) + 1e-9, category


@pytest.mark.asyncio
async def test_an_unlimited_source_marks_no_step_as_current(test_context):
    """Zonder aanbod is er geen punt op de as, en dan wijst de trap ook niets aan."""
    result = await calculate_allocation_given_shortage(test_context, _input())
    assert result.theta is None
    assert not any(step.contains_current_theta for step in result.theta_steps)


@pytest.mark.asyncio
async def test_a_step_does_not_carry_the_input_language(test_context):
    """`language` hoort bij een aanroep en niet bij een resultaatobject."""
    result = await calculate_allocation_given_shortage(
        test_context, _input(available_source_volume_m3=3 * MILLION)
    )
    assert "language" not in result.model_dump()["theta_steps"][0]


@pytest.mark.asyncio
async def test_the_text_does_not_sell_equal_sharing_as_the_law(test_context):
    """De reeks ordent de categorieen; gelijk verdelen binnen een schil is onze keuze.

    Art. 3.14 Bkl noemt binnen categorie 3 en 4 minimalisatie van de economische
    maatschappelijke schade. Gelijk tekort is wat je doet als je die schadefuncties niet
    kent, en dat verschil weglaten zou dezelfde fout zijn als een puntoptimum melden zonder
    het gebied eromheen.
    """
    result = await calculate_allocation_given_shortage(
        test_context, _input(available_source_volume_m3=3 * MILLION)
    )

    # de zin zegt expliciet dat de wet binnen een categorie niet kiest, en waar hij dan wel
    # naar wijst. Welke van de twee formuleringen er staat hangt af van of er iets te kiezen
    # valt - is alles gedekt, dan is er geen band en staat er "modelkeuze"
    assert "wet" in result.description
    assert "schade" in result.description
    assert (
        "De wet kiest daartussen niet" in result.description
        or "modelkeuze" in result.description
    )
    topics = {caveat.topic for caveat in result.caveats}
    assert "verdeling binnen een categorie" in topics
    assert "herkomst van het bronvolume" in topics


@pytest.mark.asyncio
async def test_an_omitted_period_is_assumed_and_reported(test_context):
    """`length_days` heeft een fallback, dus weglaten mag - en dan staat het in `assumptions`."""
    result = await calculate_allocation_given_shortage(
        test_context,
        AllocationInput(nodes=SELECTION, available_source_volume_m3=3 * MILLION),
    )

    assert [a.field for a in result.assumptions] == ["length_days"]
    assert result.total_demand_m3 > 0


@pytest.mark.asyncio
async def test_a_source_outside_the_selection_is_rejected_with_a_retry(test_context):
    """Dezelfde vangrail als bij de systeemvraag: geen halve graaf."""
    with pytest.raises(ModelRetry, match="niet in de selectie"):
        await calculate_allocation_given_shortage(
            test_context,
            _input(nodes=[{**FARMLAND, "draws_from": "nergens"}]),
        )


@pytest.mark.asyncio
async def test_a_selection_without_demand_is_refused_instead_of_answered(test_context):
    """Zonder vraag is er niets te verdelen, en nul gedeeld door nul is geen antwoord."""
    with pytest.raises(ModelRetry, match="niets te verdelen"):
        await calculate_allocation_given_shortage(
            test_context, _input(nodes=[{**BOEZEM, "draws_from": None}])
        )


def test_the_selection_is_bounded_so_the_graph_stays_out_of_the_call():
    """8500 afnemers passen in de rekenkern maar niet in een toolaanroep.

    Zelfde grens en zelfde reden als `CascadeInput`: een graaf is precies wat een LLM slecht
    kan produceren en goed kan verzinnen.
    """
    too_many = [
        {**FARMLAND, "name": f"polder{index}", "draws_from": None}
        for index in range(MAX_NODES + 1)
    ]
    with pytest.raises(ValueError):
        AllocationInput(nodes=too_many, length_days=30)


@pytest.mark.asyncio
async def test_the_output_reports_the_band_and_not_one_split(test_context):
    """Hoeveel water er omgaat is een modeluitkomst; wie het krijgt is een beleidskeuze.

    Twee afnemers van heel verschillende grootte in categorie 4. Beide verdedigbare
    verdelingen binnen een schil gebruiken exact hetzelfde volume - het categorietotaal is
    identiek - maar gelijk tekort legt het tekort proportioneel neer en maximin bij de
    grootste vrager. De wet kiest daartussen niet, dus mag de uitvoer dat ook niet doen.

    Dat is dezelfde discipline als het maatregelgebied uit #30: meld de band, niet het punt.
    """
    result = await calculate_allocation_given_shortage(
        test_context,
        _input(
            available_source_volume_m3=3 * MILLION,
            nodes=[
                DRINKING_WATER,
                {**FARMLAND, "name": "grote_landbouw", "area_ha": 4000},
                {**FARMLAND, "name": "kleine_landbouw", "area_ha": 400},
                BOEZEM,
            ],
        ),
    )

    low, high = result.individual_coverage_range_per_category["4"]
    assert low < result.coverage_per_category["4"] < high, (low, high)
    assert high == pytest.approx(1.0)
    # de band staat ook in de zin, want dat is wat er wordt voorgelezen
    assert "wie het krijgt wel" in result.description
    assert f"{low:.0%}" in result.description
    # en categorie 2 is volledig gedekt, dus daar is geen band
    assert result.individual_coverage_range_per_category["2"] == pytest.approx(
        [1.0, 1.0]
    )
