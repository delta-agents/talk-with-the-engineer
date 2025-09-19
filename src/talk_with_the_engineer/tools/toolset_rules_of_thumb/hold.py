"""
Calculates holding capacity
"""

import numpy as np
from pydantic_ai import ModelRetry
from talk_with_the_engineer.models.modelset_rules_of_thumb.hold import (
    HoldInput,
    HoldOutput,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_rainfall import (
    get_rainfall,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_discharge import (
    get_held_discharge,
)
from talk_with_the_engineer.utils.logging_utils import log_tool_call


# TODO: refactor to polder_hold_tool when we add brook = beek
# TODO: refactor to remove _tool
@log_tool_call
async def hold_tool(ctx, input: HoldInput) -> HoldOutput:
    """
    Given a return period return the amount of area needed to hold all the water.
    Specifically for a polder system.
    Hold = Vasthouden
    """
    # same calculation for all
    rainfall_per_day, volume_rain_mm = get_rainfall(input)  # mm
    flow_per_day, flow_per_day_delayed, model_matrix, model_matrix_delayed = (
        get_held_discharge(input, rainfall_per_day)
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

        discharge_normal = (
            (unaccounted_flow / 1000) * (area_polder)
        )  # mm/d * m2 = mm*m2/d / 1000 = m3/d

        discharge_normal_delayed = (
            (unaccounted_flow_delayed / 1000)
            * (area_polder_delayed)
        )  # mm/d * m2 = mm*m2/d / 1000 = m3/d

        discharge_combined = np.add(discharge_normal, discharge_normal_delayed)
        # to see how much additional discharge we need to reduce this delta_h_m to
        # make cumulative instead of steps -> interested in the excess rise upto the maximum.
        sum_up_to_max_discharge = np.sum(
            discharge_combined[: np.argmax(discharge_combined) + 1]
        ) # m3/d -> m3
        area_open_water = input.area_m2 * (input.percentage_open_water / 100)
        sum_up_to_max_delta_h = sum_up_to_max_discharge / (area_open_water) # m3 /  m2 = m (twijfel of area_m2_open_water_delayed)

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
            "Factor reached 1, you would have to hold all the area, retry with adjusted parameters"
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

    description = f"An area of {(area_polder / 10_000):.2f} ha is needed where water is held for {input.days_to_hold_discharge} extra days in order to reduce the waterlevel with {delta_h_m_critical_init:.2f}m"
    return HoldOutput(
        data=data,
        description=description,
    )
