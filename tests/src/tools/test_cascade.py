"""De systeemvraag: één tool die meer dan één gebied aanneemt.

Wat hier wordt vastgelegd is vooral wat de tool NIET doet: geen rij per gebied, geen graaf
als uitvoer, en een harde bovengrens op de selectie. De rekenkern doet 8500 knopen in 65 ms;
de toolgrens is begrensd door wat leesbaar is en niet door wat rekenbaar is.
"""

import pytest
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models import CascadeInput, CascadeNode
from talk_with_the_engineer.models.modelset_rules_of_thumb.cascade import MAX_NODES
from talk_with_the_engineer.tools import calculate_cascade_given_excess

STORM = {
    "return_period": 1000,
    "time_of_year": "winter",
    "length_event_hrs": 96.0,
    "name_rainfall_pattern": "p1a",
    "days_to_discharge": 4,
    "rainfall_regime": "R",
}


def _node(name, drains_to=None, head_max=None, area_ha=4000, capacity=5.0):
    return {
        "name": name,
        "area_ha": area_ha,
        "percentage_open_water": 3.5,
        "discharge_capacity_m3_per_sec": capacity,
        "drains_to": drains_to,
        "head_max_m": head_max,
    }


def _chain(length, head_max=None):
    names = [f"n{index}" for index in range(length)]
    return [
        _node(
            names[index],
            drains_to=None if index == length - 1 else names[index + 1],
            head_max=head_max,
        )
        for index in range(length)
    ]


@pytest.mark.asyncio
async def test_a_single_area_matches_the_polder_tools(test_context):
    """Eén gebied dat op de buitenwereld loost is gewoon de polder."""
    result = await calculate_cascade_given_excess(
        test_context, CascadeInput(**STORM, nodes=[_node("A")])
    )
    assert result.node_count == 1
    assert result.depth == 1
    assert result.worst_node == "A"
    assert result.worst_dh_m == pytest.approx(1.8057576857142845, abs=1e-9)
    assert result.coupling_effect_m == pytest.approx(0.0, abs=1e-12)
    assert result.binding_node is None


@pytest.mark.asyncio
async def test_the_coupling_effect_is_the_water_that_comes_from_upstream(test_context):
    """Het getal dat een model per gebied niet kan zien.

    Drie gebieden in een ketting: de middelste krijgt de uitstroom van de bovenste erbij, en
    dat is precies het verschil met hem los rekenen. Zonder dit getal lijkt afvoeren
    goedkoper dan het voor het systeem als geheel is.
    """
    result = await calculate_cascade_given_excess(
        test_context, CascadeInput(**STORM, nodes=_chain(3))
    )
    assert result.node_count == 3
    assert result.depth == 3
    assert result.coupling_effect_m > 1.0
    assert "komt er van bovenstrooms bij" in result.description


@pytest.mark.asyncio
async def test_derating_names_the_node_where_the_coupling_pinches(test_context):
    """De bindende knoop, en hoeveel van zijn vermogen op het beslissende uur wegvalt.

    Je betaalt voor geinstalleerd vermogen en je krijgt effectief vermogen, en die twee
    lopen juist bij de maatgevende gebeurtenis uiteen. Dat is de kern van de cascade, en het
    hoort dus in het antwoord en niet in een reeks die niemand opvraagt.
    """
    free = await calculate_cascade_given_excess(
        test_context, CascadeInput(**STORM, nodes=_chain(4))
    )
    derated = await calculate_cascade_given_excess(
        test_context, CascadeInput(**STORM, nodes=_chain(4, head_max=1.5))
    )

    assert free.binding_node is None
    assert free.iterations == 0

    assert derated.binding_node is not None
    assert derated.blocked_capacity_fraction > 0.5
    assert derated.iterations > 0
    assert derated.converged
    assert "De koppeling knelt bij" in derated.description


@pytest.mark.asyncio
async def test_the_output_is_aggregates_and_not_a_row_per_area(test_context):
    """Bij vijftig knopen is een rij per knoop niet meer leesbaar, en de vraag is nooit
    "geef me alle standen" maar "waar zit het probleem"."""
    result = await calculate_cascade_given_excess(
        test_context, CascadeInput(**STORM, nodes=_chain(10))
    )
    dumped = result.model_dump()
    # geen lijst met een element per gebied
    assert not [
        key
        for key, value in dumped.items()
        if isinstance(value, list) and len(value) >= result.node_count
    ]
    assert result.lowest_dh_m <= result.median_dh_m <= result.worst_dh_m


@pytest.mark.asyncio
async def test_a_selection_larger_than_the_bound_is_refused(test_context):
    """Een harde grens en geen stille afkap: afkappen leest als "alles gedekt"."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CascadeInput(**STORM, nodes=_chain(MAX_NODES + 1))


@pytest.mark.asyncio
async def test_draining_to_an_area_outside_the_selection_is_a_model_retry(test_context):
    """Een verwijzing naar iets dat er niet is, is een uitleg en geen KeyError."""
    with pytest.raises(ModelRetry, match="zit niet"):
        await calculate_cascade_given_excess(
            test_context,
            CascadeInput(**STORM, nodes=[_node("A", drains_to="de zee")]),
        )


@pytest.mark.asyncio
async def test_a_cycle_is_refused_with_an_explanation(test_context):
    with pytest.raises(ModelRetry, match="afwateringssysteem"):
        await calculate_cascade_given_excess(
            test_context,
            CascadeInput(
                **STORM,
                nodes=[_node("A", drains_to="B"), _node("B", drains_to="A")],
            ),
        )


@pytest.mark.asyncio
async def test_duplicate_names_are_refused(test_context):
    """En met een melding, niet met een validatiedump.

    Een `ValidationError` zou hier de hele knopenlijst en een link naar errors.pydantic.dev
    in het antwoord zetten; een `ModelRetry` komt er onverpakt uit. Zie
    `CascadeInput.names_are_unique`.
    """
    with pytest.raises(ModelRetry, match="uniek") as refusal:
        CascadeInput(**STORM, nodes=[_node("A"), _node("A")])

    assert "'A'" in str(refusal.value)
    assert "pydantic" not in str(refusal.value)


@pytest.mark.asyncio
async def test_a_bare_call_still_reports_its_assumptions(test_context):
    """De systeemvraag erft de aannamemelding van de bui; die verdwijnt niet op schaal."""
    result = await calculate_cascade_given_excess(
        test_context, CascadeInput(return_period=100, nodes=_chain(3))
    )
    assert "Aangenomen omdat ze niet zijn opgegeven" in result.description


@pytest.mark.asyncio
async def test_the_coupling_law_is_reported_as_an_open_question(test_context):
    """De richting van het cascade-effect is robuust, de grootte hangt aan V6.

    Dus hoort die vraag in het antwoord te staan zodra er een koppelingswet in het spel is -
    en niet als er geen terugkoppeling is, want dan bestaat hij niet.
    """
    derated = await calculate_cascade_given_excess(
        test_context, CascadeInput(**STORM, nodes=_chain(3, head_max=1.5))
    )
    free = await calculate_cascade_given_excess(
        test_context, CascadeInput(**STORM, nodes=_chain(3))
    )
    assert "koppelingswet tussen gebieden" in {c.topic for c in derated.caveats}
    assert "koppelingswet tussen gebieden" not in {c.topic for c in free.caveats}


# --- de peilband van een knoop -----------------------------------------------------


def _two_node_input(**overrides):
    """Polder A loost op een boezem; de overrides gaan naar polder A."""
    return CascadeInput(
        return_period=100,
        nodes=[
            CascadeNode(
                name="polder A",
                area_ha=4000,
                percentage_open_water=3.5,
                discharge_capacity_m3_per_sec=5,
                drains_to="boezem",
                **overrides,
            ),
            CascadeNode(
                name="boezem",
                area_ha=8000,
                percentage_open_water=3.5,
                discharge_capacity_m3_per_sec=10,
            ),
        ],
    )


@pytest.mark.asyncio
async def test_a_node_without_a_level_band_answers_exactly_as_before(test_context):
    """De peilband staat standaard op nul, dus bestaande antwoorden veranderen niet.

    Dit is de regressietoets bij het toevoegen van de twee velden: wie ze weglaat krijgt de
    doorrekening die er altijd al was.
    """
    result = await calculate_cascade_given_excess(test_context, _two_node_input())
    explicit = await calculate_cascade_given_excess(
        test_context, _two_node_input(target_level_rise_m=0.0, level_margin_m=0.0)
    )

    assert result.worst_dh_m == pytest.approx(explicit.worst_dh_m, abs=1e-12)
    assert result.lowest_dh_m == pytest.approx(explicit.lowest_dh_m, abs=1e-12)


@pytest.mark.asyncio
async def test_raising_a_node_raises_its_own_reported_rise(test_context):
    """Peilopzet telt mee in de stijging, want die wordt boven het OORSPRONKELIJKE peil gemeten.

    Zonder deze optelling zou peilopzet in de cascade gratis zijn: hij verlaagt de stijging
    boven het opgezette peil en de opgesnoepte marge zou nergens te zien zijn. Polder A is
    hier de laagste knoop, dus het effect komt in `lowest_dh_m` terug - exact de opzet.
    """
    plain = await calculate_cascade_given_excess(test_context, _two_node_input())
    raised = await calculate_cascade_given_excess(
        test_context, _two_node_input(target_level_rise_m=0.20)
    )

    assert raised.lowest_dh_m - plain.lowest_dh_m == pytest.approx(0.20, abs=1e-9)
    # de boezem staat niet hoger en blijft dus de zwaarste knoop
    assert raised.worst_node == plain.worst_node == "boezem"
    assert raised.worst_dh_m == pytest.approx(plain.worst_dh_m, abs=1e-9)


@pytest.mark.asyncio
async def test_prerelease_upstream_arrives_downstream(test_context):
    """Voorbemaling bovenstrooms maakt het benedenstrooms drukker, en dat hoort zichtbaar.

    Polder A die 30 cm mag voormalen loost eerder en meer op de boezem, dus de piek van de
    boezem gaat OMHOOG. Dat is precies het soort effect waarvoor de cascade bestaat: per
    gebied gerekend zou je het niet zien.
    """
    plain = await calculate_cascade_given_excess(test_context, _two_node_input())
    prerelease = await calculate_cascade_given_excess(
        test_context, _two_node_input(level_margin_m=0.30)
    )

    assert prerelease.worst_node == "boezem"
    assert prerelease.worst_dh_m > plain.worst_dh_m


@pytest.mark.asyncio
async def test_a_raised_node_says_what_the_coupling_does_not_do(test_context):
    """De opvoerhoogte tussen twee gebieden verandert niet mee, en dat hoort erbij te staan.

    Een gebied dat 20 cm hoger staat pompt in werkelijkheid tegen 20 cm minder verval naar
    beneden. Dat verschil in nulpunt zit niet in de doorrekening, dus het hoort in `caveats`
    en niet in stilte.
    """
    plain = await calculate_cascade_given_excess(test_context, _two_node_input())
    raised = await calculate_cascade_given_excess(
        test_context, _two_node_input(target_level_rise_m=0.20)
    )

    assert not any("peilopzet" in caveat.topic for caveat in plain.caveats)
    assert any("peilopzet" in caveat.topic for caveat in raised.caveats)
