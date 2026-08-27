"""De tweede ingang op de natte as: je eigen neerslagsom naast de statistiek.

De droge kant heeft er twee - een tekort dat je zelf opgeeft, of een droogte uit STOWA
2025-23 - en de natte kant had er een. Dit bestand legt vast dat ze nu hetzelfde werken, en
dat de vrijheid niet ten koste gaat van de herleidbaarheid: een antwoord dat op een
opgegeven getal rust, zegt dat.

Zie issue #52 voor de afweging tussen optellen, aftrekken en de derde weg.
"""

import pytest
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models import (
    CascadeInput,
    CascadeNode,
    DischargeInputGivenH,
    RetentionInputGivenH,
    StoreInputGivenArea,
    StoreInputGivenH,
)
from talk_with_the_engineer.tools import (
    calculate_cascade_given_excess,
    calculate_discharge_given_h,
    calculate_retention_given_h,
    calculate_store_given_area,
    calculate_store_given_h,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_rainfall import (
    get_sum_rainfall_stats,
)

POLDER = {"area_ha": 4000, "discharge_capacity_m3_per_sec": 5}

# De som die de statistiek voor de standaardbui geeft: zomer, 96 uur, regime R, T100. Uit
# de tabel en niet overgetypt, zodat de gelijkwaardigheidstoets meebeweegt als de bron ooit
# wordt bijgewerkt.
T100_SUMMER_96H_MM = get_sum_rainfall_stats(
    return_period=100.0,
    time_of_year="summer",
    length_event_hrs=96.0,
    rainfall_regime="R",
)


def test_the_reference_total_is_what_the_statistic_actually_gives():
    """Het ankergetal, zodat de rest van dit bestand op iets echts rust."""
    assert T100_SUMMER_96H_MM == pytest.approx(86.6, abs=0.05)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool,model,extra",
    [
        (calculate_store_given_h, StoreInputGivenH, {"delta_h_available": 1.0}),
        (calculate_retention_given_h, RetentionInputGivenH, {"delta_h_available": 1.0}),
        (calculate_discharge_given_h, DischargeInputGivenH, {"delta_h_available": 1.0}),
        (calculate_store_given_area, StoreInputGivenArea, {"area_available_ha": 100}),
    ],
)
async def test_the_same_total_by_either_route_gives_the_same_answer(
    test_context, tool, model, extra
):
    """De scherpste toets die er is: opzoeken en zelf opgeven moeten samenvallen.

    `rain_volume_mm` vervangt precies één stap - de tabelopzoeking - en verder niets. Voer
    je de waarde terug die de tabel zelf zou opleveren, dan hoort er tot op de laatste bit
    hetzelfde uit te komen. Wijkt dat af, dan doet de eigen ingang iets extra's, en dan is
    hij geen tweede weg naar hetzelfde antwoord maar een tweede model.
    """
    looked_up = await tool(test_context, model(**POLDER, return_period=100, **extra))
    supplied = await tool(
        test_context, model(**POLDER, rain_volume_mm=T100_SUMMER_96H_MM, **extra)
    )

    assert supplied.data["rain_volume_gross_mm"] == pytest.approx(
        looked_up.data["rain_volume_gross_mm"]
    )
    assert supplied.data["rain_loss_mm"] == pytest.approx(
        looked_up.data["rain_loss_mm"]
    )
    assert supplied.measure.delta == pytest.approx(looked_up.measure.delta)
    assert supplied.status is looked_up.status


@pytest.mark.asyncio
async def test_the_cascade_takes_an_own_storm_too(test_context):
    """Ook de systeemtool; hij erft dezelfde bui-invoer."""
    looked_up = await calculate_cascade_given_excess(
        test_context,
        CascadeInput(
            return_period=100,
            nodes=[CascadeNode(name="A", percentage_open_water=3.5, **POLDER)],
        ),
    )
    supplied = await calculate_cascade_given_excess(
        test_context,
        CascadeInput(
            rain_volume_mm=T100_SUMMER_96H_MM,
            nodes=[CascadeNode(name="A", percentage_open_water=3.5, **POLDER)],
        ),
    )
    assert supplied.worst_dh_m == pytest.approx(looked_up.worst_dh_m)


@pytest.mark.asyncio
async def test_a_bigger_total_gives_a_bigger_measure(test_context):
    """En het getal doet ook echt iets; anders zou de test hierboven ook slagen op inert."""
    answers = []
    for volume in (40.0, 86.6, 150.0):
        result = await calculate_store_given_h(
            test_context,
            StoreInputGivenH(**POLDER, rain_volume_mm=volume, delta_h_available=1.0),
        )
        answers.append(result.measure.delta)
    assert answers[0] < answers[1] < answers[2]


def test_giving_both_routes_is_refused():
    """Twee ingangen naast elkaar maakt onzichtbaar welke het antwoord stuurt.

    Exact de regel die op de droge kant al gold voor `deficit_mm_per_day` naast een gekozen
    droogte.
    """
    with pytest.raises(ModelRetry) as error:
        StoreInputGivenH(
            **POLDER, return_period=100, rain_volume_mm=86.6, delta_h_available=1.0
        )
    assert "dubbelop" in str(error.value)
    assert "rain_volume_mm" in str(error.value)
    assert "return_period" in str(error.value)


def test_giving_neither_route_is_refused():
    """En weglaten kan ook niet: er moet een bui zijn om door te rekenen."""
    with pytest.raises(ModelRetry) as error:
        StoreInputGivenH(**POLDER, delta_h_available=1.0)
    assert "return_period" in str(error.value)
    assert "rain_volume_mm" in str(error.value)


def test_a_regime_that_cannot_apply_is_refused_and_not_ignored():
    """`rainfall_regime` is een correctiefactor OP de opzoeking.

    Bij een eigen som is er niets om te corrigeren. Hem accepteren zou de opgegeven waarde
    stil met tot 9 % verschuiven - dezelfde faalmodus die `one_unit_only` elders bestrijdt.
    """
    with pytest.raises(ModelRetry) as error:
        StoreInputGivenH(
            **POLDER, rain_volume_mm=86.6, rainfall_regime="H", delta_h_available=1.0
        )
    assert "rainfall_regime" in str(error.value)
    assert "correctiefactor" in str(error.value)


@pytest.mark.asyncio
async def test_a_regime_that_cannot_apply_is_not_reported_as_an_assumption(
    test_context,
):
    """En hij staat ook niet in `assumptions`: dat zou zeggen dat hij het antwoord stuurt."""
    result = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(**POLDER, rain_volume_mm=86.6, delta_h_available=1.0),
    )
    assumed = {item.field for item in result.assumptions}
    assert "rainfall_regime" not in assumed
    # de velden die wél meedoen worden nog gewoon gemeld
    assert {"time_of_year", "length_event_hrs", "name_rainfall_pattern"} <= assumed


@pytest.mark.asyncio
async def test_an_answer_says_where_its_forcing_came_from(test_context):
    """Punt 3 van "klaar wanneer" in issue #52.

    De vrijheid mag niet stil zijn. Bij een opgegeven som staat de herkomst in `data` en
    staat er een caveat bij; bij een opgezochte som staat de bron er, en die caveat niet.
    """
    supplied = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(**POLDER, rain_volume_mm=86.6, delta_h_available=1.0),
    )
    looked_up = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(**POLDER, return_period=100, delta_h_available=1.0),
    )

    assert supplied.data["rain_volume_source"] == "opgegeven in de aanroep"
    assert "STOWA 2019" in looked_up.data["rain_volume_source"]

    topics = {caveat.topic for caveat in supplied.caveats}
    assert "de bui is opgegeven" in topics
    assert "de bui is opgegeven" not in {c.topic for c in looked_up.caveats}

    # en de caveat zegt wat de lezer ermee moet
    caveat = next(c for c in supplied.caveats if c.topic == "de bui is opgegeven")
    assert "geen herhaaltijd" in caveat.what
    assert "herkomst" in caveat.consequence


@pytest.mark.asyncio
async def test_the_dry_side_says_it_too(test_context):
    """Dezelfde melding aan de droge kant, want dat is wat "gelijk trekken" betekent.

    `deficit_mm_per_day` bestond al en was net zo stil: het antwoord zag er hetzelfde uit
    als een antwoord uit de statistiek.
    """
    from talk_with_the_engineer.models import SupplyInputGivenH
    from talk_with_the_engineer.tools import calculate_supply_given_h

    supplied = await calculate_supply_given_h(
        test_context,
        SupplyInputGivenH(area_ha=4000, drawdown_available_m=0.3, deficit_mm_per_day=4),
    )
    looked_up = await calculate_supply_given_h(
        test_context,
        SupplyInputGivenH(
            area_ha=4000,
            drawdown_available_m=0.3,
            drought_region="Rijn_en_IJssel",
            drought_scenario="Referentie",
            drought_return_period=10,
        ),
    )
    assert "het tekort is opgegeven" in {c.topic for c in supplied.caveats}
    assert "het tekort is opgegeven" not in {c.topic for c in looked_up.caveats}


@pytest.mark.asyncio
async def test_an_own_storm_still_loses_its_summer_rainfall(test_context):
    """De som is BRUTO: duur, vorm en neerslagverlies blijven van het model.

    Dat is precies wat deze ingang wel en niet is - hij vervangt de opzoeking en niet de
    rest van de bui.
    """
    result = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(
            **POLDER, rain_volume_mm=100.0, time_of_year="summer", delta_h_available=1.0
        ),
    )
    assert result.data["rain_volume_gross_mm"] == pytest.approx(100.0)
    assert result.data["rain_loss_mm"] > 0
    assert sum(result.data["rainfall_per_day_net_mm"]) == pytest.approx(
        100.0 - result.data["rain_loss_mm"], abs=0.05
    )

    # in de winter is er geen verlies, en dan komt de hele som in de reeks terecht
    winter = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(
            **POLDER, rain_volume_mm=100.0, time_of_year="winter", delta_h_available=1.0
        ),
    )
    assert winter.data["rain_loss_mm"] == pytest.approx(0.0)
    assert sum(winter.data["rainfall_per_day_net_mm"]) == pytest.approx(100.0, abs=0.05)
