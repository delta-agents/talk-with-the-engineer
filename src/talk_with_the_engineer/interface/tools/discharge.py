"""Maatregel afvoeren: meer gemaalcapaciteit.

Grijpt aan op `pump_capacity_m3_per_sec` van de polder-toestand.
"""

from pydantic_ai import ModelRetry

from talk_with_the_engineer.core.actions import DischargeAction
from talk_with_the_engineer.interface.schemas.discharge import (
    DischargeInputGivenDischarge,
    DischargeInputGivenH,
    DischargeOutput,
)
from talk_with_the_engineer.epistemics.assumptions import assumed_defaults
from talk_with_the_engineer.epistemics.priceless import priceless_posts
from talk_with_the_engineer.epistemics.uncertainty import supported_digits
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.interface.descriptions import (
    append_assumptions,
    append_spread,
    describe_forward,
    describe_inverse,
)
from talk_with_the_engineer.core.inverse import (
    evaluate,
    solve,
)
from talk_with_the_engineer.epistemics.uncertainty import (
    forward_answer_for,
    inverse_answer_for,
    spread_of,
    uncertainty_for,
)
from talk_with_the_engineer.utils.logging_utils import log_tool_call

SECONDS_PER_MINUTE = 60
MINUTES_PER_DAY = 60 * 24


def _data(input, result, rain):
    extra_m3_per_sec = result.magnitude
    extra_m3_per_min = extra_m3_per_sec * SECONDS_PER_MINUTE
    extra_m3_per_day = extra_m3_per_min * MINUTES_PER_DAY
    total_m3_per_min = result.state_after.pump_capacity_m3_per_sec * SECONDS_PER_MINUTE
    return {
        # bruto - verlies = som van de netto dagreeks; zie _simulation_context
        **rain,
        # het antwoord: de uitbreiding van de capaciteit
        "extra_discharge_capacity_m3_per_sec_required": extra_m3_per_sec,
        "extra_discharge_capacity_m3_per_min_required": extra_m3_per_min,
        "extra_discharge_capacity_m3_d_required": extra_m3_per_day,
        "extra_discharge_capacity_mm_d_required": extra_m3_per_day
        / input.area_m2
        * 1000,
        # de situatie na de maatregel
        "total_discharge_capacity_m3_per_min": total_m3_per_min,
        "total_discharge_capacity_mm_d": total_m3_per_min
        * MINUTES_PER_DAY
        / input.area_m2
        * 1000,
        "magnitude_at_optimum_m3_per_sec": result.magnitude_at_optimum,
    }


def _simulation_context(input):
    from talk_with_the_engineer.core.transition import (
        simulate,
        storm_shape,
    )

    state = PolderState.from_water_system_input(input)
    reference = simulate(state, input.to_storm())
    return state, storm_shape(reference, input.to_storm())


@log_tool_call
async def calculate_discharge_given_h(
    ctx, input: DischargeInputGivenH
) -> DischargeOutput:
    """Hoeveel extra gemaalcapaciteit houdt de waterstandstijging onder een grens?

    Afvoeren = discharge.
    """
    state, rain = _simulation_context(input)
    result = solve(state, input.to_storm(), DischargeAction(), input.delta_h_available)

    assumptions = assumed_defaults(input)
    sensitivity, caveats = uncertainty_for(
        input,
        inverse_answer_for(DischargeAction, "delta_h_available"),
        has_cost=result.cost is not None,
    )

    return DischargeOutput.from_solve_result(
        result,
        sensitivity=sensitivity,
        caveats=caveats,
        data=_data(input, result, rain),
        priceless=priceless_posts(input, result.measure_nl),
        description=append_assumptions(
            append_spread(
                describe_inverse(
                    result,
                    input,
                    input.language,
                    supported_digits(
                        spread_of(sensitivity, result.magnitude), result.magnitude
                    ),
                ),
                sensitivity,
                result.magnitude,
                "m3/s",
                input.language,
            ),
            assumptions,
            input.language,
        ),
        assumptions=assumptions,
    )


@log_tool_call
async def calculate_discharge_given_discharge(
    ctx, input: DischargeInputGivenDischarge
) -> DischargeOutput:
    """Welke waterstandstijging hoort bij een gegeven uitbreiding van de gemaalcapaciteit?

    Afvoeren = discharge.
    """
    if input.delta_discharge_capacity_m3_per_sec < 0:
        raise ModelRetry(
            "delta_discharge_capacity is de uitbreiding van de capaciteit en kan niet "
            "negatief zijn. Bedoel je een kleiner gemaal, geef dan de kleinere "
            "discharge_capacity op. Bedoel je water dat de andere kant op gaat, dan is "
            "dat aanvoer: gebruik calculate_supply_given_supply."
        )

    state, rain = _simulation_context(input)
    action = DischargeAction(
        delta_pump_capacity_m3_per_sec=input.delta_discharge_capacity_m3_per_sec
    )
    result = evaluate(state, input.to_storm(), action)

    assumptions = assumed_defaults(input)
    sensitivity, caveats = uncertainty_for(
        input,
        forward_answer_for(action),
        has_cost=result.cost is not None,
    )

    return DischargeOutput.from_solve_result(
        result,
        sensitivity=sensitivity,
        caveats=caveats,
        data=_data(input, result, rain),
        priceless=priceless_posts(input, result.measure_nl),
        description=append_assumptions(
            append_spread(
                describe_forward(
                    result,
                    input,
                    input.language,
                    supported_digits(
                        spread_of(sensitivity, result.magnitude), result.magnitude
                    ),
                ),
                sensitivity,
                result.magnitude,
                "m3/s",
                input.language,
            ),
            assumptions,
            input.language,
        ),
        assumptions=assumptions,
    )
