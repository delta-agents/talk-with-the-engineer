"""
Example of a tool cal
"""

import numpy as np
from talk_with_the_engineer.models.modelset_rules_of_thumb.discharge import (
    DischargeInput,
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
async def discharge_tool(ctx, input: DischargeInput) -> DischargeOutput:
    """

    Given a return period return the amount of area needed to hold all the water.
    """

    rainfall_per_day, volume_rain_mm = get_rainfall(input)  # noqa: F821
    flow_per_day, model_matrix = get_discharge(input, rainfall_per_day)  # noqa: F821

    unaccounted_flow = np.zeros_like(flow_per_day)  # mm/d
    for index, dh in enumerate(flow_per_day):
        unaccounted_flow[index] = max(dh - input.discharge_capacity_mm_d, 0)
    area_m2_current_open_water = input.area_m2 * (input.percentage_open_water / 100)

    delta_h_m_flow = (
        (unaccounted_flow / 1000) * input.area_m2 / area_m2_current_open_water
    )  # mm/d * m2 = mm*m2/d / 1000 = m3/d
    # to see how much additional discharge we need to reduce this delta_h_m to
    # make cumulative instead of steps -> interested in the excess rise upto the maximum.
    sum_up_to_max_delta_h_m = np.sum(delta_h_m_flow[: np.argmax(delta_h_m_flow) + 1])

    extra_discharge_capacity_m3_d_required = (
        max((sum_up_to_max_delta_h_m - input.delta_h_available), 0)
        * area_m2_current_open_water
    )

    # moet dit een som zijn?
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
    data["delta_h_m_flow"] = delta_h_m_flow.tolist()

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

    description = (
        f"An extra discharge capacity is needed of {data['extra_discharge_capacity_m3_per_min_required']}mm"
        + f" with a return period of {input.return_period} years"
    )
    return DischargeOutput(
        data=data,
        description=description,
    )
