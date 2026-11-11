"""De hele geldige invoerruimte moet doorrekenen.

D2 was een invoer die de validators goedkeurden en die vervolgens crashte
(`length_event_hrs=192` gaf een IndexError in 9 van de 27 combinaties duur x
days_to_discharge). D8 leverde negatieve neerslag op. Deze module dekt de klasse, niet de
twee losse gevallen.

De volledige ruimte wordt op neerslag- en afvoerniveau doorgerekend, want dat is snel en
daar zit alle conditionele logica. Op toolniveau wordt het raster duur x
days_to_discharge x seizoen gedekt: de waterbalans zelf is rekenkunde zonder takken.
"""

import itertools

import numpy as np
import pytest

from talk_with_the_engineer.interface.schemas.store import StoreInputGivenH
from talk_with_the_engineer.interface.schemas.area import DAYS_TO_DISCHARGE
from talk_with_the_engineer.interface.schemas.rainfall import (
    LENGTH_EVENT_HRS,
    NAME_RAINFALL_PATTERN,
    RAINFALL_REGIMES,
    RETURN_PERIODS,
    TIME_OF_YEAR,
)
from talk_with_the_engineer.interface.tools.discharge import calculate_discharge_given_h
from talk_with_the_engineer.interface.tools.retain import calculate_retention_given_h
from talk_with_the_engineer.interface.tools.store import calculate_store_given_h
from talk_with_the_engineer.interface.schemas.discharge import DischargeInputGivenH
from talk_with_the_engineer.interface.schemas.retain import RetentionInputGivenH
from talk_with_the_engineer.core.stats.runoff import (
    get_discharge,
)
from talk_with_the_engineer.core.stats.rainfall import (
    get_rainfall,
)

POLDER = {
    "area_ha": 4000,
    "percentage_open_water": 3.5,
    "discharge_capacity_m3_per_sec": 5,
}

# Sinds return_period een Literal over RETURN_PERIODS is, is ook 0.5 bereikbaar; als int
# getypeerd veld was die waarde eerder onbruikbaar.
USABLE_RETURN_PERIODS = list(RETURN_PERIODS)


def test_rainfall_and_drainage_cover_full_valid_input_space():
    checked = 0
    for season, period, hours, pattern, days in itertools.product(
        TIME_OF_YEAR,
        USABLE_RETURN_PERIODS,
        LENGTH_EVENT_HRS,
        NAME_RAINFALL_PATTERN,
        DAYS_TO_DISCHARGE,
    ):
        model = StoreInputGivenH(
            time_of_year=season,
            return_period=period,
            length_event_hrs=hours,
            name_rainfall_pattern=pattern,
            days_to_discharge=days,
            delta_h_available=1.0,
            **POLDER,
        )
        rain_per_day, volume_mm = get_rainfall(model)
        drainage, _ = get_discharge(model, rain_per_day)

        label = f"{season} T={period} {hours:.0f}u {pattern} d2d={days}"
        assert (rain_per_day >= 0).all(), (
            f"negatieve neerslag bij {label}: {rain_per_day}"
        )
        assert np.isfinite(rain_per_day).all(), f"niet-eindige neerslag bij {label}"
        assert (drainage >= 0).all(), f"negatieve afvoer bij {label}"
        assert volume_mm > 0
        checked += 1

    expected = (
        len(TIME_OF_YEAR)
        * len(USABLE_RETURN_PERIODS)
        * len(LENGTH_EVENT_HRS)
        * len(NAME_RAINFALL_PATTERN)
        * len(DAYS_TO_DISCHARGE)
    )
    assert checked == expected


def test_summer_loss_never_exceeds_available_rainfall():
    """Het neerslagverlies mag de bui hoogstens op nul brengen, nooit eronder."""
    for period, hours, pattern in itertools.product(
        USABLE_RETURN_PERIODS, LENGTH_EVENT_HRS, NAME_RAINFALL_PATTERN
    ):
        model = StoreInputGivenH(
            time_of_year="summer",
            return_period=period,
            length_event_hrs=hours,
            name_rainfall_pattern=pattern,
            delta_h_available=1.0,
            **POLDER,
        )
        with_loss, _ = get_rainfall(model, apply_summer_loss=True)
        without_loss, _ = get_rainfall(model, apply_summer_loss=False)

        label = f"T={period} {hours:.0f}u {pattern}"
        assert (with_loss >= 0).all(), f"negatieve neerslag bij {label}"
        removed = without_loss.sum() - with_loss.sum()
        assert removed <= 20.0 + 1e-9, (
            f"meer dan 20 mm verwijderd bij {label}: {removed}"
        )
        assert removed >= -1e-9, f"neerslag toegenomen bij {label}: {removed}"


def test_summer_loss_follows_e3_exactly_when_well_defined():
    """Waar E.3 goed gedefinieerd is, blijft het gedrag ongewijzigd."""
    model = StoreInputGivenH(
        time_of_year="summer",
        return_period=10,
        length_event_hrs=96.0,
        delta_h_available=1.0,
        **POLDER,
    )
    without_loss, _ = get_rainfall(model, apply_summer_loss=False)
    with_loss, _ = get_rainfall(model, apply_summer_loss=True)

    rain_first_two_days = without_loss[:2].sum()
    assert rain_first_two_days > 20.0  # anders test deze casus iets anders

    factor = 20.0 / rain_first_two_days
    np.testing.assert_allclose(with_loss[:2], without_loss[:2] * (1 - factor))
    np.testing.assert_allclose(with_loss[2:], without_loss[2:])


def test_summer_loss_stays_on_the_first_two_days():
    """Het verlies wordt niet doorgeschoven; dag 3 komt volledig ten goede aan afstroming.

    Bij een achtdaags patroon dragen dag 1 en 2 samen maar 12 % van de bui, dus er gaat
    minder dan 20 mm af. Eerder kwam hier negatieve neerslag uit, en daarna schoof een
    interim-implementatie het restant door naar dag 3 en verder. Ton Botterhuis heeft in
    augustus 2026 bevestigd dat het verlies op de eerste twee dagen blijft.
    """
    model = StoreInputGivenH(
        time_of_year="summer",
        return_period=100,
        length_event_hrs=192.0,
        delta_h_available=1.0,
        **POLDER,
    )
    without_loss, _ = get_rainfall(model, apply_summer_loss=False)
    with_loss, _ = get_rainfall(model, apply_summer_loss=True)

    assert without_loss[:2].sum() < 20.0  # dit is de casus die negatief werd
    assert (with_loss >= 0).all()
    # alles wat er in de eerste twee dagen valt gaat eraf, en niet meer dan dat
    assert with_loss[0] == pytest.approx(0.0)
    assert with_loss[1] == pytest.approx(0.0)
    # dag 3 en verder blijven onaangeroerd
    np.testing.assert_allclose(with_loss[2:], without_loss[2:])
    np.testing.assert_allclose(
        without_loss.sum() - with_loss.sum(), without_loss[:2].sum()
    )


def test_summer_loss_never_exceeds_twenty_millimetres():
    """Bij een vierdaags patroon is er genoeg neerslag en gaat er precies 20 mm af."""
    model = StoreInputGivenH(
        time_of_year="summer",
        return_period=100,
        length_event_hrs=96.0,
        delta_h_available=1.0,
        **POLDER,
    )
    without_loss, _ = get_rainfall(model, apply_summer_loss=False)
    with_loss, _ = get_rainfall(model, apply_summer_loss=True)

    assert without_loss[:2].sum() > 20.0
    np.testing.assert_allclose(without_loss.sum() - with_loss.sum(), 20.0)
    np.testing.assert_allclose(with_loss[2:], without_loss[2:])


@pytest.mark.asyncio
@pytest.mark.parametrize("hours", LENGTH_EVENT_HRS)
@pytest.mark.parametrize("days", DAYS_TO_DISCHARGE)
async def test_all_tools_run_for_every_duration_and_discharge_length(
    test_context, hours, days
):
    """D2-regressie: dit raster gaf 9 van 27 keer een IndexError."""
    common = {
        "return_period": 100,
        "time_of_year": "summer",
        "length_event_hrs": hours,
        "days_to_discharge": days,
        **POLDER,
    }
    assert await calculate_store_given_h(
        test_context, StoreInputGivenH(delta_h_available=1.0, **common)
    )
    assert await calculate_retention_given_h(
        test_context, RetentionInputGivenH(delta_h_available=1.0, **common)
    )
    assert await calculate_discharge_given_h(
        test_context, DischargeInputGivenH(delta_h_available=1.0, **common)
    )


def test_rainfall_regimes_are_all_usable():
    for season, regime in itertools.product(TIME_OF_YEAR, RAINFALL_REGIMES):
        model = StoreInputGivenH(
            time_of_year=season,
            rainfall_regime=regime,
            return_period=100,
            delta_h_available=1.0,
            **POLDER,
        )
        rain_per_day, volume_mm = get_rainfall(model)
        assert volume_mm > 0
        assert (rain_per_day >= 0).all()
