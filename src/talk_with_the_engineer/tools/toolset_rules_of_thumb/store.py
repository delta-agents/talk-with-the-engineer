"""Maatregel bergen: land omzetten in open water.

Grijpt aan op `pct_open_water` van de polder-toestand. Beide richtingen lopen over
dezelfde `simulate`: vooruit met `evaluate`, achteruit met `solve`.
"""

from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import BergenAction
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    assumed_defaults,
    supported_digits,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.models.modelset_rules_of_thumb.store import (
    StoreInputGivenArea,
    StoreInputGivenH,
    StoreOutput,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.descriptions import (
    append_assumptions,
    append_spread,
    describe_forward,
    describe_inverse,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.solve import (
    evaluate,
    forward_answer_for,
    inverse_answer_for,
    solve,
    spread_of,
    uncertainty_for,
)
from talk_with_the_engineer.utils.logging_utils import log_tool_call

SQUARE_METRES_PER_HECTARE = 10_000


def _rain(reference):
    """De bui zoals de tool hem rapporteert: bruto, het verlies, en netto per dag.

    Drie grootheden onder namen die zeggen welke het zijn. Eerder stonden hier
    `volume_rain_mm` (de statistiek, bruto) en `rainfall_per_day` (na aftrek van het
    zomerse neerslagverlies, dus netto) naast elkaar. Die telden in de zomer 20 mm
    verschil - en zomer is de standaardwaarde, dus juist de kale aanroep leverde uitvoer
    op die niet optelt en dus als rekenfout leest. Met het verlies erbij sluit de balans
    zichtbaar.

    De restpost is 0,02 mm op 86 mm: het patroon uit de tabel sommeert tot 0,9998 in
    plaats van 1. Zie test_the_rain_balance_closes.
    """
    return {
        "rain_volume_gross_mm": reference.volume_rain_mm,
        "rain_loss_mm": reference.rain_loss_mm,
        "rainfall_per_day_net_mm": reference.rainfall_per_day_mm.tolist(),
    }


def _data(result, rain):
    state_after = result.state_after
    return {
        # bruto - verlies = som van de netto dagreeks; zie _simulation_context
        **rain,
        # het antwoord: hoeveel open water er bij moet
        "delta_open_water_ha": result.magnitude,
        # de situatie na de maatregel
        "area_ha_required_open_water": state_after.area_open_water_ha,
        "area_m2_required_open_water": state_after.area_open_water_ha
        * SQUARE_METRES_PER_HECTARE,
        "new_area_percentage": state_after.pct_open_water,
        "magnitude_at_optimum_ha": result.magnitude_at_optimum,
    }


def _simulation_context(input):
    from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import simulate

    state = PolderState.from_water_system_input(input)
    reference = simulate(state, input)
    return state, _rain(reference)


@log_tool_call
async def calculate_store_given_h(ctx, input: StoreInputGivenH) -> StoreOutput:
    """Hoeveel open water is er nodig om de waterstandstijging onder een grens te houden?

    Bergen = store.
    """
    state, rain = _simulation_context(input)
    result = solve(state, input, BergenAction(), input.delta_h_available)

    assumptions = assumed_defaults(input)
    sensitivity, caveats = uncertainty_for(
        input,
        inverse_answer_for(BergenAction, "delta_h_available"),
        has_cost=result.cost is not None,
    )

    return StoreOutput.from_solve_result(
        result,
        sensitivity=sensitivity,
        caveats=caveats,
        data=_data(result, rain),
        description=append_assumptions(
            append_spread(
                describe_inverse(
                    result,
                    input.return_period,
                    input.language,
                    supported_digits(
                        spread_of(sensitivity, result.magnitude), result.magnitude
                    ),
                ),
                sensitivity,
                result.magnitude,
                "ha",
                input.language,
            ),
            assumptions,
            input.language,
        ),
        assumptions=assumptions,
    )


@log_tool_call
async def calculate_store_given_area(ctx, input: StoreInputGivenArea) -> StoreOutput:
    """Welke waterstandstijging hoort bij een gegeven hoeveelheid extra open water?

    Bergen = store.
    """
    state, rain = _simulation_context(input)
    action = BergenAction(delta_open_water_ha=input.area_available_ha)
    result = evaluate(state, input, action)

    assumptions = assumed_defaults(input)
    sensitivity, caveats = uncertainty_for(
        input,
        forward_answer_for(lambda: action),
        has_cost=result.cost is not None,
    )

    return StoreOutput.from_solve_result(
        result,
        sensitivity=sensitivity,
        caveats=caveats,
        data=_data(result, rain),
        description=append_assumptions(
            append_spread(
                describe_forward(
                    result,
                    input.return_period,
                    input.language,
                    supported_digits(
                        spread_of(sensitivity, result.magnitude), result.magnitude
                    ),
                ),
                sensitivity,
                result.magnitude,
                "ha",
                input.language,
            ),
            assumptions,
            input.language,
        ),
        assumptions=assumptions,
    )
