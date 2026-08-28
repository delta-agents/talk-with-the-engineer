"""De bodem als tweede voorraad: een voorraad, een plafond, en welke schakel knelt.

Wat hier wordt vastgelegd:

* weglaten verandert niets - bit voor bit het antwoord zonder bodem;
* de balans sluit met de bodem erin, en het plafond maakt van vraag geen minder vraag maar
  onvervulde vraag;
* de twee regimes komen er echt uit: met aanvoer is de bodem een doorgeefluik en telt het
  plafond, zonder aanvoer is het geleverde exact de voorraad;
* `binding_link` zegt welk advies erbij hoort, en slaat om als de traagste schakel omslaat;
* de tabel is intern consistent: geen plafond boven de capillaire grens waar het grondwater
  de bron is, en veen levert minder en korter dan zand.
"""

import pytest
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models import SupplyInputGivenH, SupplyInputGivenSupply
from talk_with_the_engineer.models.modelset_rules_of_thumb.soil import (
    CAPILLARY_LIMIT_MM_PER_DAY,
    SOIL_LINKS,
    SOIL_TYPE_NAMES,
    SOIL_TYPES,
)
from talk_with_the_engineer.tools import (
    calculate_supply_given_h,
    calculate_supply_given_supply,
)

POLDER = {
    "area_ha": 4000,
    "percentage_open_water": 3.5,
    "drawdown_available_m": 0.3,
}
LAND_FRACTION = 0.965
"""Het landaandeel van de referentiepolder; de tabel staat over land en het antwoord over de polder."""


# --- de tabel is intern consistent ----------------------------------------------------


@pytest.mark.parametrize("name", SOIL_TYPE_NAMES)
def test_every_area_type_names_a_link_that_exists(name):
    """Het plafond hoort bij een schakel, en die schakel hoort in het vocabulaire te staan."""
    body = SOIL_TYPES[name]
    assert body.binding_link in SOIL_LINKS
    assert body.transfer_mm_per_day == min(body.limits.values())
    assert body.store_mm > 0.0


@pytest.mark.parametrize("name", SOIL_TYPE_NAMES)
def test_the_ceiling_respects_the_capillary_limit(name):
    """Waar het grondwater de bron is, levert de bodem niet meer dan capillair mogelijk is.

    Het droogtegevoelige type is de uitzondering, en het is er een met een reden: daar staat
    het grondwater buiten capillair bereik en komt het water uit de wortelzone zelf. Dat is
    het enige type dat boven de grens mag liggen.
    """
    body = SOIL_TYPES[name]
    if name == "droogtegevoelig_zand":
        assert "bodem_naar_wortelzone" not in body.limits
        assert body.transfer_mm_per_day > CAPILLARY_LIMIT_MM_PER_DAY
    else:
        assert body.transfer_mm_per_day <= CAPILLARY_LIMIT_MM_PER_DAY


def test_peat_gives_the_least_and_sand_the_most():
    """De rangorde over de gebiedstypen, en die is de kern van de uitkomst.

    In veenweide is de bodemvoorraad KLEINER dan de open-waterbuffer die het model al kent -
    op de referentiepolder 10,5 mm bij 30 cm peilband. De winst zit op de zandgronden, en
    nergens anders.
    """
    peat = SOIL_TYPES["veenweide"]
    sand = SOIL_TYPES["zandgrond_zonder_slootinvloed"]
    assert peat.store_mm < sand.store_mm
    assert peat.transfer_mm_per_day < sand.transfer_mm_per_day

    open_water_buffer_mm = 0.30 * 0.035 * 1000
    assert peat.store_mm * LAND_FRACTION < open_water_buffer_mm
    assert sand.store_mm * LAND_FRACTION > open_water_buffer_mm


# --- weglaten verandert niets ---------------------------------------------------------


@pytest.mark.asyncio
async def test_leaving_the_soil_out_changes_nothing(test_context):
    """De regressietoets die de uitbreiding opt-in maakt.

    Een voorraad van nul verdiept de band niet en een oneindig plafond knijpt de vraag niet
    af, dus zonder gebiedstype hoort er tot op de bit hetzelfde uit te komen als uit een
    aanroep die de bodem niet kent.
    """
    plain = await calculate_supply_given_h(
        test_context,
        SupplyInputGivenH(**POLDER, deficit_mm_per_day=4, length_days=30),
    )
    assert plain.soil_store_mm is None
    assert plain.soil_supplied_mm is None
    assert plain.unreachable_mm is None
    assert plain.buffer_mm == pytest.approx(10.5, abs=0.01)
    assert plain.shortfall_mm == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_without_soil_the_caveat_still_says_surface_water_only(test_context):
    """Zolang de bodem er niet in zit, hoort het antwoord dat te zeggen."""
    plain = await calculate_supply_given_h(
        test_context,
        SupplyInputGivenH(**POLDER, deficit_mm_per_day=4, length_days=30),
    )
    topics = {caveat.topic for caveat in plain.caveats}
    assert "alleen oppervlaktewater" in topics
    assert not any("bodemvoorraad" in topic for topic in topics)


@pytest.mark.asyncio
async def test_with_soil_the_caveat_hands_over(test_context):
    """En zodra hij er wel in zit, is die tekst onwaar en neemt een andere hem over."""
    with_soil = await calculate_supply_given_h(
        test_context,
        SupplyInputGivenH(
            **POLDER,
            deficit_mm_per_day=4,
            length_days=30,
            soil_type="kleipolder",
        ),
    )
    topics = {caveat.topic for caveat in with_soil.caveats}
    assert "alleen oppervlaktewater" not in topics
    caveat = next(item for item in with_soil.caveats if "bodemvoorraad" in item.topic)
    # de twee richtingen waarin dit antwoord scheef staat, en ze staan tegenover elkaar
    assert "beregening" in caveat.consequence
    assert "te gunstig" in caveat.consequence


# --- de balans sluit, en het plafond is onvervulde vraag ------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("name", SOIL_TYPE_NAMES)
async def test_the_water_balance_closes_with_the_soil_in_it(test_context, name):
    """Vraag = geleverd + peilband + bodem + onvervuld, in elk gebiedstype.

    Dit is de toets die het plafond eerlijk houdt. Zou vraag die het plafond niet doorlaat
    stil van de vraag AF gaan in plaats van onvervuld te blijven, dan zou een trage bodem in
    de uitvoer als winst verschijnen en zou deze som niet sluiten.
    """
    result = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(
            **POLDER,
            deficit_mm_per_day=2,
            length_days=60,
            delta_supply_capacity_l_s_ha=0.4,
            soil_type=name,
        ),
    )
    total = (
        result.supplied_mm
        + result.buffer_mm
        + result.soil_supplied_mm
        + result.shortfall_mm
    )
    assert total == pytest.approx(result.demand_mm, rel=1e-9)
    # en het onbereikbare deel zit IN het tekort en niet ernaast
    assert result.unreachable_mm <= result.shortfall_mm + 1e-9


@pytest.mark.asyncio
async def test_the_ceiling_is_unmet_demand_and_not_less_demand(test_context):
    """Een plafond onder de vraag laat een deel van die vraag onvervuld, en zegt dat.

    Bij een tekort van 4 mm/dag en een veenplafond van 0,67 mm/dag over land komt ruim 80 %
    van de vraag niet bij het gewas. Dat is de uitspraak waar het om gaat, en hij hoort niet
    als een lagere vraag in de uitvoer te verschijnen.
    """
    result = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(
            **POLDER,
            deficit_mm_per_day=4,
            length_days=30,
            delta_supply_capacity_l_s_ha=0.4,
            soil_type="veenweide",
        ),
    )
    ceiling = SOIL_TYPES["veenweide"].transfer_mm_per_day
    expected = (4 - ceiling) * LAND_FRACTION * 30
    assert result.demand_mm == pytest.approx(4 * 30)
    assert result.unreachable_mm == pytest.approx(expected, rel=1e-6)
    assert result.binding_link == "sloot_naar_bodem"


@pytest.mark.asyncio
async def test_a_bigger_intake_does_not_beat_the_ceiling(test_context):
    """Knelt het plafond, dan verandert een grotere inlaat het antwoord niet.

    Dat is het hele verschil tussen een plafond en een keel, en het is het advies dat eraan
    hangt: hier helpt onderwaterdrainage of subirrigatie en geen kunstwerk.
    """
    common = dict(
        **POLDER,
        deficit_mm_per_day=4,
        length_days=30,
        soil_type="veenweide",
    )
    modest = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(**common, delta_supply_capacity_l_s_ha=0.4),
    )
    generous = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(**common, delta_supply_capacity_l_s_ha=4.0),
    )
    assert generous.shortfall_mm == pytest.approx(modest.shortfall_mm, rel=1e-9)
    assert generous.binding_link == modest.binding_link == "sloot_naar_bodem"


@pytest.mark.asyncio
async def test_the_sentence_stops_advising_what_does_not_help(test_context):
    """De zin die een lezer overneemt hoort hetzelfde te zeggen als `binding_link`.

    Bij een onhaalbaar doel adviseert de aanvoertool bergen of vasthouden, en dat is het
    juiste advies zolang de INLAAT de klem is. Knijpt de bodem de vraag af, dan helpt geen van
    beide: het water komt niet bij het gewas, en meer voorraad verandert daar niets aan.
    """
    with_ceiling = await calculate_supply_given_h(
        test_context,
        SupplyInputGivenH(
            **POLDER, deficit_mm_per_day=4, length_days=30, soil_type="veenweide"
        ),
    )
    assert "onderwaterdrainage" in with_ceiling.description
    assert "bergen of vasthouden" not in with_ceiling.description

    # en zonder plafond blijft het oorspronkelijke advies staan. Een tekort van 50 mm/dag
    # ligt boven wat de aanvoernorm-bovengrens van 5 l/s/ha levert, dus de INLAAT is daar de
    # klem en dan helpt een grotere voorraad wel degelijk.
    without = await calculate_supply_given_h(
        test_context,
        SupplyInputGivenH(
            area_ha=4000,
            percentage_open_water=3.5,
            drawdown_available_m=0.0,
            deficit_mm_per_day=50,
            length_days=30,
        ),
    )
    assert "bergen of vasthouden" in without.description


# --- de twee regimes ------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name", ["veenweide", "zandgrond_zonder_slootinvloed", "droogtegevoelig_zand"]
)
async def test_without_supply_the_soil_delivers_exactly_its_store(test_context, name):
    """Zonder aanvoer is het geleverde precies de voorraad, en niets meer.

    Geen peilband, geen inlaat, en een tekort onder het plafond zodat de voorraad en niet de
    snelheid de klem is. Dan hoort er uit de bodem te komen wat erin zat.
    """
    result = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(
            area_ha=4000,
            percentage_open_water=3.5,
            drawdown_available_m=0.0,
            deficit_mm_per_day=0.5,
            length_days=183,
            delta_supply_capacity_m3_per_sec=0.0,
            soil_type=name,
        ),
    )
    # een inlaat van nul levert nul, op de ruis van de cumulatieve som na
    assert result.supplied_mm == pytest.approx(0.0, abs=1e-9)
    assert result.buffer_mm == pytest.approx(0.0, abs=1e-9)
    assert result.soil_supplied_mm == pytest.approx(result.soil_store_mm, rel=1e-6)
    assert result.binding_link == "voorraad_op"


@pytest.mark.asyncio
async def test_with_supply_the_store_stays_put(test_context):
    """Met aanvoer is de bodem een doorgeefluik en blijft de voorraad staan.

    De inlaat vult de peilband bij, dus het peil komt niet op zijn ondergrens en de bodem
    wordt niet aangesproken. Wat dan telt is het plafond en niet de voorraad - en dat is
    precies waarom er twee getallen nodig zijn en niet een.
    """
    result = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(
            **POLDER,
            deficit_mm_per_day=1.0,
            length_days=183,
            delta_supply_capacity_l_s_ha=0.4,
            soil_type="kleipolder",
        ),
    )
    assert result.soil_store_mm > 0.0
    assert result.soil_supplied_mm == pytest.approx(0.0)
    assert result.days_until_soil_empty is None
    assert result.shortfall_mm == pytest.approx(0.0)
    assert result.binding_link is None


@pytest.mark.asyncio
async def test_the_store_is_used_after_the_level_band_and_not_before(test_context):
    """De bodem ligt ONDER de peilband: eerst het open water, dan de bodem.

    Zonder die volgorde zou de bodemvoorraad onmiddellijk beschikbaar zijn, en dan is hij
    geen bodemvoorraad meer maar extra open water.
    """
    result = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(
            **POLDER,
            deficit_mm_per_day=1.0,
            length_days=183,
            delta_supply_capacity_m3_per_sec=0.0,
            soil_type="kleipolder",
        ),
    )
    # de peilband is helemaal leeggetrokken voordat de bodem iets levert
    assert result.buffer_mm == pytest.approx(10.5, abs=0.01)
    assert result.soil_supplied_mm > 0.0
    assert result.days_until_buffer_empty < result.days_until_soil_empty


@pytest.mark.asyncio
async def test_the_days_until_empty_match_the_withdrawal(test_context):
    """De voorraad gedeeld door wat eruit gaat, en dat is te controleren.

    Bij een tekort van 1 mm/dag en geen aanvoer gaat er 1 mm/dag uit het systeem: de
    peilband houdt het 10,5 dagen en de bodem daarna zijn eigen voorraad.
    """
    result = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(
            **POLDER,
            deficit_mm_per_day=1.0,
            length_days=183,
            delta_supply_capacity_m3_per_sec=0.0,
            soil_type="zandgrond_zonder_slootinvloed",
        ),
    )
    expected_days = (result.buffer_mm + result.soil_store_mm) / 1.0
    assert result.days_until_soil_empty == pytest.approx(expected_days, rel=0.02)


# --- de traagste schakel --------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_binding_link_flips_when_the_slowest_link_flips(test_context):
    """Verlaag de weerstand en de klem verschuift van de sloot naar de wortelzone.

    Dat is de uitspraak die de gebiedstypen dragen: in veenweide is de slootbodem de traagste
    schakel, op zandgrond met water de capillaire opstijging. Bij een vraag boven beide
    plafonds hoort het antwoord die twee te onderscheiden.
    """
    common = dict(**POLDER, deficit_mm_per_day=4, length_days=30)
    peat = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(
            **common, delta_supply_capacity_l_s_ha=0.4, soil_type="veenweide"
        ),
    )
    sand = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(
            **common,
            delta_supply_capacity_l_s_ha=0.4,
            soil_type="zandgrond_met_slootinvloed",
        ),
    )
    assert peat.binding_link == "sloot_naar_bodem"
    assert sand.binding_link == "bodem_naar_wortelzone"
    # en de zandgrond laat meer door, dus er blijft minder onvervuld
    assert sand.unreachable_mm < peat.unreachable_mm


@pytest.mark.asyncio
async def test_the_source_beats_the_intake_in_the_ladder(test_context):
    """Is de bron leeg, dan is dat de klem en niet het kunstwerk.

    De rangorde in `binding_link` is die van het advies: een lege bron is een
    verdelingsvraag, en dan helpt een grotere inlaat in dit gebied niet.
    """
    result = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(
            **POLDER,
            deficit_mm_per_day=4,
            length_days=30,
            delta_supply_capacity_l_s_ha=0.4,
            available_source_volume_m3=500_000,
        ),
    )
    assert result.days_until_source_empty is not None
    assert result.binding_link == "bron_leeg"


@pytest.mark.asyncio
async def test_without_soil_the_link_still_answers(test_context):
    """`binding_link` staat er ook zonder bodem; de vraag welke schakel knelt blijft geldig."""
    result = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(
            **POLDER,
            deficit_mm_per_day=4,
            length_days=30,
            delta_supply_capacity_m3_per_sec=0.0,
        ),
    )
    assert result.soil_store_mm is None
    assert result.binding_link == "inlaat"


# --- de invoerregels ------------------------------------------------------------------


def test_a_store_without_a_ceiling_is_refused():
    """Een voorraad zonder plafond is onmiddellijk beschikbaar, en dan is het geen bodem."""
    with pytest.raises(ModelRetry) as error:
        SupplyInputGivenH(**POLDER, deficit_mm_per_day=4, soil_store_mm=20)
    assert "soil_transfer_mm_per_day" in str(error.value)


def test_a_ceiling_without_a_store_is_refused():
    """En andersom, met dezelfde melding: de twee horen bij elkaar."""
    with pytest.raises(ModelRetry) as error:
        SupplyInputGivenH(**POLDER, deficit_mm_per_day=4, soil_transfer_mm_per_day=1.0)
    assert "soil_store_mm" in str(error.value)


def test_an_own_number_wins_from_the_table():
    """Een eigen getal overschrijft het gebiedstype, en het antwoord zegt welke het was."""
    given = SupplyInputGivenH(
        **POLDER,
        deficit_mm_per_day=4,
        soil_type="veenweide",
        soil_store_mm=25.0,
    )
    assert given.soil_store_mm == 25.0
    # het plafond komt nog wel uit de tabel, want dat is niet opgegeven
    assert given.soil_transfer_mm_per_day == SOIL_TYPES["veenweide"].transfer_mm_per_day


@pytest.mark.asyncio
async def test_an_own_ceiling_does_not_claim_to_know_the_link(test_context):
    """Wij weten dan niet welke schakel erachter zit, en een naam noemen zou dat verzinnen."""
    result = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(
            **POLDER,
            deficit_mm_per_day=4,
            length_days=30,
            delta_supply_capacity_l_s_ha=0.4,
            soil_store_mm=10.0,
            soil_transfer_mm_per_day=1.0,
        ),
    )
    assert result.binding_link == "plafond_opgegeven"
    assert result.data["soil_release"]["source"] == "opgegeven"


@pytest.mark.asyncio
async def test_the_area_type_carries_its_own_assumptions_into_the_answer(test_context):
    """De aannames achter een rij horen in het antwoord, zodat hij na te rekenen is."""
    result = await calculate_supply_given_h(
        test_context,
        SupplyInputGivenH(
            **POLDER,
            deficit_mm_per_day=1,
            length_days=30,
            soil_type="veenweide",
        ),
    )
    block = result.data["soil_release"]
    assert block["soil_type"] == "veenweide"
    assert block["storage_coefficient"] == 0.03
    assert block["drawdown_m"] == 0.20
    assert block["infiltration_resistance_days"] == 300.0
    assert block["source"] == "gebiedstype"


@pytest.mark.asyncio
async def test_the_measure_that_unlocks_the_store_has_a_water_price(test_context):
    """Onderwaterdrainage ontsluit de voorraad en kost zelf water; dat hoort erbij te staan.

    In veenweide ontsluit hij 5,8 mm en vraagt hij 6 tot 77 mm per jaar aan extra
    infiltratie, dus de maatregel kan meer water vragen dan de voorraad die hij vrijmaakt.
    """
    result = await calculate_supply_given_h(
        test_context,
        SupplyInputGivenH(
            **POLDER,
            deficit_mm_per_day=1,
            length_days=30,
            soil_type="veenweide",
        ),
    )
    posts = {post.topic: post for post in result.priceless}
    assert "de bodemvoorraad bereikbaar maken" in posts
    what_it_costs = posts["de bodemvoorraad bereikbaar maken"].what_it_costs
    assert "77 mm" in what_it_costs
    assert "onomkeerbaar" in what_it_costs
