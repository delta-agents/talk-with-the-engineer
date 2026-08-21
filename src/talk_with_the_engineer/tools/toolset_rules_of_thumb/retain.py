"""Maatregel vasthouden: de afvoer van een deel van het land vertragen.

Grijpt aan op `retention_fraction` van de polder-toestand, een fractie van het
LANDoppervlak. Anders dan bergen en afvoeren heeft deze maatregel een optimum: voorbij een
zeker areaal valt de vertraagde afvoer van het ene deel samen met de piek van het andere en
wordt het weer slechter. `solve` zoekt daarom eerst dat optimum.
"""

from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
    VasthoudenAction,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.retain import (
    RetentionInputGivenArea,
    RetentionInputGivenH,
    RetentionOutput,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    assumed_defaults,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.descriptions import (
    append_assumptions,
    describe_forward,
    describe_inverse,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.solve import evaluate, solve
from talk_with_the_engineer.utils.logging_utils import log_tool_call


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
        # het antwoord: hoeveel land er voor retentie wordt ingericht
        "area_polder_delayed_ha": result.magnitude,
        "area_percentage_delayed": state_after.retention_fraction * 100,
        "days_to_retain": state_after.days_to_retain,
        "dh_reference_cm": result.dh_reference_m * 100,
        "dh_with_measure_cm": result.dh_with_measure_m * 100,
        "dh_reduction_cm": result.dh_reduction_m * 100,
        "feasible_dh_min_cm": result.feasible_dh_min_m * 100,
        "feasible_dh_max_cm": result.feasible_dh_max_m * 100,
        "magnitude_at_optimum_ha": result.magnitude_at_optimum,
    }


def _simulation_context(input):
    from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import simulate

    state = PolderState.from_water_system_input(
        input, days_to_retain=input.days_to_retain_discharge
    )
    reference = simulate(state, input)
    return state, _rain(reference)


@log_tool_call
async def calculate_retention_given_h(
    ctx, input: RetentionInputGivenH
) -> RetentionOutput:
    """Hoeveel land moet voor retentie worden ingericht om onder een grens te blijven?

    Vasthouden = retention.
    """
    state, rain = _simulation_context(input)
    result = solve(state, input, VasthoudenAction(), input.delta_h_available)

    assumptions = assumed_defaults(input)

    return RetentionOutput.from_solve_result(
        result,
        data=_data(result, rain),
        description=append_assumptions(
            describe_inverse(result, input.return_period, input.language),
            assumptions,
            input.language,
        ),
        assumptions=assumptions,
    )


@log_tool_call
async def calculate_retention_given_area(
    ctx, input: RetentionInputGivenArea
) -> RetentionOutput:
    """Welke waterstandstijging hoort bij een gegeven retentie-areaal?

    Vasthouden = retention.
    """
    if input.delta_area_ha < 0:
        raise ModelRetry(
            "delta_area_ha is het areaal dat voor retentie wordt ingericht en kan niet "
            "negatief zijn."
        )

    state, rain = _simulation_context(input)
    action = VasthoudenAction(delta_retention_ha=input.delta_area_ha)
    result = evaluate(state, input, action)

    assumptions = assumed_defaults(input)

    return RetentionOutput.from_solve_result(
        result,
        data=_data(result, rain),
        description=append_assumptions(
            describe_forward(result, input.return_period, input.language),
            assumptions,
            input.language,
        ),
        assumptions=assumptions,
    )
