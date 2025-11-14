"""
Example of a tool cal
"""

import numpy as np
from talk_with_the_engineer.models.modelset_rules_of_thumb.discharge import (
    DischargeInputGivenH,
    DischargeInputGivenDischarge,
    DischargeOutput,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_rainfall import (
    get_rainfall,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_discharge import (
    get_discharge,
)
from talk_with_the_engineer.utils.logging_utils import log_tool_call


@log_tool_call
async def calculate_discharge_given_h(
    ctx, input: DischargeInputGivenH
) -> DischargeOutput:
    """

    Given a change in water level, return the amount of discharge capacity needed to achieve this change.
    Discharge = Afvoeren
    """

    rainfall_per_day, volume_rain_mm = get_rainfall(input)  # noqa: F821
    flow_per_day, model_matrix = get_discharge(input, rainfall_per_day)  # noqa: F821

    unaccounted_flow = np.zeros_like(flow_per_day)  # mm/d
    for index, dh in enumerate(flow_per_day):
        unaccounted_flow[index] = max(dh - input.discharge_capacity_mm_d, 0)  # mm/d
    area_m2_current_open_water = input.area_m2 * (input.percentage_open_water / 100)

    total_unaccounted_flow = (
        unaccounted_flow / 1000
    ) * input.area_m2  # mm/d * m2 = mm*m2/d / 1000 = m3/d
    # to see how much additional discharge we need to reduce this delta_h_m to
    # make cumulative instead of steps -> interested in the excess rise upto the maximum.
    sum_up_to_max_delta_h_m = np.sum(
        total_unaccounted_flow[: np.argmax(total_unaccounted_flow) + 1]
    )  # m3/d -> m3
    n_days_excess_flow = np.argmax(total_unaccounted_flow) + 1
    # hier zit al een aanname van vooruit malen in
    # we berekenen de totale hoeveelheid water dat we kwijt moeten
    # en delen dat door het aantal dagen dat we die hoeveelheid kwijt moeten
    # in de praktijk zal de piek meer zijn,
    # maar deze kunnen we opvangen door in de dagen dat we niet op de piek zitten alvast vooruit te malen
    extra_discharge_capacity_m3_d_required = (
        (
            max(
                (
                    (sum_up_to_max_delta_h_m / area_m2_current_open_water)
                    - input.delta_h_available
                ),
                0,
            )
        )
        * area_m2_current_open_water
        / n_days_excess_flow
    )  # (m3/ m2 -> m), (m-m = m), (m * m2 = m3), m3 / d = m3/d

    extra_discharge_capacity_mm_d_required = (
        extra_discharge_capacity_m3_d_required / input.area_m2 * 1000
    )  # m3/d/m2=m/d/1000=mm/d
    extra_discharge_capacity_m3_per_min_required = (
        extra_discharge_capacity_m3_d_required / (60 * 24)
    )
    extra_discharge_capacity_m3_per_sec_required = (
        extra_discharge_capacity_m3_per_min_required / 60
    )

    data = {}
    data["volume_rain_mm"] = float(volume_rain_mm)
    data["model_matrix"] = model_matrix.tolist()
    data["rainfall_per_day"] = rainfall_per_day.tolist()
    data["flow_per_day"] = flow_per_day.tolist()
    data["total_unaccounted_flow"] = total_unaccounted_flow.tolist()

    data["extra_discharge_capacity_m3_d_required"] = (
        extra_discharge_capacity_m3_d_required
    )
    data["extra_discharge_capacity_mm_d_required"] = (
        extra_discharge_capacity_mm_d_required
    )
    data["extra_discharge_capacity_m3_per_min_required"] = (
        extra_discharge_capacity_m3_per_min_required
    )
    data["extra_discharge_capacity_m3_per_sec_required"] = (
        extra_discharge_capacity_m3_per_sec_required
    )

    # TODO: check if this is correct
    delta_h_cm = input.delta_h_available * 100
    extra_discharge_capacity_m3_per_min_required = (
        extra_discharge_capacity_m3_per_min_required
    )
    total_discharge_capactiy_m3_per_min = (
        extra_discharge_capacity_m3_per_min_required
        + input.discharge_capacity_m3_per_min
    )
    total_discharge_capactiy_mm_d = (
        #                             min * 60 = hr, * 24 = d, * 1000 = mm
        total_discharge_capactiy_m3_per_min * 60 * 24 / input.area_m2 * 1000
    )

    return_period = input.return_period
    delta_h_cm = input.delta_h_available * 100
    discharge_capacity_m3_per_min = input.discharge_capacity_m3_per_min
    extra_discharge_capacity_percentage = (
        extra_discharge_capacity_m3_per_min_required
        / discharge_capacity_m3_per_min
        * 100
    )

    description_nl = (
        f"Om de waterstand voor een bui van eens per {return_period} jaar "
        f"met {delta_h_cm:.0f} cm te verlagen, "
        f"moet de huidige afvoercapaciteit ({discharge_capacity_m3_per_min:.0f} m3/min) "
        f"met {extra_discharge_capacity_percentage:.0f} % ({total_discharge_capactiy_m3_per_min:.0f} m3/min) toenemen. \n"
        f"Door de maatregel 'afvoeren' wordt de capaciteit {total_discharge_capactiy_mm_d:.0f} mm/dag."
    )

    description_en = (
        f"To lower the water level by {delta_h_cm:.0f} cm "
        f"for a rainfall event with a return period of {return_period} years, "
        f"we need to increase the current discharge capacity ({discharge_capacity_m3_per_min:.0f} m3/min) "
        f"with {extra_discharge_capacity_percentage:.0f} % ({extra_discharge_capacity_m3_per_min_required:.0f} m3/min). \n"
        f"By the 'discharge' measure, the discharge capacity is increased to {total_discharge_capactiy_mm_d:.0f} mm/day."
    )
    if input.language == "nl":
        description = description_nl
    if input.language == "en":
        description = description_en

    return DischargeOutput(
        data=data,
        description=description,
    )


@log_tool_call
async def calculate_discharge_given_discharge(
    ctx, input: DischargeInputGivenDischarge
) -> DischargeOutput:
    """

    Given a change in discharge capacity, return the resulting change in water level (can be reduction or increase).
    Discharge = Afvoeren
    """
    # Get rainfall data and flow calculations (same as calculate_discharge_given_h)
    rainfall_per_day, volume_rain_mm = get_rainfall(input)
    flow_per_day, model_matrix = get_discharge(input, rainfall_per_day)

    area_m2_current_open_water = input.area_m2 * (input.percentage_open_water / 100)

    # Calculate unaccounted flow with CURRENT discharge capacity
    unaccounted_flow_current = np.zeros_like(flow_per_day)  # mm/d
    for index, dh in enumerate(flow_per_day):
        unaccounted_flow_current[index] = max(
            dh - input.discharge_capacity_mm_d - input.delta_discharge_capacity_mm_d, 0
        )  # mm/d

    total_unaccounted_flow_current = (
        unaccounted_flow_current / 1000
    ) * input.area_m2  # mm/d * m2 = mm*m2/d / 1000 = m3/d

    max_idx_current = np.argmax(total_unaccounted_flow_current)
    sum_up_to_max_delta_h_m_current = np.sum(
        total_unaccounted_flow_current[: max_idx_current + 1]
    )  # m3/d -> ,2

    # Calculate unaccounted flow with NEW discharge capacity
    # Calculate change in water level
    # Positive delta_discharge -> less unaccounted flow -> lower water level (reduction)
    # Negative delta_discharge -> more unaccounted flow -> higher water level (increase)
    change_in_delta_h_m = (
        sum_up_to_max_delta_h_m_current
    ) / area_m2_current_open_water  # m3 / m2 = m
    change_in_delta_h_cm = change_in_delta_h_m * 100  # convert to cm

    # Prepare data dictionary
    data = {}
    data["volume_rain_mm"] = float(volume_rain_mm)
    data["model_matrix"] = model_matrix.tolist()
    data["rainfall_per_day"] = rainfall_per_day.tolist()
    data["flow_per_day"] = flow_per_day.tolist()
    data["unaccounted_flow_current"] = unaccounted_flow_current.tolist()
    data["total_unaccounted_flow_current"] = total_unaccounted_flow_current.tolist()
    data["delta_discharge_capacity_m3_per_min"] = (
        input.delta_discharge_capacity_m3_per_min
    )
    data["change_in_delta_h_cm"] = change_in_delta_h_cm
    data["change_in_delta_h_m"] = change_in_delta_h_m

    return_period = input.return_period
    delta_discharge_capacity_m3_per_min = input.delta_discharge_capacity_m3_per_min
    new_discharge_capacity_mm_d = (
        input.discharge_capacity_mm_d - input.delta_discharge_capacity_mm_d
    )

    description_nl = (
        f"Als met de maatregel 'afvoeren' de afvoercapaciteit wordt uitgebreid met {delta_discharge_capacity_m3_per_min:.0f} m3/min, "
        f"is de waterstandverlaging {change_in_delta_h_cm:.0f} cm "
        f"bij een bui van eens per {return_period} jaar. \n"
        f"Door de maatregel 'afvoeren' wordt de totale capaciteit {new_discharge_capacity_mm_d:.0f} mm/dag."
    )
    description_en = (
        f"When the 'discharge' measure increases the discharge capacity by {delta_discharge_capacity_m3_per_min:.0f} m3/min, "
        f"the water level reduction is {change_in_delta_h_cm:.0f} cm "
        f"for a rainfall event with a return period of {return_period} years. \n"
        f"By the 'discharge' measure, the total discharge capacity is increased to {new_discharge_capacity_mm_d:.0f} mm/day."
    )

    if input.language == "nl":
        description = description_nl
    if input.language == "en":
        description = description_en

    return DischargeOutput(
        data=data,
        description=description,
    )
