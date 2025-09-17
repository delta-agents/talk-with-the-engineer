"""
Calculates holding capacity
"""

import numpy as np
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
    while not stop:
        factor_delayed = 1 - factor
        area_polder = input.area_m2 * factor
        area_polder_delayed = input.area_m2 * factor_delayed
        area_m2_open_water = area_polder * (input.percentage_open_water / 100)
        area_m2_open_water_delayed = area_polder_delayed * (
            input.percentage_open_water / 100
        )

        delta_h_m_flow = (
            (unaccounted_flow / 1000) * area_polder / area_m2_open_water
        )  # mm/d * m2 = mm*m2/d / 1000 = m3/d

        delta_h_m_flow_delayed = (
            (unaccounted_flow_delayed / 1000)
            * area_polder_delayed
            / area_m2_open_water_delayed
        )  # mm/d * m2 = mm*m2/d / 1000 = m3/d

        delta_h_m_flow_combined = np.add(delta_h_m_flow, delta_h_m_flow_delayed)
        # to see how much additional discharge we need to reduce this delta_h_m to
        # make cumulative instead of steps -> interested in the excess rise upto the maximum.
        sum_up_to_max_delta_h_m = np.sum(
            delta_h_m_flow_combined[: np.argmax(delta_h_m_flow_combined)]
        )

        # stop criteria
        if sum_up_to_max_delta_h_m < input.delta_h_available:
            stop = True
        else:
            factor += 0.05
            if factor >= 1:
                stop = True
                factor = None

    data = {}
    data["volume_rain_mm"] = float(volume_rain_mm)
    data["model_matrix"] = model_matrix.tolist()
    data["rainfall_per_day"] = rainfall_per_day.tolist()
    data["flow_per_day"] = flow_per_day.tolist()
    data["flow_per_day_delayed"] = flow_per_day_delayed.tolist()
    data["area_polder_delayed"] = area_polder_delayed
    data["area_polder"] = area_polder

    description = (
        f"Holding area of {area_polder} m2 (factor {factor}) is needed to be held for {input.days_to_hold_discharge} extra days"
    )
    return HoldOutput(
        data=data,
        description=description,
    )
