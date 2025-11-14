"""
Example of a tool cal
"""

import numpy as np
from talk_with_the_engineer.models.modelset_rules_of_thumb.store import (
    StoreInputGivenH,
    StoreInputGivenArea,
    StoreOutput,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_rainfall import (
    get_rainfall,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_discharge import (
    get_discharge,
)
from talk_with_the_engineer.utils.logging_utils import log_tool_call


@log_tool_call
async def calculate_store_given_h(ctx, input: StoreInputGivenH) -> StoreOutput:
    """

    Given a return period returns the flow rate.
    """

    rainfall_per_day, volume_rain_mm = get_rainfall(input)  # noqa: F821
    flow_per_day, model_matrix = get_discharge(input, rainfall_per_day)  # noqa: F821

    unaccounted_flow = np.zeros_like(flow_per_day)
    for index, dh in enumerate(flow_per_day):
        unaccounted_flow[index] = max(dh - input.discharge_capacity_mm_d, 0)  # mm/d
    area_m2_current_open_water = input.area_m2 * (input.percentage_open_water / 100)

    # Find the day with maximum dh:
    # make a cumulative sum of the unaccounted flow
    # convert this to an area needed.
    # to see how much additional storage we need to reduce this delta_h_m to
    # make cumulative instead of steps -> interested in the excess rise upto the maximum.
    total_unaccounted_flow = (
        unaccounted_flow / 1000
    ) * input.area_m2  # mm/d * m2 = mm*m2/d / 1000 = m3/d
    # we then sum the flow up to the point of maximum delta_h_m
    # this gives us teh total volume that needs to be stored
    volume_sum_up_to_max_delta_h_m = np.sum(
        total_unaccounted_flow[: np.argmax(total_unaccounted_flow) + 1]
    )  # m3/d -> m3

    # with the known availible delta_h_m, we can calculate the current volume that can be stored
    volume_currently_stored = (
        input.delta_h_available * area_m2_current_open_water
    )  # m * m2 = m3
    # we subtract this from the total volume to be stored
    volume_to_be_stored = volume_sum_up_to_max_delta_h_m - volume_currently_stored
    # the difference is the volume that needs to be additionally stored
    area_m2_required_open_water = (
        volume_to_be_stored / input.delta_h_available
    )  # m3 / m = m2
    area_ha_required_open_water = area_m2_required_open_water / 10000

    data = {}
    data["volume_rain_mm"] = float(volume_rain_mm)
    data["model_matrix"] = model_matrix.tolist()
    data["rainfall_per_day"] = rainfall_per_day.tolist()
    data["flow_per_day"] = flow_per_day.tolist()
    data["total_unaccounted_flow"] = total_unaccounted_flow.tolist()
    data["area_ha_required_open_water"] = area_ha_required_open_water
    data["area_m2_required_open_water"] = area_m2_required_open_water

    # TODO: check if this is correct
    delta_h_cm = input.delta_h_available * 100
    area_percentage_required_open_water = (
        area_ha_required_open_water / input.area_ha * 100
    )
    return_period = input.return_period

    description_nl = (
        f"Om de waterstand voor een bui van eens per {return_period} jaar "
        f"met {delta_h_cm:.0f} cm te verlagen, "
        f"moet {area_percentage_required_open_water:.0f} % ({area_ha_required_open_water:.0f} ha) "
        f"van het gebied worden omgezet in open water. \n"
        f"Door de maatregel 'bergen' wordt de afvoer van neerslag verkleind ten opzicht van een situatie zonder maatregelen. \n"
    )

    description_en = (
        f"To lower the water level by {delta_h_cm:.0f} cm "
        f"for a rainfall event with a return period of {return_period} years, "
        f"we need {area_percentage_required_open_water:.0f} % ({area_ha_required_open_water:.0f} ha) "
        f"of the area to be converted to open water. \n"
        f"By the 'store' measure, the discharge of the rainfall is reduced."
    )
    if input.language == "nl":
        description = description_nl
    if input.language == "en":
        description = description_en
    
    return StoreOutput(
        data=data,
        description=description,
    )


@log_tool_call
async def calculate_store_given_area(ctx, input: StoreInputGivenArea) -> StoreOutput:
    """

    Given a return period returns the flow rate.
    """

    rainfall_per_day, volume_rain_mm = get_rainfall(input)  # noqa: F821
    flow_per_day, model_matrix = get_discharge(input, rainfall_per_day)  # noqa: F821

    discharge_capacity_mm_d = (
        input.discharge_capacity_m3_per_day / input.area_m2 * 1000
    )  # m3/d / m2 = m/d -> *1000 = mm/d
    unaccounted_flow = np.zeros_like(flow_per_day)
    for index, dh in enumerate(flow_per_day):
        unaccounted_flow[index] = max(dh - discharge_capacity_mm_d, 0)  # mm/d
    area_m2_current_open_water = input.area_m2 * (input.percentage_open_water / 100)

    # Find the day with maximum dh:
    # make a cumulative sum of the unaccounted flow
    # convert this to an area needed.
    # to see how what the result is of the additional storage we need use the delta_h_m to
    # make cumulative instead of steps -> interested in the excess rise upto the maximum.
    # we divide this maximum by the total area of open water (current + added)
    total_unaccounted_flow = (
        unaccounted_flow / 1000
    ) * input.area_m2  # mm/d * m2 = mm*m2/d / 1000 = m3/d
    # to see how much additional storage we need to reduce this delta_h_m to
    sum_q_up_to_max_delta_h_m = np.sum(
        total_unaccounted_flow[: np.argmax(total_unaccounted_flow) + 1]
    )  # m3/d -> m3

    # m3 / (m2 + m2) = m
    reduction_in_delta_h_m = sum_q_up_to_max_delta_h_m / (
        area_m2_current_open_water + input.area_available_m2
    )
    reduction_in_delta_h_cm = reduction_in_delta_h_m * 100
    data = {}
    data["volume_rain_mm"] = float(volume_rain_mm)
    data["model_matrix"] = model_matrix.tolist()
    data["rainfall_per_day"] = rainfall_per_day.tolist()
    data["flow_per_day"] = flow_per_day.tolist()
    data["total_unaccounted_flow"] = total_unaccounted_flow.tolist()
    data["reduction_in_delta_h_cm"] = reduction_in_delta_h_cm

    return_period = input.return_period
    area_available_ha = input.area_available_ha
    reduction_in_delta_h_cm = reduction_in_delta_h_cm


    description_nl = (
        f"Als met maatregel 'bergen' {area_available_ha:.0f} ha open water wordt gecreerd, "
        f"is de waterstandverlaging {reduction_in_delta_h_cm:.0f} cm "
        f"bij een bui van eens per {return_period} jaar. \n"
        f"Door de maatregel 'bergen' wordt de afvoer van neerslag verkleind ten opzicht van een situatie zonder maatregelen."
    )

    description_en = (
        f"When {area_available_ha:.0f} ha of open water is created with the 'store' measure, "
        f"the water level reduction is {reduction_in_delta_h_cm:.0f} cm "
        f"for a rainfall event with a return period of {return_period} years. \n"
        f"By the 'store' measure, the discharge of the rainfall is reduced."
    )

    if input.language == "nl":
        description = description_nl
    if input.language == "en":
        description = description_en
    
    return StoreOutput(
        data=data,
        description=description,
    )
