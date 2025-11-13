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
async def calculate_retention_given_h(ctx, input: RetentionInputGivenH) -> RetentionOutput:
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

    # TODO: check if this is correct
    delta_h_cm = delta_h_m_critical_init * 100  # ?????
    delay_days = input.days_to_retain_discharge
    area_percentage = factor * 100
    area_ha = area_polder / 10_000

    # Determine description based on sign of delta_h_cm
    if delta_h_cm >= 0:
        level_change = "reduction"
    else:
        level_change = "increase"
    
    description = (
        f"To achieve a water level {level_change} of {abs(delta_h_cm):.0f} cm using the 'retention' measure, "
        f"we need to utilize {area_percentage:.0f} % of the available surface area (that is {area_ha:.0f} ha) "
        f"while delaying the retained water by {delay_days} days."

    )
    return RetentionOutput(
        data=data,
        description=description,
    )

@log_tool_call
async def calculate_retention_given_area(ctx, input: RetentionInputGivenArea) -> RetentionOutput:
    """
    Given a change in area for retention, return the resulting change in water level (can be reduction or increase).
    Specifically for a polder system.
    Retention = Vasthouden
    """
    # Get rainfall data and flow calculations (same as calculate_retention_given_h)
    rainfall_per_day, volume_rain_mm = get_rainfall(input)
    flow_per_day, flow_per_day_delayed, model_matrix, model_matrix_delayed = (
        get_retained_discharge(input, rainfall_per_day)
    )
    
    # Calculate unaccounted flows (same as calculate_retention_given_h)
    unaccounted_flow = np.zeros_like(flow_per_day)  # mm/d
    for index, dh in enumerate(flow_per_day):
        unaccounted_flow[index] = max(dh - input.discharge_capacity_mm_d, 0)
    
    unaccounted_flow_delayed = np.zeros_like(flow_per_day_delayed)  # mm/d
    for index, dh in enumerate(flow_per_day_delayed):
        unaccounted_flow_delayed[index] = max(dh - input.discharge_capacity_mm_d, 0)
    
    # Convert delta_area_ha to m2
    delta_area_m2 = input.delta_area_ha * 10000  # ha to m2
    
    # BASELINE SCENARIO: All area for immediate discharge (no retention)
    # area_polder = area for immediate discharge
    # area_polder_delayed = area for retention/delayed discharge
    area_polder_baseline = input.area_m2  # All area for immediate discharge
    area_polder_delayed_baseline = 0.0  # No area for retention
    
    discharge_normal_baseline = (unaccounted_flow / 1000) * (
        area_polder_baseline
    )  # mm/d * m2 = mm*m2/d / 1000 = m3/d
    
    discharge_normal_delayed_baseline = (unaccounted_flow_delayed / 1000) * (
        area_polder_delayed_baseline
    )  # mm/d * m2 = mm*m2/d / 1000 = m3/d
    
    discharge_combined_baseline = np.add(discharge_normal_baseline, discharge_normal_delayed_baseline)
    
    # Calculate cumulative discharge up to maximum for baseline scenario
    if len(discharge_combined_baseline) > 0 and np.max(discharge_combined_baseline) > 0:
        max_idx_baseline = np.argmax(discharge_combined_baseline)
        sum_up_to_max_discharge_baseline = np.sum(
            discharge_combined_baseline[: max_idx_baseline + 1]
        )  # m3
    else:
        sum_up_to_max_discharge_baseline = 0.0  # m3
    
    # NEW SCENARIO: With delta_area for retention
    # delta_area_ha positive -> adding area for retention (delayed discharge)
    # delta_area_ha negative -> removing area from retention (back to immediate discharge)
    # Clamp: can't have negative retention area, and can't exceed total area
    area_polder_delayed_new = max(0.0, min(input.area_m2, delta_area_m2))  # Clamp between 0 and total area
    area_polder_new = input.area_m2 - area_polder_delayed_new
    
    discharge_normal_new = (unaccounted_flow / 1000) * (
        area_polder_new
    )  # mm/d * m2 = mm*m2/d / 1000 = m3/d
    
    discharge_normal_delayed_new = (unaccounted_flow_delayed / 1000) * (
        area_polder_delayed_new
    )  # mm/d * m2 = mm*m2/d / 1000 = m3/d
    
    discharge_combined_new = np.add(discharge_normal_new, discharge_normal_delayed_new)
    
    # Calculate cumulative discharge up to maximum for new scenario
    if len(discharge_combined_new) > 0 and np.max(discharge_combined_new) > 0:
        max_idx_new = np.argmax(discharge_combined_new)
        sum_up_to_max_discharge_new = np.sum(
            discharge_combined_new[: max_idx_new + 1]
        )  # m3
    else:
        sum_up_to_max_discharge_new = 0.0  # m3
    
    # Calculate change in water level
    area_open_water = input.area_m2 * (input.percentage_open_water / 100)
    
    # Positive delta_area -> more retention -> less discharge -> lower water level (reduction)
    # Negative delta_area -> less retention -> more discharge -> higher water level (increase)
    sum_up_to_max_delta_h_baseline = sum_up_to_max_discharge_baseline / area_open_water  # m3 / m2 = m
    sum_up_to_max_delta_h_new = sum_up_to_max_discharge_new / area_open_water  # m3 / m2 = m
    
    change_in_delta_h_m = sum_up_to_max_delta_h_baseline - sum_up_to_max_delta_h_new  # m
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
    data["delta_area_m2"] = delta_area_m2
    data["area_polder_new"] = area_polder_new
    data["area_polder_delayed_new"] = area_polder_delayed_new
    data["discharge_combined_baseline"] = discharge_combined_baseline.tolist()
    data["discharge_combined_new"] = discharge_combined_new.tolist()
    data["change_in_delta_h_cm"] = change_in_delta_h_cm
    data["change_in_delta_h_m"] = change_in_delta_h_m
    
    # Determine description based on sign of delta
    if input.delta_area_ha >= 0:
        change_direction = "an increase"
        level_change = "reduction"
    else:
        change_direction = "a decrease"
        level_change = "increase"
    
    # area_ha = abs(area_polder_new) / 10000  # totalling to
    delay_days = input.days_to_retain_discharge
    
    description = (
        f"With the 'retention' measure, {change_direction} in retention area of "
        f"{abs(input.delta_area_ha):.0f} ha "
        f"results in a water level {level_change} of {abs(change_in_delta_h_cm):.0f} cm "
        f"for a rainfall event with a return period of 1x per {input.return_period} years "
        f"(using a delayed discharge of {delay_days} days for the retained water)."
    )
    
    return RetentionOutput(
        data=data,
        description=description,
    )