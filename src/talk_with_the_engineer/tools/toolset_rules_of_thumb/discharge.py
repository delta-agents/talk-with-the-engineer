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
from talk_with_the_engineer.utils.logging_utils import log_tool_call


@log_tool_call
async def discharge_tool(ctx, input: DischargeInput) -> DischargeOutput:
    """

    Given a return period return the amount of area needed to hold all the water.
    """

    # TODO:  Refactor disposal to discharge
    flow_per_day, volume_rain_mm, model_matrix, rainfall_per_day = get_rainfall(input)  # noqa: F821

    unaccounted_flow = np.zeros_like(flow_per_day)  # mm/d
    for index, dh in enumerate(flow_per_day):
        unaccounted_flow[index] = max(dh - input.disposal_capacity_mm_d, 0)
    area_m2_current_open_water = input.area_m2 * (input.percentage_open_water / 100)

    delta_h_m_flow = (
        (unaccounted_flow / 1000) * input.area_m2 / area_m2_current_open_water
    )  # mm/d * m2 = mm*m2/d / 1000 = m3/d
    # to see how much additional storage we need to reduce this delta_h_m to
    # TODO: make cumulative instead of steps -> interested in the maximum.
    disposal_capacity_m3_d_required = np.zeros_like(delta_h_m_flow)
    for index, dh in enumerate(delta_h_m_flow):
        disposal_capacity_m3_d_required[index] = (
            max((dh - input.delta_h_available), 0) * area_m2_current_open_water
        )

    # moet dit een som zijn?
    disposal_capacity_m3_per_min_required = disposal_capacity_m3_d_required / (60 * 24)
    disposal_capacity_m3_per_sec_required = disposal_capacity_m3_per_min_required / 60

    data = {}
    data["volume_rain_mm"] = float(volume_rain_mm)
    data["model_matrix"] = model_matrix.tolist()
    data["rainfall_per_day"] = rainfall_per_day.tolist()
    data["flow_per_day"] = flow_per_day.tolist()
    data["delta_h_m_flow"] = delta_h_m_flow.tolist()

    data["disposal_capacity_m3_d_required"] = disposal_capacity_m3_d_required.tolist()
    data["disposal_capacity_m3_per_min_required"] = (
        disposal_capacity_m3_per_min_required.tolist()
    )
    data["disposal_capacity_m3_per_sec_required"] = (
        disposal_capacity_m3_per_sec_required.tolist()
    )

    description = (
        f"Holding capacity of {data['volume_rain_mm']}mm"
        + f" with a return period of {input.return_period} years"
        + f" and a model matrix {data['model_matrix']}"
    )
    return DischargeOutput(
        data=data,
        description=description,
    )
