"""Maatregel aanvoeren: meer inlaatcapaciteit.

Grijpt aan op `capacity_in_m3_per_sec` van de verbinding, en gebruikt dezelfde rekenkern
als de andere vijf tools met de klem gespiegeld. Zie `simulate_deficit`.
"""

from dataclasses import dataclass

from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    assumed_defaults,
    model_caveats,
    priceless_posts,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
    AanvoerenAction,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.connection import Connection
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    MeasureChange,
    PricelessPost,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.models.modelset_rules_of_thumb.supply import (
    SupplyInputGivenH,
    SupplyInputGivenSupply,
    SupplyOutput,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.descriptions import (
    append_assumptions,
    describe_supply_forward,
    describe_supply_inverse,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.solve import (
    evaluate_supply,
    solve_supply,
)
from talk_with_the_engineer.utils.logging_utils import log_tool_call

SECONDS_PER_MINUTE = 60
MINUTES_PER_DAY = 60 * 24
LITRES_PER_M3 = 1000


@dataclass(frozen=True)
class Deficit:
    """De exogene droogte zoals `simulate_deficit` hem verwacht."""

    deficit_mm_per_day: float
    length_days: int
    available_source_volume_m3: float = float("inf")
    """Wat de bron over deze periode kan leveren [m3]; `inf` is onbeperkt.

    Onbeperkt is het gedrag dat er altijd was, en het is precies de aanname die de caveat
    over aanvoerbeschikbaarheid benoemde: dat het water bij de inlaat is. Vul hem in en die
    aanname wordt een getal.
    """


def _state(input, supply_capacity_m3_per_sec: float = 0.0) -> PolderState:
    """Bouw de toestand, met de bruikbare diepte onder streefpeil als peilmarge.

    `drawdown_available_m` en `level_margin_m` zijn dezelfde grootheid vanuit twee kanten
    bekeken: hoe diep de waterstand mag zakken. Aan de toolgrens heet hij naar wat de beller
    weet, in de toestand naar wat de rekenkern ermee doet.
    """
    return PolderState(
        area_ha=input.area_ha,
        pct_open_water=input.percentage_open_water,
        level_margin_m=input.drawdown_available_m,
        connections=(
            Connection(
                capacity_out_m3_per_sec=input.discharge_capacity_m3_per_sec,
                capacity_in_m3_per_sec=supply_capacity_m3_per_sec,
            ),
        ),
    )


def _data(input, result) -> dict:
    """De echo van de vraag, plus het antwoord in alle eenheden waarin een inlaat wordt
    uitgedrukt.

    Wat hier NIET meer in staat: `demand_mm`, `supplied_mm`, `buffer_mm`, `shortfall_mm`,
    de uitzakking en `days_until_buffer_empty`. Die zes stonden zowel hier als op
    topniveau, en dubbele velden roepen bij een beller de vraag op of er verschil is - juist
    omdat ze in `data` "ruwe uitkomsten en tussenresultaten" heten en op topniveau een
    gedocumenteerd veld zijn. Er was geen verschil; ze staan nu alleen nog op topniveau,
    waar de beschrijving bij ze hoort.
    """
    per_sec = result.supply_capacity_m3_per_sec
    return {
        # de vraag waar dit antwoord op reageert
        "deficit_mm_per_day": input.deficit_mm_per_day,
        "length_days": input.length_days,
        "drawdown_available_m": input.drawdown_available_m,
        # het antwoord, in alle eenheden waarin een inlaat wordt uitgedrukt
        "supply_capacity_m3_per_sec": per_sec,
        "supply_capacity_m3_per_min": per_sec * SECONDS_PER_MINUTE,
        "supply_capacity_m3_per_day": per_sec * SECONDS_PER_MINUTE * MINUTES_PER_DAY,
        "supply_capacity_l_s_ha": per_sec * LITRES_PER_M3 / input.area_ha,
        "supply_capacity_mm_d": per_sec
        * SECONDS_PER_MINUTE
        * MINUTES_PER_DAY
        / input.area_m2
        * LITRES_PER_M3,
    }


def _required_volume_m3(input, result) -> float:
    """Het volume dat door de inlaat moet, over de hele periode.

    Staat in de caveat omdat een debiet haalbaar klinkt en een volume uitnodigt tot
    narekenen: 1,81 m3/s is een pompje, 4,7 miljoen m3 in een maand is een vraag aan het
    regionale systeem. Nul bij nul capaciteit, en dan gaat de caveat niet af.
    """
    return (
        result.supply_capacity_m3_per_sec
        * input.length_days
        * SECONDS_PER_MINUTE
        * MINUTES_PER_DAY
    )


def _days(result) -> float | None:
    """`inf` is geen geldige JSON, dus een periode die het volhoudt wordt `None`."""
    days = result.days_until_buffer_empty
    return None if days == float("inf") else days


def _supply_measure(result) -> MeasureChange:
    """Het `measure`-blok voor de aanvoerkant.

    Eigen functie en niet `MeasureChange.from_solve_result`, want de droogtekant heeft een
    eigen resultaattype: `SupplySolveResult` kent geen `magnitude`/`unit` maar een
    inlaatcapaciteit. De inhoud is dezelfde vraag - van welke waarde naar welke - en de vorm
    naar buiten hoort dus gelijk te zijn aan die van de natte tools.
    """
    before = result.state_before.supply_capacity_m3_per_sec
    after = result.supply_capacity_m3_per_sec
    delta = after - before
    return MeasureChange(
        name_nl=AanvoerenAction.name_nl,
        unit=AanvoerenAction.unit,
        before=before,
        after=after,
        delta=delta,
        delta_relative=(delta / before) if before else None,
        # een inlaat is een capaciteit en geen aandeel van het gebied
        delta_percentage_points=None,
    )


@log_tool_call
async def calculate_supply_given_h(ctx, input: SupplyInputGivenH) -> SupplyOutput:
    """Hoeveel inlaatcapaciteit dekt het neerslagtekort zonder dat de waterstand te diep zakt?

    Aanvoeren = supply.
    """
    state = _state(input)
    deficit = Deficit(
        input.deficit_mm_per_day,
        input.length_days,
        float("inf")
        if input.available_source_volume_m3 is None
        else float(input.available_source_volume_m3),
    )
    result = solve_supply(state, deficit)

    assumptions = assumed_defaults(input)
    caveats = model_caveats(
        input,
        is_drought=True,
        required_supply_volume_m3=_required_volume_m3(input, result),
        source_volume_is_modelled=input.available_source_volume_m3 is not None,
    )
    return SupplyOutput(
        data=_data(input, result),
        description=append_assumptions(
            describe_supply_inverse(result, input, input.language),
            assumptions,
            input.language,
        ),
        status=result.status,
        assumptions=assumptions,
        caveats=caveats,
        priceless=[
            PricelessPost(**post)
            for post in priceless_posts(input, AanvoerenAction.name_nl)
        ],
        measure=_supply_measure(result),
        supply_capacity_m3_per_sec=result.supply_capacity_m3_per_sec,
        demand_mm=result.demand_mm,
        supplied_mm=result.supplied_mm,
        buffer_mm=result.buffer_mm,
        shortfall_mm=result.shortfall_mm,
        drawdown_m=result.drawdown_m,
        days_until_buffer_empty=_days(result),
    )


@log_tool_call
async def calculate_supply_given_supply(
    ctx, input: SupplyInputGivenSupply
) -> SupplyOutput:
    """Wat doet deze inlaatcapaciteit met de waterstand en met de onvervulde watervraag?

    Aanvoeren = supply.
    """
    state = _state(input, input.supply_capacity_m3_per_sec)
    deficit = Deficit(
        input.deficit_mm_per_day,
        input.length_days,
        float("inf")
        if input.available_source_volume_m3 is None
        else float(input.available_source_volume_m3),
    )
    result = evaluate_supply(state, deficit)

    assumptions = assumed_defaults(input)
    caveats = model_caveats(
        input,
        is_drought=True,
        required_supply_volume_m3=_required_volume_m3(input, result),
        source_volume_is_modelled=input.available_source_volume_m3 is not None,
    )
    return SupplyOutput(
        data=_data(input, result),
        description=append_assumptions(
            describe_supply_forward(result, input, input.language),
            assumptions,
            input.language,
        ),
        status=result.status,
        assumptions=assumptions,
        caveats=caveats,
        priceless=[
            PricelessPost(**post)
            for post in priceless_posts(input, AanvoerenAction.name_nl)
        ],
        measure=_supply_measure(result),
        supply_capacity_m3_per_sec=result.supply_capacity_m3_per_sec,
        demand_mm=result.demand_mm,
        supplied_mm=result.supplied_mm,
        buffer_mm=result.buffer_mm,
        shortfall_mm=result.shortfall_mm,
        drawdown_m=result.drawdown_m,
        days_until_buffer_empty=_days(result),
    )
