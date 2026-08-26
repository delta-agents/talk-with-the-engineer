"""De aanvoertools: dezelfde rekenkern, de andere richting.

Twee dingen staan hier centraal. Dat de drie posten optellen tot de vraag - geleverd plus
berging plus tekort - want dat is de enige totaalcontrole die de droogtekant heeft. En dat
de inverse de *kleinste* dekkende capaciteit vindt in plaats van de bovengrens; die fout is
er tijdens de bouw daadwerkelijk in geslopen.
"""

import pytest

from talk_with_the_engineer.models import (
    SupplyInputGivenH,
    SupplyInputGivenSupply,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import SolveStatus
from talk_with_the_engineer.tools import (
    calculate_supply_given_h,
    calculate_supply_given_supply,
)

# Referentiepolder, en een tekort van 4 mm/dag over 30 dagen: 120 mm vraag. Een warme
# zomermaand zonder regen. De bruikbare diepte onder streefpeil is 30 cm, wat op 3,5 %
# open water 10,5 mm berging over de polder is.
BASE = {
    "area_ha": 4000,
    "percentage_open_water": 3.5,
    "discharge_capacity_l_s_ha": 1.25,
    "deficit_mm_per_day": 4,
    "drawdown_available_m": 0.30,
    "length_days": 30,
}

DEMAND_MM = 120.0
BUFFER_MM = 10.5

# Het Twente-anker uit WP12: 1 % open water, dus bijna geen eigen berging, en daarmee is de
# beschikbaarheid van aanvoerwater de bindende vraag in plaats van de inlaatcapaciteit.
TWENTE = {**BASE, "percentage_open_water": 1.0}
del TWENTE["drawdown_available_m"]


@pytest.mark.asyncio
async def test_the_inverse_finds_the_smallest_covering_capacity(test_context):
    """0,4225 l/s/ha, en niet de bovengrens.

    De vraag is 4 mm/dag; de berging levert 10,5 mm over 30 dagen, dus 0,35 mm/dag. Wat de
    inlaat moet dekken is 3,65 van de 4 mm/dag, oftewel 0,4225 van de 0,4630 l/s/ha die de
    volle vraag zou kosten.

    Dit ging tijdens de bouw mis. Met een bisectie op *gelijkheid* aan nul tekort kwam de
    bovengrens eruit - 5 l/s/ha - want het tekort is nul over een heel interval en de
    randcontrole sloeg daarop aan. De vraag is de kleinste capaciteit die het haalt, en dat
    is een binaire zoektocht op een monotone voorwaarde.
    """
    result = await calculate_supply_given_h(test_context, SupplyInputGivenH(**BASE))

    assert result.status is SolveStatus.EXACT
    assert result.data["supply_capacity_l_s_ha"] == pytest.approx(0.4225, abs=5e-4)
    assert result.shortfall_mm == pytest.approx(0.0, abs=1e-6)
    assert result.drawdown_m == pytest.approx(0.30, abs=1e-3)


@pytest.mark.asyncio
async def test_the_inverse_answer_is_just_above_the_supply_norm(test_context):
    """De aanvoernorm van 0,4 l/s/ha dekt dit tekort net niet.

    Geen toeval en geen ramp: 0,4 haalt 95 % van de 0,4225 die nodig is. Maar het is wel
    het soort uitspraak waarvoor je een model nodig hebt in plaats van de norm.
    """
    needed = (
        await calculate_supply_given_h(test_context, SupplyInputGivenH(**BASE))
    ).data["supply_capacity_l_s_ha"]
    assert 0.4 < needed < 0.45
    assert 0.4 / needed == pytest.approx(0.947, abs=0.01)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "supply_l_s_ha,shortfall_mm,days_until_empty",
    [(0.0, 109.50, 2.58), (0.3, 31.74, 7.42), (0.4, 5.82, 19.29)],
)
async def test_the_forward_anchors(
    test_context, supply_l_s_ha, shortfall_mm, days_until_empty
):
    """BOUW_WP8_WP10.md Sec. 7.E, nu via de toolgrens in plaats van de kern."""
    result = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(**BASE, delta_supply_capacity_l_s_ha=supply_l_s_ha),
    )
    assert result.shortfall_mm == pytest.approx(shortfall_mm, abs=5e-2)
    assert result.days_until_buffer_empty == pytest.approx(days_until_empty, abs=5e-2)
    assert result.buffer_mm == pytest.approx(BUFFER_MM, abs=1e-6)


@pytest.mark.asyncio
@pytest.mark.parametrize("supply_l_s_ha", [0.0, 0.2, 0.4, 0.4225, 0.5, 1.0, 3.0])
async def test_the_three_posts_add_up_to_the_demand(test_context, supply_l_s_ha):
    """Geleverd + berging + tekort = de vraag. Ook boven de dekkende capaciteit.

    Dit ging tijdens de bouw mis bij overcapaciteit: `supplied_mm` werd uit de capaciteit
    maal de tijd berekend in plaats van uit de reeks, en dan meldde de tool 1296 van de
    120 mm geleverd. Een inlaat die groter is dan de vraag levert de vraag; de bovengrens
    van de klem knijpt de rest af.
    """
    result = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(**BASE, delta_supply_capacity_l_s_ha=supply_l_s_ha),
    )
    total = result.supplied_mm + result.buffer_mm + result.shortfall_mm
    assert total == pytest.approx(DEMAND_MM, rel=1e-6)
    assert result.supplied_mm <= DEMAND_MM + 1e-6
    assert result.buffer_mm >= 0.0
    assert result.shortfall_mm >= 0.0


@pytest.mark.asyncio
async def test_enough_supply_holds_the_target_level(test_context):
    result = await calculate_supply_given_supply(
        test_context, SupplyInputGivenSupply(**BASE, delta_supply_capacity_l_s_ha=1.0)
    )
    assert result.shortfall_mm == pytest.approx(0.0, abs=1e-9)
    assert result.drawdown_m == pytest.approx(0.0, abs=1e-9)
    assert result.buffer_mm == pytest.approx(0.0, abs=1e-9)
    assert result.days_until_buffer_empty is None


@pytest.mark.asyncio
async def test_no_measure_needed_when_the_buffer_covers_the_deficit(test_context):
    """Een klein tekort en een ruime marge: dan is een inlaat niet nodig."""
    result = await calculate_supply_given_h(
        test_context,
        SupplyInputGivenH(
            **{**BASE, "deficit_mm_per_day": 0.2, "length_days": 30},
            **{},
        ),
    )
    assert result.status is SolveStatus.NO_MEASURE_NEEDED
    assert result.supply_capacity_m3_per_sec == pytest.approx(0.0)
    assert "geen inlaatcapaciteit nodig" in result.description.lower()


@pytest.mark.asyncio
async def test_an_extreme_deficit_is_reported_as_action_infeasible(test_context):
    """Niet een geklemd getal maar een uitleg, en niet 'het probleem is onoplosbaar'.

    `action_infeasible` en niet `problem_infeasible`: aanvoeren alleen haalt het niet, maar
    bergen of vasthouden kunnen er nog bij.
    """
    result = await calculate_supply_given_h(
        test_context,
        SupplyInputGivenH(**{**BASE, "deficit_mm_per_day": 60}),
    )
    assert result.status is SolveStatus.ACTION_INFEASIBLE
    assert result.shortfall_mm > 0
    assert "niet te dekken" in result.description


@pytest.mark.asyncio
async def test_the_days_readout_is_the_useful_one(test_context):
    """Meer aanvoer schuift het moment waarop de berging op is naar achteren.

    Een aantal dagen is voor een lezer af te wegen; een aantal millimeters onvervulde vraag
    is dat niet. Daarom staat het in de uitlegzin.
    """
    days = []
    for norm in (0.0, 0.1, 0.2, 0.3, 0.4):
        result = await calculate_supply_given_supply(
            test_context, SupplyInputGivenSupply(**BASE, delta_supply_capacity_l_s_ha=norm)
        )
        days.append(result.days_until_buffer_empty)
    assert days == sorted(days)
    assert "van de 30 dagen op" in result.description


@pytest.mark.asyncio
async def test_the_assumed_period_is_reported(test_context):
    """`length_days` weglaten mag, maar dan staat het in `assumptions`.

    De benodigde capaciteit hangt eraan: de berging dekt een vast volume, dus over een
    langere periode een steeds kleiner deel.
    """
    without = {key: value for key, value in BASE.items() if key != "length_days"}
    result = await calculate_supply_given_h(test_context, SupplyInputGivenH(**without))
    assert [a.field for a in result.assumptions] == ["length_days"]
    assert "length_days=30" in result.description


# De inlaatcapaciteit die de volle vraag van 4 mm/dag dekt, zonder berging: het land vraagt
# 1,7870 m3/s en het open water 0,0648, samen 1,8519 m3/s op 4000 ha.
FULL_DEMAND_L_S_HA = 0.4630


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [10, 30, 90, 365])
async def test_the_buffer_buys_time_and_not_coverage(test_context, days):
    """Waarom de duur uitmaakt, als formule in plaats van als los getal.

    De berging levert een vast volume - 10,5 mm - en dus over een langere periode een
    steeds kleiner deel van de dagvraag. Wat de inlaat moet dekken is `tekort - berging/duur`,
    en de benodigde capaciteit schaalt daarmee:

        nodig = volle_vraag * (tekort - berging/duur) / tekort

    Bij 30 dagen is dat 0,4225 l/s/ha en bij 90 dagen 0,4495; hij kruipt naar 0,4630 toe
    zonder daar ooit te komen. Dat is precies waarom `length_days` een gemelde aanname is.
    """
    result = await calculate_supply_given_h(
        test_context, SupplyInputGivenH(**{**BASE, "length_days": days})
    )
    covered_by_buffer_mm_per_day = BUFFER_MM / days
    expected = (
        FULL_DEMAND_L_S_HA
        * (BASE["deficit_mm_per_day"] - covered_by_buffer_mm_per_day)
        / BASE["deficit_mm_per_day"]
    )
    assert result.data["supply_capacity_l_s_ha"] == pytest.approx(expected, abs=1e-3)
    assert result.data["supply_capacity_l_s_ha"] < FULL_DEMAND_L_S_HA


@pytest.mark.asyncio
async def test_the_forward_and_inverse_agree(test_context):
    """Het rondje sluit: de capaciteit uit de inverse levert precies geen tekort."""
    needed = (
        await calculate_supply_given_h(test_context, SupplyInputGivenH(**BASE))
    ).data["supply_capacity_l_s_ha"]
    forward = await calculate_supply_given_supply(
        test_context, SupplyInputGivenSupply(**BASE, delta_supply_capacity_l_s_ha=needed)
    )
    assert forward.shortfall_mm == pytest.approx(0.0, abs=1e-3)

    just_short = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(**BASE, delta_supply_capacity_l_s_ha=needed * 0.95),
    )
    assert just_short.shortfall_mm > 0.0


@pytest.mark.asyncio
async def test_the_text_never_calls_a_drawdown_a_rise(test_context):
    """De gespiegelde D11: op de droogtekant is elk woord over stijgen fout."""
    for supply in (0.0, 0.4, 1.0):
        result = await calculate_supply_given_supply(
            test_context, SupplyInputGivenSupply(**BASE, delta_supply_capacity_l_s_ha=supply)
        )
        lowered = result.description.lower()
        assert "stijg" not in lowered
        assert "verlaging" not in lowered


# --- de eindige bron aan de toolgrens (WP14.5) --------------------------------------


@pytest.mark.asyncio
async def test_omitting_the_source_volume_keeps_the_load_bearing_caveat(test_context):
    """Zonder bronvolume is de aanname dragend, en dan hoort de caveat er te staan.

    Op de natte kant is "de rand neemt je water aan" onschuldig; op de droge kant is hij
    dragend. Dat verschil is de belangrijkste caveat van het hele model.
    """
    result = await calculate_supply_given_h(
        test_context, SupplyInputGivenH(**TWENTE, drawdown_available_m=0.3)
    )
    topics = {caveat.topic for caveat in result.caveats}

    assert "beschikbaarheid van aanvoerwater" in topics
    assert "herkomst van het bronvolume" not in topics


@pytest.mark.asyncio
async def test_giving_the_source_volume_replaces_the_caveat_instead_of_repeating_it(
    test_context,
):
    """Zodra de bron is gemodelleerd is die caveat ONWAAR, en dan hoort hij weg.

    Wat ervoor in de plaats komt is wat er dan nog wel openstaat: het volume is een invoer,
    dus dit antwoord is voorwaardelijk en geen voorspelling. Een caveat laten staan die niet
    meer geldt is net zo misleidend als er geen hebben.
    """
    result = await calculate_supply_given_h(
        test_context,
        SupplyInputGivenH(
            **TWENTE, drawdown_available_m=0.3, available_source_volume_m3=1_000_000
        ),
    )
    topics = {caveat.topic for caveat in result.caveats}

    assert "beschikbaarheid van aanvoerwater" not in topics
    assert "herkomst van het bronvolume" in topics


@pytest.mark.asyncio
async def test_an_empty_source_makes_the_answer_infeasible(test_context):
    """De Twente-casus: zonder water is er geen inlaatcapaciteit die het tekort dekt.

    Dat is het eerlijke antwoord in plaats van "0,45 l/s/ha en je tekort is gedekt". Meer
    capaciteit haalt het water niet uit een droge boezem, en dus is dit `action_infeasible`
    en geen `exact`.
    """
    covered = await calculate_supply_given_h(
        test_context, SupplyInputGivenH(**TWENTE, drawdown_available_m=0.3)
    )
    assert covered.status is SolveStatus.EXACT

    dry = await calculate_supply_given_h(
        test_context,
        SupplyInputGivenH(
            **TWENTE, drawdown_available_m=0.3, available_source_volume_m3=0
        ),
    )
    assert dry.status is SolveStatus.ACTION_INFEASIBLE
    assert dry.shortfall_mm > 0.9 * dry.demand_mm


# --- de bestaande inlaat en de uitbreiding zijn twee dingen -------------------------


@pytest.mark.asyncio
async def test_the_forward_tool_reports_a_new_intake_as_something_that_must_happen(
    test_context,
):
    """`measure.delta` betekende in de twee aanvoertools iets verschillends.

    De opgegeven inlaat werd gelezen als de BESTAANDE situatie, dus `before` en `after`
    waren gelijk en `delta` was nul - terwijl er een inlaat van 1,2 m3/s in het spel is die
    50 van de 120 mm levert en waarbij 60 mm vraag onvervuld blijft. Een beller die
    `measure.delta` leest als "wat moet er gebeuren" - de juiste lezing bij de zeven andere
    maatregeltools - concludeerde daaruit dat er niets hoeft te gebeuren.
    """
    result = await calculate_supply_given_supply(
        test_context, SupplyInputGivenSupply(**BASE, delta_supply_capacity_l_s_ha=0.3)
    )
    assert result.measure.before == 0.0
    assert result.measure.delta == pytest.approx(result.measure.after)
    assert result.measure.delta > 0


@pytest.mark.asyncio
async def test_an_existing_intake_is_before_and_the_extension_is_delta(test_context):
    """Dezelfde vorm als het afvoerpaar: bestaand plus uitbreiding is de nieuwe situatie."""
    result = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(
            **BASE, supply_capacity_l_s_ha=0.2, delta_supply_capacity_l_s_ha=0.3
        ),
    )
    assert result.measure.before == pytest.approx(0.2 * 4000 / 1000)
    assert result.measure.delta == pytest.approx(0.3 * 4000 / 1000)
    assert result.measure.after == pytest.approx(0.5 * 4000 / 1000)
    assert result.supply_capacity_m3_per_sec == pytest.approx(result.measure.after)


@pytest.mark.asyncio
async def test_the_inverse_tool_only_asks_for_what_is_missing(test_context):
    """Met een bestaande inlaat is het antwoord de UITBREIDING en niet het totaal.

    Voorheen kende de inverse tool geen bestaande inlaat en rekende hij altijd vanaf nul.
    Nu is `after` het totaal dat nodig is en `delta` wat daarvoor nog aangelegd moet worden.
    """
    from_scratch = await calculate_supply_given_h(
        test_context, SupplyInputGivenH(**BASE)
    )
    partly_built = await calculate_supply_given_h(
        test_context, SupplyInputGivenH(**BASE, supply_capacity_l_s_ha=0.2)
    )

    assert partly_built.measure.after == pytest.approx(from_scratch.measure.after)
    assert partly_built.measure.before == pytest.approx(0.2 * 4000 / 1000)
    assert partly_built.measure.delta == pytest.approx(
        from_scratch.measure.delta - 0.2 * 4000 / 1000
    )


@pytest.mark.asyncio
async def test_an_intake_that_already_covers_the_deficit_needs_no_measure(test_context):
    """En dan is `delta` nul omdat er niets hoeft, niet omdat de velden samenvallen."""
    result = await calculate_supply_given_h(
        test_context, SupplyInputGivenH(**BASE, supply_capacity_l_s_ha=3.0)
    )
    assert result.status is SolveStatus.NO_MEASURE_NEEDED
    assert result.measure.delta == pytest.approx(0.0)
    assert result.measure.before == pytest.approx(3.0 * 4000 / 1000)
