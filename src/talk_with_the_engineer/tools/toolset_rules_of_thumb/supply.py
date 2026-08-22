"""Maatregel aanvoeren: meer inlaatcapaciteit.

Grijpt aan op `capacity_in_m3_per_sec` van de verbinding, en gebruikt dezelfde rekenkern
als de andere vijf tools met de klem gespiegeld. Zie `simulate_deficit`.
"""

from dataclasses import dataclass

from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    assumed_defaults,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.connection import Connection
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


def _state(input, supply_capacity_m3_per_sec: float = 0.0) -> PolderState:
    """Bouw de toestand, met de bruikbare diepte onder streefpeil als peilmarge.

    `drawdown_available_m` en `level_margin_m` zijn dezelfde grootheid vanuit twee kanten
    bekeken: hoe diep het peil mag zakken. Aan de toolgrens heet hij naar wat de beller
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
    per_sec = result.supply_capacity_m3_per_sec
    return {
        # de vraag waar dit antwoord op reageert
        "deficit_mm_per_day": input.deficit_mm_per_day,
        "length_days": input.length_days,
        "demand_mm": result.demand_mm,
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
        # waar het water vandaan komt: de drie posten tellen op tot demand_mm
        "supplied_mm": result.supplied_mm,
        "buffer_mm": result.buffer_mm,
        "shortfall_mm": result.shortfall_mm,
        # en wat dat met het peil doet
        "drawdown_cm": result.drawdown_m * 100,
        "drawdown_available_cm": input.drawdown_available_m * 100,
        "days_until_buffer_empty": _days(result),
    }


def _days(result) -> float | None:
    """`inf` is geen geldige JSON, dus een periode die het volhoudt wordt `None`."""
    days = result.days_until_buffer_empty
    return None if days == float("inf") else days


@log_tool_call
async def calculate_supply_given_h(ctx, input: SupplyInputGivenH) -> SupplyOutput:
    """Hoeveel inlaatcapaciteit dekt het neerslagtekort zonder dat het peil te diep zakt?

    Aanvoeren = supply.
    """
    state = _state(input)
    deficit = Deficit(input.deficit_mm_per_day, input.length_days)
    result = solve_supply(state, deficit)

    assumptions = assumed_defaults(input)
    return SupplyOutput(
        data=_data(input, result),
        description=append_assumptions(
            describe_supply_inverse(result, input, input.language),
            assumptions,
            input.language,
        ),
        status=result.status,
        assumptions=assumptions,
        state_before=result.state_before,
        state_after=result.state_after,
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
    """Wat doet deze inlaatcapaciteit met het peil en met de onvervulde watervraag?

    Aanvoeren = supply.
    """
    state = _state(input, input.supply_capacity_m3_per_sec)
    deficit = Deficit(input.deficit_mm_per_day, input.length_days)
    result = evaluate_supply(state, deficit)

    assumptions = assumed_defaults(input)
    return SupplyOutput(
        data=_data(input, result),
        description=append_assumptions(
            describe_supply_forward(result, input, input.language),
            assumptions,
            input.language,
        ),
        status=result.status,
        assumptions=assumptions,
        state_before=result.state_before,
        state_after=result.state_after,
        supply_capacity_m3_per_sec=result.supply_capacity_m3_per_sec,
        demand_mm=result.demand_mm,
        supplied_mm=result.supplied_mm,
        buffer_mm=result.buffer_mm,
        shortfall_mm=result.shortfall_mm,
        drawdown_m=result.drawdown_m,
        days_until_buffer_empty=_days(result),
    )
