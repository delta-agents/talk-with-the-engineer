"""
Example of a tool cal
"""

import pandas as pd

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
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_calculations import (
    clcMax,
)
# eeste opzet
prcAlst = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]  # % toename afvoercapaciteit
maxMtrLst = [
    -9.99,
    -9.99,
    -9.99,
    -9.99,
    -9.99,
    -9.99,
    -9.99,
    -9.99,
    -9.99,
    -9.99,
    -9.99,
]  # max peiloverschreiding maatregel


@log_tool_call
async def calculate_store_given_h(ctx, input: StoreInputGivenH) -> StoreOutput:
    """

    Given a return period returns the flow rate.
    """

    rainfall_per_day, volume_rain_mm = get_rainfall(input)  # noqa: F821
    flow_per_hour_l_s_ha, model_matrix = get_discharge(input, rainfall_per_day)  # noqa: F821

    effect = pd.DataFrame(
        list(zip(prcAlst, maxMtrLst)), columns=["percA [%]", "dH_mtr [m]"]
    )

    Qd_file = pd.read_csv(rf"C:\Data\Python\Delta Agents\Talk With Engineer\talk-with-the-engineer\scripts\scripts_Ton\drainage.csv", sep=",", encoding="latin1")

     # VB polder
    totA = input.area_ha #4000  # ha
    area_open_water = input.percentage_open_water / 100 * totA  # ha open water (3,5%)
    area_land = totA - area_open_water  # ha overig
    pmpQ = input.discharge_capacity_m3_per_sec  # m3/s capaciteit
    totWlvl_ref = 0
    totWlvl_mtr = 0
    prcA = 0

    # Qd = pd.DataFrame(flow_per_hour_l_s_ha, columns=["drainage [l/s/ha]"])
    Qd = Qd_file.copy()
    
    effect["dH_mtr [m]"] = effect["percA [%]"].apply(lambda x: clcMax(x, Qd, prcA, totWlvl_ref, totWlvl_mtr, area_open_water, area_land, pmpQ))

    area_ha_required_open_water = 0
    area_m2_required_open_water = area_ha_required_open_water * 10000

    data = {}
    data["volume_rain_mm"] = float(volume_rain_mm)
    data["model_matrix"] = model_matrix.tolist()
    data["rainfall_per_day"] = rainfall_per_day.tolist()
    data["flow_per_hour_l_s_ha"] = flow_per_hour_l_s_ha.tolist()
    data["area_ha_required_open_water"] = area_ha_required_open_water
    data["area_m2_required_open_water"] = area_m2_required_open_water
    data["effect"] = effect.to_dict(orient="list")

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
    flow_per_hour_l_s_ha, model_matrix = get_discharge(input, rainfall_per_day)  # noqa: F821

    reduction_in_delta_h_cm = 0
    data = {}
    data["volume_rain_mm"] = float(volume_rain_mm)
    data["model_matrix"] = model_matrix.tolist()
    data["rainfall_per_day"] = rainfall_per_day.tolist()
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
