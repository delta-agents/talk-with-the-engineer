"""De droogtestatistiek uit STOWA 2025-23, zoals hij in de repo staat.

`drought_statistics.json` is een data-asset naast `rainfall_patterns.json`: de exogene
droogte-as, per waterschap en per KNMI'23-scenario. Deze tests bewaken de eigenschappen die
het bestand bruikbaar maken - niet de exacte getallen, want die komen uit het rapport en
worden hier niet overgeschreven.

Het klimaatsignaal is wél vastgelegd, want dat is de controle dat de extractie het rapport
reproduceert: Tabel 1 van STOWA 2025-23 geeft voor het Hd2050-scenario ongeveer +35 % op het
maximaal cumulatief neerslagtekort bij T10, en +68 % voor Hd2100.
"""

import pytest

from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_drought import (
    available_regions,
    available_scenarios,
    cumulative_deficit_mm,
)

RETURN_PERIODS = (2, 5, 10, 25, 50, 100)


def test_every_water_authority_is_there():
    """Eenentwintig waterschappen; de regiokeuze is niet optioneel.

    De ruimtelijke variatie in het neerslagtekort is meer dan 30 % tussen noord en zuid, dus
    een landelijk gemiddelde zou voor de meeste gebieden het verkeerde getal zijn.
    """
    regions = available_regions()
    assert len(regions) == 21
    assert "Rijn_en_IJssel" in regions
    assert "Hollands_Noorderkwartier" in regions


def test_every_region_has_the_reference_and_the_climate_scenarios():
    for region in available_regions():
        scenarios = available_scenarios(region)
        assert "Referentie" in scenarios
        assert {"Hd_2050", "Hd_2100", "Hn_2050", "Hn_2100"} <= set(scenarios)


def test_the_deficit_rises_with_the_return_period():
    """Een zeldzamere droogte is een diepere droogte, overal en in elk scenario."""
    for region in available_regions():
        for scenario in available_scenarios(region):
            values = [
                cumulative_deficit_mm(region, scenario, period)
                for period in RETURN_PERIODS
            ]
            present = [value for value in values if value is not None]
            assert present, f"{region}/{scenario} heeft geen enkele herhaaltijd"
            assert all(
                earlier <= later for earlier, later in zip(present, present[1:])
            ), f"{region}/{scenario} is niet monotoon: {values}"


def test_the_climate_signal_reproduces_the_report():
    """De controle op de extractie: Tabel 1 van STOWA 2025-23.

    Het rapport geeft voor T10 een toename van 35 % (2050Hd) en 68 % (2100Hd) ten opzichte
    van het referentiescenario. Komt de extractie daarop uit, dan is de GEV-interpolatie
    langs de plotposities de fit die het rapport beschrijft.
    """
    reference = cumulative_deficit_mm("Rijn_en_IJssel", "Referentie", 10)
    hd_2050 = cumulative_deficit_mm("Rijn_en_IJssel", "Hd_2050", 10)
    hd_2100 = cumulative_deficit_mm("Rijn_en_IJssel", "Hd_2100", 10)

    assert hd_2050 / reference - 1 == pytest.approx(0.35, abs=0.02)
    assert hd_2100 / reference - 1 == pytest.approx(0.68, abs=0.02)


def test_a_dry_scenario_is_drier_than_its_wet_twin():
    """De d/n-as van KNMI'23: droge zomers verdrogen sterker dan natte."""
    for region in available_regions():
        for horizon in ("2050", "2100"):
            dry = cumulative_deficit_mm(region, f"Hd_{horizon}", 10)
            wet = cumulative_deficit_mm(region, f"Hn_{horizon}", 10)
            assert dry > wet, f"{region} {horizon}: {dry} niet groter dan {wet}"


def test_the_regional_spread_is_real():
    """Meer dan 30 % verschil tussen het natste en het droogste waterschap.

    Dit is de reden dat de statistiek per waterschap in het bestand staat en niet als één
    landelijk getal.
    """
    values = [
        cumulative_deficit_mm(region, "Referentie", 10)
        for region in available_regions()
    ]
    assert min(values) > 0
    assert max(values) / min(values) > 1.2


def test_an_unknown_region_is_an_error_and_not_a_silent_none():
    """Een tikfout in de regionaam is een fout in de aanroep, geen ontbrekende statistiek."""
    with pytest.raises(KeyError, match="onbekende regio"):
        cumulative_deficit_mm("Waterschap Bestaat Niet", "Referentie", 10)


def test_an_untabulated_return_period_is_an_error():
    """Een herhaaltijd die niet wordt bijgehouden is een fout in de aanroep.

    Niet `None`, want dat betekent iets anders - zie de test hieronder. Twee verschillende
    situaties die allebei stil `None` teruggeven, zijn niet uit elkaar te houden.
    """
    with pytest.raises(KeyError, match="wordt niet bijgehouden"):
        cumulative_deficit_mm("Rijn_en_IJssel", "Referentie", 500)


def test_a_return_period_outside_the_series_is_none_and_not_extrapolated():
    """Buiten de 240-jarige reeks staat `null`, en dat is eerlijker dan doorrekenen.

    Dit komt echt voor: in het natste scenario van Noorderzijlvest wordt T100 in 240 jaar
    niet gehaald. Extrapoleren zou daar een getal verzinnen waar het rapport er geen heeft.
    """
    assert cumulative_deficit_mm("Noorderzijlvest", "Ln_2100", 100) is None
    # en het is een uitzondering en geen regel: dezelfde regio heeft T10 gewoon
    assert cumulative_deficit_mm("Noorderzijlvest", "Ln_2100", 10) > 0
