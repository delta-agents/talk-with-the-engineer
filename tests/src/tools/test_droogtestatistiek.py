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
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models import SupplyInputGivenH
from talk_with_the_engineer.models.modelset_rules_of_thumb.supply import (
    DROUGHT_REGIONS,
    DROUGHT_RETURN_PERIODS,
    DROUGHT_SCENARIOS,
    GROWING_SEASON_DAYS,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_drought import (
    available_regions,
    available_return_periods,
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


# --- van data-asset naar toolinvoer -------------------------------------------------
#
# De statistiek stond in de repo en niemand las hem: geen invoerveld, geen tool, alleen
# deze tests. `PLAN_DROOGTE_EIS_ALS_WATERSTAND.md` Sec. 5.2 beschrijft de knop die dat
# gat dicht - regio, scenario, herhaaltijd - en die staat nu op de twee aanvoertools.

POLDER = {
    "area_ha": 4000,
    "percentage_open_water": 3.5,
    "drawdown_available_m": 0.3,
}


def test_the_schema_enums_cannot_drift_from_the_asset():
    """De keuzelijsten staan in het invoermodel en de waarden in het databestand.

    Ze staan er los van elkaar omdat een import uit het toolpakket een importcykel zou
    opleveren - `tools/__init__.py` importeert de tools en die importeren de modellen. Deze
    test is wat die duplicatie eerlijk houdt: gaat er een waterschap bij of verandert er een
    naam, dan valt hij om in plaats van dat het schema stil iets anders adverteert dan de
    tool aankan.
    """
    assert set(DROUGHT_REGIONS) == set(available_regions())
    assert set(DROUGHT_RETURN_PERIODS) == set(available_return_periods())
    for region in available_regions():
        assert set(DROUGHT_SCENARIOS) == set(available_scenarios(region)), region


def test_choosing_a_drought_fills_in_the_deficit():
    """Het tripel is de droogte-tegenhanger van `return_period` op de natte kant."""
    model = SupplyInputGivenH(
        **POLDER,
        drought_region="Rijn_en_IJssel",
        drought_scenario="Referentie",
        drought_return_period=10,
    )

    total = cumulative_deficit_mm("Rijn_en_IJssel", "Referentie", 10)
    assert model.cumulative_deficit_mm == total
    # het venster is het groeiseizoen en niet de dertig dagen van de losse invoer
    assert model.length_days == GROWING_SEASON_DAYS
    assert model.deficit_mm_per_day == pytest.approx(total / GROWING_SEASON_DAYS)
    # en het venster is een AANNAME, dus het staat in `assumptions`
    assert "length_days" in model.assumed_fields


def test_a_shorter_window_concentrates_the_same_volume():
    """Hetzelfde cumulatieve tekort over minder dagen is een scherpere vraag."""
    season = SupplyInputGivenH(
        **POLDER,
        drought_region="Rijn_en_IJssel",
        drought_scenario="Referentie",
        drought_return_period=10,
    )
    short = SupplyInputGivenH(
        **POLDER,
        length_days=90,
        drought_region="Rijn_en_IJssel",
        drought_scenario="Referentie",
        drought_return_period=10,
    )
    assert short.cumulative_deficit_mm == season.cumulative_deficit_mm
    assert short.deficit_mm_per_day > season.deficit_mm_per_day
    assert "length_days" not in short.assumed_fields


def test_the_climate_scenario_moves_the_answer():
    """Wat het scenario in het rapport doet, doet het ook aan de toolgrens."""
    rates = [
        SupplyInputGivenH(
            **POLDER,
            drought_region="Rijn_en_IJssel",
            drought_scenario=scenario,
            drought_return_period=10,
        ).deficit_mm_per_day
        for scenario in ("Referentie", "Hd_2050", "Hd_2100")
    ]
    assert rates[0] < rates[1] < rates[2]


def test_giving_the_deficit_yourself_still_works_and_looks_up_nothing():
    """De oude weg blijft de eerste; de statistiek is een tweede en geen vervanging."""
    model = SupplyInputGivenH(**POLDER, deficit_mm_per_day=4)
    assert model.deficit_mm_per_day == 4
    assert model.cumulative_deficit_mm is None
    assert model.drought_statistic_choice == {}
    # en dan geldt de gewone standaardwaarde van dertig dagen
    assert model.length_days == 30


@pytest.mark.parametrize(
    "extra, expected",
    [
        ({}, "deficit_mm_per_day"),
        ({"drought_region": "Rijn_en_IJssel"}, "ontbreken"),
        (
            {
                "deficit_mm_per_day": 4,
                "drought_region": "Rijn_en_IJssel",
                "drought_scenario": "Referentie",
                "drought_return_period": 10,
            },
            "dubbelop",
        ),
    ],
)
def test_an_ambiguous_or_incomplete_drought_is_refused(extra, expected):
    """Beide wegen tegelijk, of een half tripel, is een invoerfout en geen keuze.

    Dezelfde discipline als `one_unit_only` op de eenheden: stil een van de twee laten
    winnen zou een antwoord opleveren waarvan niet te zien is waar het op rust.
    """
    with pytest.raises(ModelRetry) as refusal:
        SupplyInputGivenH(**POLDER, **extra)
    assert expected in str(refusal.value)


def test_a_return_period_outside_the_series_names_what_is_available():
    """`None` in het bestand is "niet gemeten", en dat is iets anders dan een fout.

    Een null zit aan BEIDE uiteinden - bij de natste scenario's wordt T100 niet gehaald en
    bij de droogste ligt T2 onder de reeks - dus een richting adviseren zou in de helft van
    de gevallen het verkeerde advies zijn. De weigering noemt daarom wat er wel kan.
    """
    with pytest.raises(ModelRetry) as refusal:
        SupplyInputGivenH(
            **POLDER,
            drought_region="Delfland",
            drought_scenario="Hd_2100",
            drought_return_period=2,
        )
    message = str(refusal.value)
    assert "buiten de reeks" in message
    assert "5, 10, 25, 50, 100" in message


def test_the_field_description_names_the_gaps_it_actually_has():
    """De beschrijving beloofde een weigering die je in de praktijk zelden tegenkomt.

    Er stond "bij de natste scenario's is T100 niet bereikt binnen de gebruikte reeks", en
    dat las als een regel. Drie voor de hand liggende steekproeven - Rijn en IJssel /
    Ln_2100 / T100, Rijn en IJssel / Hn_2100 / T100, Delfland / Hn_2100 / T100 - leverden
    alle drie gewoon een getal op, en dan is de tekst voor de meest waarschijnlijke
    testgevallen niet waar. Zie B6 in bevindingenrapport-vuistregels-deel-2.md.

    Deze test telt de lege cellen en legt ze naast wat de beschrijving zegt, zodat de twee
    niet uit elkaar kunnen lopen zodra het databestand wordt bijgewerkt.
    """
    from talk_with_the_engineer.models.modelset_rules_of_thumb.drought import (
        DROUGHT_REGIONS,
        DROUGHT_RETURN_PERIODS,
        DROUGHT_SCENARIOS,
        DroughtStatisticInput,
    )

    empty = [
        (region, scenario, period)
        for region in DROUGHT_REGIONS
        for scenario in DROUGHT_SCENARIOS
        for period in DROUGHT_RETURN_PERIODS
        if cumulative_deficit_mm(region, scenario, period) is None
    ]
    total = len(DROUGHT_REGIONS) * len(DROUGHT_SCENARIOS) * len(DROUGHT_RETURN_PERIODS)

    description = DroughtStatisticInput.model_fields[
        "drought_return_period"
    ].description
    assert f"{total} cellen" in description
    assert f"zijn er {len(empty)} leeg" in description

    # en elke lege cel wordt bij naam genoemd, want "de natste scenario's" was te vaag
    for region, scenario, _ in empty:
        assert region.replace("_", " ") in description, (region, scenario)
        assert scenario in description, scenario

    # de drie steekproeven uit het rapport horen juist WEL een getal te geven
    for scenario in ("Ln_2100", "Hn_2100"):
        assert cumulative_deficit_mm("Rijn_en_IJssel", scenario, 100) > 0
    assert cumulative_deficit_mm("Delfland", "Hn_2100", 100) > 0
