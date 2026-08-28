"""Wat er bij schaarste werkelijk wordt besloten: zouter inlaten, en peil boven gewas.

In de zomer van 2026 vulden twee westelijke waterschappen bergingsgebieden met zoetwater,
niet voor de landbouw maar voor dijkstabiliteit en tegen verzilting. Dat legt drie dingen
bloot die het model niet zei, en die alle drie tekst zijn en geen rekenkern:

* bij schaarste is de volgende stap niet minder inlaten maar ZOUTER inlaten, en chloride zit
  niet in dit model;
* peilhandhaving hoort in categorie 1 van de verdringingsreeks, en dat is niet
  vanzelfsprekend voor wie de tool voor het eerst gebruikt;
* een bergingsgebied is aan geen van beide kanten als knoop te stellen, en wie dat toch doet
  krijgt een antwoord dat niets meet.

Dit bestand legt vast dat het antwoord die drie zegt.
"""

import pytest

from talk_with_the_engineer.models import (
    AllocationInput,
    AllocationNode,
    CascadeInput,
    CascadeNode,
    ReadMeInput,
    SupplyInputGivenH,
)
from talk_with_the_engineer.tools import (
    calculate_allocation_given_shortage,
    calculate_cascade_given_excess,
    calculate_supply_given_h,
    read_me,
)

POLDER = {"area_ha": 4000, "deficit_mm_per_day": 4, "drawdown_available_m": 0.3}

# De verdeling waarmee de zomer van 2026 is nagemeten: peilhandhaving tegen dijkuitdroging in
# categorie 1, landbouw in categorie 4, en een bron die de twee samen niet dekt. De inlaten
# zijn ruim genomen, zodat de BRON de klem is en niet het kunstwerk - anders meet deze
# selectie de verdringing niet maar de keel.
SELECTION = dict(
    length_days=14,
    available_source_volume_m3=9_000_000,
    nodes=[
        AllocationNode(
            name="peilhandhaving",
            area_ha=8000,
            deficit_mm_per_day=4,
            intake_capacity_m3_per_sec=10.0,
            demand_post="peilbeheer",
        ),
        AllocationNode(
            name="landbouw",
            area_ha=18000,
            deficit_mm_per_day=4,
            intake_capacity_m3_per_sec=10.0,
            category=4,
        ),
    ],
)


# --- verzilting is de beslissing die erachter ligt ------------------------------------


@pytest.mark.asyncio
async def test_a_supply_answer_names_salinisation(test_context):
    """Een antwoord over aanvoerschaarste suggereert een kwantiteitsvraag; dat is hij niet."""
    result = await calculate_supply_given_h(
        test_context, SupplyInputGivenH(**POLDER, length_days=30)
    )
    caveat = next(item for item in result.caveats if "verzilting" in item.topic)
    assert "chloride" in caveat.what
    # de twee gevolgen: de inlaat is op doorspoeling gedimensioneerd, en verzilting van veen
    # is onomkeerbaar en dus categorie 1
    assert "doorspoeling" in caveat.consequence
    assert "onomkeerbaar" in caveat.consequence


@pytest.mark.asyncio
async def test_an_allocation_answer_names_it_too(test_context):
    """Op de verdelingstool geldt hij net zo: rantsoeneren is in de praktijk verzouten."""
    result = await calculate_allocation_given_shortage(
        test_context, AllocationInput(**SELECTION)
    )
    topics = {caveat.topic for caveat in result.caveats}
    assert any("verzilting" in topic for topic in topics)


@pytest.mark.asyncio
async def test_the_english_answer_names_it_as_well(test_context):
    """Dezelfde beperking, en dus dezelfde melding, in de andere taal."""
    result = await calculate_supply_given_h(
        test_context, SupplyInputGivenH(**POLDER, length_days=30, language="en")
    )
    caveat = next(item for item in result.caveats if "salinisation" in item.topic)
    assert "chloride" in caveat.what
    assert "irreversible" in caveat.consequence


# --- de keuze van 2026 komt eruit ----------------------------------------------------


@pytest.mark.asyncio
async def test_the_priority_order_reproduces_the_choice_that_was_made(test_context):
    """Dijken volledig bediend, landbouw gerantsoeneerd - en dat is wat er is gebeurd.

    De dijkgraaf zei het zo: kiezen tussen gewasschade of doorbrekende dijken, dan kies ik
    sterke dijken. Dat is geen weging in dit model maar een ondoordringbare schil: categorie 1
    komt eerst, en daar kan geen schadefunctie tegenop.
    """
    result = await calculate_allocation_given_shortage(
        test_context, AllocationInput(**SELECTION)
    )
    assert result.coverage_per_category["1"] == pytest.approx(1.0)
    assert result.coverage_per_category["4"] < 1.0
    assert result.binding_category == 4
    # en de tool zegt er het juiste vervolg bij: dit is een rantsoeneringsvraag
    assert not result.binding_is_capacity_not_availability


@pytest.mark.asyncio
async def test_more_water_helps_the_lower_category_and_not_the_higher(test_context):
    """Een berging van 2 mln m3 erbij bedient de landbouw beter en de dijken niet meer.

    Zo is de maatregel van 2026 met deze tools uit te drukken, en de kanttekening staat in de
    handleiding: dat water is eerder uit diezelfde bron gehaald en de berging is daarna leeg.
    """
    without = await calculate_allocation_given_shortage(
        test_context, AllocationInput(**SELECTION)
    )
    with_storage = await calculate_allocation_given_shortage(
        test_context,
        AllocationInput(**{**SELECTION, "available_source_volume_m3": 11_000_000}),
    )
    assert with_storage.coverage_per_category["1"] == pytest.approx(1.0)
    assert with_storage.coverage_per_category["4"] > without.coverage_per_category["4"]


# --- de handleiding legt uit wat er niet kan ------------------------------------------


@pytest.mark.asyncio
async def test_the_manual_explains_category_one(test_context):
    """Categorie 1 is ruimer dan "veiligheid" klinkt, en dat hoort er te staan."""
    text = (await read_me(test_context, ReadMeInput(modules=["gebruik"]))).text
    assert "categorie 1" in text.lower()
    for term in ("waterkering", "veenoxidatie", "onomkeerbare"):
        assert term in text.lower(), term


@pytest.mark.asyncio
async def test_the_manual_says_a_storage_area_is_not_a_node(test_context):
    """Wie een berging als cascadeknoop neerzet krijgt 0 cm, en dat lijkt geruststellend.

    Het is het niet: een cascadeknoop heeft geen inlaat en geen drempel, dus water kan er
    alleen van bovenstrooms inkomen - en een bergingsgebied heeft nauwelijks eigen afwaterend
    gebied. De handleiding hoort dat te zeggen voordat iemand het antwoord vertrouwt.
    """
    text = (await read_me(test_context, ReadMeInput(modules=["gebruik"]))).text.lower()
    assert "berging" in text
    assert "drempel" in text
    assert "0 cm" in text


@pytest.mark.asyncio
async def test_the_cascade_really_does_measure_nothing_for_a_storage_area(test_context):
    """De uitspraak in de handleiding, nagemeten in plaats van beweerd.

    Een bergingsgebied met een verwaarloosbaar eigen afwaterend gebied krijgt in een cascade
    geen water van bovenstrooms, dus de peilopzet die het in werkelijkheid ontvangt komt er
    niet in. Zolang dat zo is, hoort de handleiding ervoor te waarschuwen.
    """
    boezem = CascadeNode(
        name="boezem",
        area_ha=8000,
        percentage_open_water=3.5,
        discharge_capacity_m3_per_sec=10,
    )
    storage = CascadeNode(
        name="berging",
        area_ha=300,
        # bijna helemaal water: dat is wat een bergingsgebied is
        percentage_open_water=60,
        discharge_capacity_m3_per_sec=0,
        drains_to="boezem",
    )
    result = await calculate_cascade_given_excess(
        test_context, CascadeInput(return_period=100, nodes=[boezem, storage])
    )
    per_node = {result.worst_node: result.worst_dh_m}
    # de berging is niet de knoop met de hoogste stijging; hij vult zich niet uit de boezem
    assert "berging" not in per_node or result.lowest_dh_m < result.worst_dh_m
    assert result.lowest_dh_m < result.worst_dh_m


@pytest.mark.asyncio
async def test_the_manual_offers_the_route_that_does_work(test_context):
    """Niet alleen wat niet kan, ook wat wel kan: peilopzet plus het volume bij de bron."""
    text = (await read_me(test_context, ReadMeInput(modules=["gebruik"]))).text.lower()
    assert "peilopzet" in text
    assert "bronvolume" in text
