"""
Calculates retention capacity
"""

import numpy as np
from pydantic_ai import ModelRetry
from talk_with_the_engineer.models.modelset_rules_of_thumb.retain import (
    RetentionInputGivenH,
    RetentionInputGivenArea,
    RetentionOutput,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_rainfall import (
    get_rainfall,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_discharge import (
    get_retained_discharge,
)
from talk_with_the_engineer.utils.logging_utils import log_tool_call


@log_tool_call
async def calculate_retention_given_h(
    ctx, input: RetentionInputGivenH
) -> RetentionOutput:
    """
    Given a return period return the amount of area needed to retain all the water.
    Specifically for a polder system.
    Retention = Vasthouden
    """
    # same calculation for all
    rainfall_per_day, volume_rain_mm = get_rainfall(input)  # mm
    flow_per_day, flow_per_day_delayed, model_matrix, model_matrix_delayed = (
        get_retained_discharge(input, rainfall_per_day)
    )  # mm/d

    unaccounted_flow = np.zeros_like(flow_per_day)  # mm/d
    for index, dh in enumerate(flow_per_day):
        unaccounted_flow[index] = max(dh - input.discharge_capacity_mm_d, 0)

    unaccounted_flow_delayed = np.zeros_like(flow_per_day_delayed)  # mm/d
    for index, dh in enumerate(flow_per_day_delayed):
        unaccounted_flow_delayed[index] = max(dh - input.discharge_capacity_mm_d, 0)

    # TODO: Tweak in order to calculate the area instead, for now do it iteratively
    factor = 0.05
    stop = False
    delta_h_m_critical_init = None
    while not stop:
        factor_delayed = 1 - factor
        area_polder = input.area_m2 * factor
        area_polder_delayed = input.area_m2 * factor_delayed
        # area_m2_open_water = area_polder * (input.percentage_open_water / 100)
        # area_m2_open_water_delayed = area_polder_delayed * (
        #     input.percentage_open_water / 100
        # )

        discharge_normal = (unaccounted_flow / 1000) * (
            area_polder
        )  # mm/d * m2 = mm*m2/d / 1000 = m3/d

        discharge_normal_delayed = (unaccounted_flow_delayed / 1000) * (
            area_polder_delayed
        )  # mm/d * m2 = mm*m2/d / 1000 = m3/d

        discharge_combined = np.add(discharge_normal, discharge_normal_delayed)
        # to see how much additional discharge we need to reduce this delta_h_m to
        # make cumulative instead of steps -> interested in the excess rise upto the maximum.
        sum_up_to_max_discharge = np.sum(
            discharge_combined[: np.argmax(discharge_combined) + 1]
        )  # m3/d -> m3
        area_open_water = input.area_m2 * (input.percentage_open_water / 100)
        sum_up_to_max_delta_h = sum_up_to_max_discharge / (
            area_open_water
        )  # m3 /  m2 = m (twijfel of area_m2_open_water_delayed)

        # stop criteria
        delta_h_m_critical = sum_up_to_max_delta_h - input.delta_h_available
        if delta_h_m_critical_init is None:
            delta_h_m_critical_init = delta_h_m_critical

        if delta_h_m_critical < input.delta_h_available:
            stop = True
        else:
            factor += 0.05
            if factor >= 1:
                stop = True

    if factor == 1:
        ModelRetry(
            "Factor reached 1, you would have to retain all the area, retry with adjusted parameters"
        )

    data = {}
    data["volume_rain_mm"] = float(volume_rain_mm)
    data["model_matrix"] = model_matrix.tolist()
    data["model_matrix_delayed"] = model_matrix_delayed.tolist()

    data["rainfall_per_day"] = rainfall_per_day.tolist()
    data["flow_per_day"] = flow_per_day.tolist()
    data["flow_per_day_delayed"] = flow_per_day_delayed.tolist()
    data["area_polder_delayed"] = area_polder_delayed
    data["area_polder"] = area_polder
    data["area_polder_delayed_ha"] = area_polder_delayed / 10_000
    data["area_polder_ha"] = area_polder / 10_000

    delta_h_cm = input.delta_h_available * 100
    delay_days = input.days_to_retain_discharge
    return_period = input.return_period
    area_percentage_delayed = factor_delayed * 100  # retention area percentage
    area_polder_delayed_ha = area_polder_delayed / 10_000  # retention area in hectares

    description_nl = (
        f"Met de maatregel 'vasthouden' (vertragen van neerslag met {delay_days} dagen) "
        f"kan de waterstandstijging minder dan {delta_h_cm:.0f} cm blijven "
        f"voor een bui eens per {return_period} jaar, "
        f"wanneer {area_percentage_delayed:.0f} % ({area_polder_delayed_ha:.0f} ha) van het gebied voor retentie wordt ingericht. \n"
        f"Door de maatregel 'vasthouden' wordt het maximum van de piekafvoer verkleind ten opzicht van een situatie zonder maatregelen."
    )

    description_en = (
        f"With the 'retention' measure (delaying rainfall by {delay_days} days) "
        f"the water level can remain below {delta_h_cm:.0f} cm "
        f"for a rainfall event with a return period of {return_period} years, "
        f"when {area_percentage_delayed:.0f} % ({area_polder_delayed_ha:.0f} ha) of the area is used for retention. \n"
        f"By the 'retention' measure, the maximum of the peak discharge is reduced."
    )

    if input.language == "nl":
        description = description_nl
    if input.language == "en":
        description = description_en

    return RetentionOutput(
        data=data,
        description=description,
    )


@log_tool_call
async def calculate_retention_given_area(
    ctx, input: RetentionInputGivenArea
) -> RetentionOutput:
    """
    Given a change in area for retention, return the resulting change in water level (can be reduction or increase).
    Specifically for a polder system.
    Retention = Vasthouden
    """
    # Get rainfall data and flow calculations (same as calculate_retention_given_h)
    # TODO: change to per hour instead of per day, for now keep it per day
    rainfall_per_day, volume_rain_mm = get_rainfall(input)
    flow_per_day, flow_per_day_delayed, model_matrix, model_matrix_delayed = (
        get_retained_discharge(input, rainfall_per_day)
    )
    # Change to TONs approach 
    # l/s/ha 

    # Calculate unaccounted flows (same as calculate_retention_given_h)
    unaccounted_flow = np.zeros_like(flow_per_day)  # mm/d
    for index, dh in enumerate(flow_per_day):
        unaccounted_flow[index] = max(dh - input.discharge_capacity_mm_d, 0)

    unaccounted_flow_delayed = np.zeros_like(flow_per_day_delayed)  # mm/d
    for index, dh in enumerate(flow_per_day_delayed):
        unaccounted_flow_delayed[index] = max(dh - input.discharge_capacity_mm_d, 0)

    area_polder = input.area_m2  # All area for immediate discharge
    area_polder_delayed = input.delta_area_m2  # No area for retention

    discharge_normal_baseline = (unaccounted_flow / 1000) * (
        area_polder
    )  # mm/d * m2 = mm*m2/d / 1000 = m3/d

    discharge_normal_delayed_baseline = (unaccounted_flow_delayed / 1000) * (
        area_polder_delayed
    )  # mm/d * m2 = mm*m2/d / 1000 = m3/d

    discharge_combined = np.add(
        discharge_normal_baseline, discharge_normal_delayed_baseline
    )

    # to see how much additional discharge we need to reduce this delta_h_m to
    # make cumulative instead of steps -> interested in the excess rise upto the maximum.
    sum_up_to_max_discharge = np.sum(
        discharge_combined[: np.argmax(discharge_combined) + 1]
    )  # sum(m3/d) -> m3

    area_open_water = input.area_m2 * (input.percentage_open_water / 100)

    change_in_delta_h_m = sum_up_to_max_discharge / area_open_water
    # m3 / m2 = m

    change_in_delta_h_cm = change_in_delta_h_m * 100  # convert to cm

    # Prepare data dictionary
    data = {}
    data["volume_rain_mm"] = float(volume_rain_mm)
    data["model_matrix"] = model_matrix.tolist()
    data["model_matrix_delayed"] = model_matrix_delayed.tolist()
    data["rainfall_per_day"] = rainfall_per_day.tolist()
    data["flow_per_day"] = flow_per_day.tolist()
    data["flow_per_day_delayed"] = flow_per_day_delayed.tolist()
    data["delta_area_ha"] = input.delta_area_ha
    data["change_in_delta_h_cm"] = change_in_delta_h_cm
    data["change_in_delta_h_m"] = change_in_delta_h_m

    delay_days = input.days_to_retain_discharge
    delta_area_ha = input.delta_area_ha
    return_period = input.return_period

    description_nl = (
        f"Als de maatregel 'vasthouden' (vertragen van neerslag met {delay_days} dagen) "
        f"wordt toegepast op {delta_area_ha:.0f} ha, "
        f"is de waterstandstijging {change_in_delta_h_cm:.0f} cm "
        f"bij een bui van eens per {return_period} jaar. \n"
        f"Door de maatregel 'vasthouden' wordt het maximum van de piekafvoer verkleind ten opzichte van een situatie zonder maatregelen."
    )

    description_en = (
        f"When the 'retention' measure (delaying rainfall by {delay_days} days) "
        f"is applied to {delta_area_ha:.0f} ha, "
        f"the water level increase is {change_in_delta_h_cm:.0f} cm "
        f"for a rainfall event with a return period of {return_period} years. \n"
        f"By the 'retention' measure, the maximum of the peak discharge is reduced."
    )

    if input.language == "nl":
        description = description_nl
    if input.language == "en":
        description = description_en

    return RetentionOutput(
        data=data,
        description=description,
    )
