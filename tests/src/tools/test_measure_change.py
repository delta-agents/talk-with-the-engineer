"""Het `measure`-blok: van welke waarde naar welke, en hoeveel dat is.

Vervangt `state_before` en `state_after` in de tooluitvoer. Die gaven de hele toestand twee
keer terug terwijl er per maatregel één grootheid verandert, en juist het verschil in
procentpunten en het relatieve verschil stonden er niet in.

De drie gevallen die deze tests bewaken zijn niet de gelukkige: `before` is bij twee van de
vier maatregelen NUL, een maatregel kan overbodig zijn, en een doel kan onhaalbaar zijn. In
dat laatste geval is `after` de grens waarop het vastloopt en nadrukkelijk geen advies.
"""

import pytest

from talk_with_the_engineer.models import (
    DischargeInputGivenH,
    RetentionInputGivenH,
    StoreInputGivenH,
    SupplyInputGivenH,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import SolveStatus
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.models.modelset_rules_of_thumb import actions as A
from talk_with_the_engineer.tools import (
    calculate_discharge_given_h,
    calculate_retention_given_h,
    calculate_store_given_h,
    calculate_supply_given_h,
)

# Het gebied staat los van het gemaal, want de aanvoertool kent er geen: in een tekort is
# er niets weg te pompen. Zie `SupplyWaterSystemInput.refuse_the_pump_capacity`.
AREA = {
    "area_ha": 4000,
    "percentage_open_water": 3.5,
}
POLDER = {**AREA, "discharge_capacity_m3_per_sec": 5}
WET = {"return_period": 100, "delta_h_available": 0.5}
DRY = {"deficit_mm_per_day": 4, "drawdown_available_m": 0.3}

WET_TOOLS = [
    (calculate_store_given_h, StoreInputGivenH, WET),
    (calculate_retention_given_h, RetentionInputGivenH, WET),
    (calculate_discharge_given_h, DischargeInputGivenH, WET),
]
ALL_TOOLS = WET_TOOLS + [(calculate_supply_given_h, SupplyInputGivenH, DRY)]


def test_every_action_knows_its_own_starting_value():
    """`current_magnitude` is de beginwaarde, en `+ magnitude` is waar je uitkomt.

    De invariant waarop `MeasureChange` rust, hier op de maatregel zelf getoetst in plaats
    van via een tool. Een diff van twee toestanden zou dit niet kunnen: vasthouden werkt op
    `retention_fraction` maar rapporteert hectares, bergen op `pct_open_water` maar
    rapporteert hectares open water.
    """
    state = PolderState(area_ha=4000, pct_open_water=3.5, pump_capacity_m3_per_sec=5.0)
    for action, magnitude in (
        (A.BergenAction(), 44.0),
        (A.AfvoerenAction(), 1.5),
        (A.VasthoudenAction(), 500.0),
        (A.AanvoerenAction(), 1.69),
        (A.PeilopzetAction(), 0.2),
        (A.PeilmargeAction(), 0.3),
    ):
        applied = action.at(magnitude)
        before = applied.current_magnitude(state)
        after = applied.current_magnitude(applied.apply(state))
        assert after == pytest.approx(before + magnitude, abs=1e-9), action.name_nl


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool,model,extra", ALL_TOOLS, ids=lambda v: getattr(v, "__name__", "")
)
async def test_the_measure_change_adds_up(test_context, tool, model, extra):
    """`before + delta == after`, op elke maatregeltool."""
    area = AREA if model is SupplyInputGivenH else POLDER
    result = await tool(test_context, model(**area, **extra))
    change = result.measure

    assert change.after == pytest.approx(change.before + change.delta, abs=1e-6)
    assert change.name_nl
    assert change.unit


@pytest.mark.asyncio
async def test_a_relative_change_needs_something_to_be_relative_to(test_context):
    """`delta_relative` is `None` zodra `before` nul is, en dat is de NORMALE situatie.

    Een polder heeft standaard geen retentie en geen inlaat. 'Oneindig veel meer dan niets'
    is geen bruikbare uitspraak, dus daar hoort geen getal te staan. Bij bergen en afvoeren
    is er wel iets om tegen af te zetten.
    """
    retention = (
        await calculate_retention_given_h(
            test_context, RetentionInputGivenH(**POLDER, **WET)
        )
    ).measure
    supply = (
        await calculate_supply_given_h(test_context, SupplyInputGivenH(**AREA, **DRY))
    ).measure
    store = (
        await calculate_store_given_h(test_context, StoreInputGivenH(**POLDER, **WET))
    ).measure

    assert retention.before == 0.0 and retention.delta_relative is None
    assert supply.before == 0.0 and supply.delta_relative is None
    assert store.before > 0 and store.delta_relative == pytest.approx(
        store.delta / store.before, rel=1e-6
    )


@pytest.mark.asyncio
async def test_percentage_points_only_where_the_quantity_is_a_share(test_context):
    """Open water is een aandeel van het gebied; een gemaal is dat niet.

    Bergen gaat van 3,5 % naar 4,6 %, dus 1,1 procentpunt - en dat is 31 % relatief. Die
    twee door elkaar halen is de klassieke fout in een terugkoppeling, en daarom staan ze
    als twee velden met twee namen.
    """
    store = (
        await calculate_store_given_h(test_context, StoreInputGivenH(**POLDER, **WET))
    ).measure
    discharge = (
        await calculate_discharge_given_h(
            test_context, DischargeInputGivenH(**POLDER, **WET)
        )
    ).measure

    assert store.delta_percentage_points == pytest.approx(1.1, abs=0.05)
    assert store.delta_relative == pytest.approx(0.31, abs=0.02)
    assert discharge.delta_percentage_points is None


@pytest.mark.asyncio
async def test_a_measure_that_is_not_needed_changes_nothing(test_context):
    """Bij `no_measure_needed` is `after` gelijk aan `before` en `delta` nul.

    Het degeneratieve geval is geldig en hoort herkenbaar te zijn zonder dat een beller het
    zelf moet afleiden.
    """
    result = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(**POLDER, return_period=100, delta_h_available=2.0),
    )

    assert result.status is SolveStatus.NO_MEASURE_NEEDED
    assert result.measure.delta == 0.0
    assert result.measure.after == result.measure.before


@pytest.mark.asyncio
async def test_an_unreachable_goal_reports_the_limit_and_not_an_advice(test_context):
    """**De belangrijkste van deze tests.** Bij `action_infeasible` is `after` de GRENS.

    Bergen loopt vast op 100 % open water. Dat is de constatering dat het niet kan, geen
    voorstel om de hele polder onder water te zetten - en het is precies de reden dat de
    veldbeschrijving van `after` naar `status` verwijst. Wie dit getal zonder de status
    doorgeeft, geeft een absurd advies.
    """
    result = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(**POLDER, return_period=1000, delta_h_available=0.01),
    )

    assert result.status is SolveStatus.ACTION_INFEASIBLE
    # het hele gebied als open water: de fysieke bovengrens
    assert result.measure.after == pytest.approx(POLDER["area_ha"], rel=1e-6)
    # en de tekstuele terugkoppeling zegt het ook, zodat het niet alleen in een enum staat
    assert "niet haalbaar" in result.description


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool,model,extra", ALL_TOOLS, ids=lambda v: getattr(v, "__name__", "")
)
async def test_the_replaced_fields_are_really_gone(test_context, tool, model, extra):
    """De echo's en de afleidbare velden staan niet meer in de uitvoer.

    `language` was de invoer terug; `state_before` was de invoer in een ander jasje;
    `dh_reduction_m` is `dh_reference_m` min `dh_with_measure_m`; `feasible_dh_max_m` was
    exact `dh_reference_m`. Deze test faalt zodra er een terugsluipt.
    """
    area = AREA if model is SupplyInputGivenH else POLDER
    result = await tool(test_context, model(**area, **extra))
    body = result.model_dump()

    for gone in (
        "language",
        "state_before",
        "state_after",
        "dh_reduction_m",
        "feasible_dh_max_m",
    ):
        assert gone not in body, gone


@pytest.mark.asyncio
async def test_a_measure_that_does_nothing_reports_zero_and_not_noise(test_context):
    """Nul procentpunt is nul, en niet `4,4e-16`.

    Gevonden door de tool over MCP aan te roepen in plaats van door de code te lezen.
    `pct_open_water` wordt via het areaal heen en weer gerekend, dus een maatregel van nul
    kwam een ULP naast zijn eigen beginwaarde uit - en dat getal ging als
    "4,4e-16 procentpunt" de uitvoer in.

    En dit is meteen de reden dat het aandeel op de MAATREGEL zit en niet uit een diff van
    twee toestanden komt: verandert er niets, dan is uit de toestanden niet meer af te
    leiden welke grootheid de maatregel zou hebben veranderd. Een diff gaf dan `0,0` voor
    afvoeren, alsof gemaalcapaciteit een aandeel van het gebied is.
    """
    store = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(**POLDER, return_period=100, delta_h_available=2.0),
    )
    discharge = await calculate_discharge_given_h(
        test_context,
        DischargeInputGivenH(**POLDER, return_period=100, delta_h_available=2.0),
    )

    assert store.status is SolveStatus.NO_MEASURE_NEEDED
    assert store.measure.delta_percentage_points == 0.0
    # gemaalcapaciteit is geen aandeel van het gebied, ook niet als er niets verandert
    assert discharge.measure.delta_percentage_points is None


@pytest.mark.asyncio
async def test_a_percentage_says_what_it_is_a_percentage_of(test_context):
    """De noemer verschilt per maatregel, en staat er daarom bij.

    Bergen rapporteert `pct_open_water` - een deel van het hele gebied. Vasthouden
    rapporteert `retention_fraction` - een deel van het LANDoppervlak, want op open water
    kun je niets vasthouden. Die twee gelijktrekken zou een grootheid opleveren die niemand
    gebruikt, en het koopt geen vergelijkbaarheid: de maatregelen doen niet hetzelfde.

    Zonder `share_of_nl` is '59 procentpunt' dubbelzinnig, en dat is precies het soort
    dubbelzinnigheid dat een verkeerde zin naar de gebruiker oplevert.
    """
    store = (
        await calculate_store_given_h(test_context, StoreInputGivenH(**POLDER, **WET))
    ).measure
    retention = (
        await calculate_retention_given_h(
            test_context, RetentionInputGivenH(**POLDER, **WET)
        )
    ).measure
    discharge = (
        await calculate_discharge_given_h(
            test_context, DischargeInputGivenH(**POLDER, **WET)
        )
    ).measure

    assert store.share_of_nl == "het gebied"
    assert retention.share_of_nl == "het landoppervlak"
    # een capaciteit is geen aandeel, dus er is ook geen noemer om te noemen
    assert discharge.delta_percentage_points is None
    assert discharge.share_of_nl is None

    # en het percentage hoort bij die noemer: 2277 ha op 3860 ha land
    assert retention.delta_percentage_points == pytest.approx(
        retention.after
        / (POLDER["area_ha"] * (1 - POLDER["percentage_open_water"] / 100))
        * 100,
        abs=0.1,
    )
