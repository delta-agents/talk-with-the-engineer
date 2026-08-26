"""Wat de tools over hun eigen antwoord vertellen.

Twee dingen die geen invloed hebben op de getallen maar wel op de bruikbaarheid ervan:
welke standaardwaarden er stilzwijgend zijn gebruikt, en wat `magnitude_at_optimum`
eigenlijk voor punt is.
"""

import re

import pytest

from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    ASSUMPTION_NOTES,
    RETURN_PERIODS,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.discharge import (
    DischargeInputGivenDischarge,
    DischargeInputGivenH,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import OptimumKind
from talk_with_the_engineer.models.modelset_rules_of_thumb.supply import (
    SupplyInputGivenH,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.retain import (
    RetentionInputGivenArea,
    RetentionInputGivenH,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.store import (
    StoreInputGivenArea,
    StoreInputGivenH,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.discharge import (
    calculate_discharge_given_discharge,
    calculate_discharge_given_h,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.retain import (
    calculate_retention_given_area,
    calculate_retention_given_h,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.store import (
    calculate_store_given_area,
    calculate_store_given_h,
)

# Alleen wat iemand noemt die "reken eens uit wat een polder van 4000 ha nodig heeft"
# vraagt. Alles wat hier niet in staat komt uit een standaardwaarde.
BARE_CALL = {
    "area_ha": 4000,
    "discharge_capacity_m3_per_sec": 5,
    "return_period": 100,
}


@pytest.mark.asyncio
async def test_a_bare_call_reports_every_default_it_used(test_context):
    result = await calculate_store_given_h(
        test_context, StoreInputGivenH(**BARE_CALL, delta_h_available=1.0)
    )

    reported = {a.field for a in result.assumptions}
    assert reported == {
        "time_of_year",
        "percentage_open_water",
        "length_event_hrs",
        "rainfall_regime",
        "name_rainfall_pattern",
        "days_to_discharge",
    }
    assert all(a.why_it_matters for a in result.assumptions)


@pytest.mark.asyncio
async def test_the_derived_unit_fields_are_not_assumptions(test_context):
    """De validators vullen area_m2 en de vier andere capaciteitseenheden zelf in.

    Die zijn afgeleid van wat de beller wel opgaf en dus geen aanname; ze zouden de lijst
    alleen maar verdunnen.
    """
    result = await calculate_store_given_h(
        test_context, StoreInputGivenH(**BARE_CALL, delta_h_available=1.0)
    )

    reported = {a.field for a in result.assumptions}
    assert not any(field.startswith("discharge_capacity") for field in reported)
    assert "area_m2" not in reported


@pytest.mark.asyncio
async def test_a_fully_specified_call_assumes_nothing(test_context, reference_case):
    """De referentiecasus laat niets aan het toeval over, dus de uitvoer blijft zoals hij was."""
    result = await calculate_store_given_h(
        test_context, StoreInputGivenH(**reference_case, delta_h_available=1.0)
    )

    assert result.assumptions == []
    assert "Aangenomen" not in result.description


@pytest.mark.asyncio
async def test_the_assumptions_end_up_in_the_sentence_that_gets_read(test_context):
    """Het gestructureerde veld is te makkelijk over te slaan; de uitleg niet."""
    result = await calculate_store_given_h(
        test_context, StoreInputGivenH(**BARE_CALL, delta_h_available=1.0)
    )

    assert "Aangenomen omdat ze niet zijn opgegeven" in result.description
    assert "time_of_year=summer" in result.description
    assert "percentage_open_water=2.0" in result.description


@pytest.mark.asyncio
async def test_the_assumptions_follow_the_language(test_context):
    result = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(**BARE_CALL, delta_h_available=1.0, language="en"),
    )

    assert "Assumed, because they were not given" in result.description


@pytest.mark.asyncio
async def test_retention_asks_for_one_default_more(test_context, reference_case):
    """`days_to_retain_discharge` hoort alleen bij vasthouden, en wordt daar wel gemeld."""
    result = await calculate_retention_given_h(
        test_context, RetentionInputGivenH(**reference_case, delta_h_available=0.10)
    )

    assert [a.field for a in result.assumptions] == ["days_to_retain_discharge"]


@pytest.mark.asyncio
async def test_every_measure_names_its_own_kind_of_optimum(
    test_context, reference_case
):
    """Dezelfde veldnaam, drie verschillende betekenissen - en die staan er nu bij.

    Bergen loopt tegen de fysieke grens (al het land is open water), afvoeren wordt vlak
    zodra de stijging niet verder kan zakken, en vasthouden heeft een echt binnenoptimum
    waar verder gaan de stijging weer opdrijft.
    """
    store = await calculate_store_given_h(
        test_context, StoreInputGivenH(**reference_case, delta_h_available=1.0)
    )
    discharge = await calculate_discharge_given_h(
        test_context, DischargeInputGivenH(**reference_case, delta_h_available=1.0)
    )
    retention = await calculate_retention_given_h(
        test_context, RetentionInputGivenH(**reference_case, delta_h_available=0.10)
    )

    assert store.magnitude_optimum_kind is OptimumKind.UPPER_BOUND
    assert discharge.magnitude_optimum_kind is OptimumKind.PLATEAU
    assert retention.magnitude_optimum_kind is OptimumKind.INTERIOR


@pytest.mark.asyncio
async def test_an_interior_optimum_really_gets_worse_beyond_it(
    test_context, reference_case
):
    """De belofte die `interior` doet, nagerekend op de maatregel die hem waarmaakt."""
    retention = await calculate_retention_given_h(
        test_context, RetentionInputGivenH(**reference_case, delta_h_available=0.10)
    )
    assert retention.magnitude_optimum_kind is OptimumKind.INTERIOR

    optimum_ha = retention.data["magnitude_at_optimum_ha"]
    beyond = await calculate_retention_given_area(
        test_context,
        RetentionInputGivenArea(**reference_case, delta_area_ha=optimum_ha * 1.15),
    )

    assert beyond.dh_with_measure_m > retention.feasible_dh_min_m


@pytest.mark.asyncio
async def test_a_plateau_optimum_does_not_get_worse_beyond_it(
    test_context, reference_case
):
    """En de belofte die `plateau` doet: meer pompen is zinloos, niet schadelijk."""
    discharge = await calculate_discharge_given_h(
        test_context, DischargeInputGivenH(**reference_case, delta_h_available=1.0)
    )
    assert discharge.magnitude_optimum_kind is OptimumKind.PLATEAU

    optimum = discharge.data["magnitude_at_optimum_m3_per_sec"]
    beyond = await calculate_discharge_given_discharge(
        test_context,
        DischargeInputGivenDischarge(
            **reference_case, delta_discharge_capacity_m3_per_sec=optimum * 1.5
        ),
    )

    assert beyond.dh_with_measure_m <= discharge.feasible_dh_min_m + 1e-6


@pytest.mark.asyncio
async def test_the_forward_direction_carries_it_too(test_context, reference_case):
    """Beide richtingen rapporteren hetzelfde over dezelfde maatregel."""
    result = await calculate_store_given_area(
        test_context, StoreInputGivenArea(**reference_case, area_available_ha=111.2)
    )

    assert result.magnitude_optimum_kind is OptimumKind.UPPER_BOUND
    assert result.assumptions == []


# --- Kloppen de notities zelf nog? ---------------------------------------------------
#
# Elke notitie in ASSUMPTION_NOTES doet een uitspraak over wat de rekenkern doet. Die zijn
# nagerekend op de tools en niet ontleend aan wat in de praktijk gebruikelijk is; deze
# tests houden ze vast, zodat een notitie niet stilletjes een bewering wordt die niet meer
# klopt.

REFERENCE_POLDER_ONLY = {
    "area_ha": 4000,
    "percentage_open_water": 3.5,
    "discharge_capacity_m3_per_sec": 5,
    "length_event_hrs": 96,
    "rainfall_regime": "R",
    "name_rainfall_pattern": "p1c",
    "days_to_discharge": 3,
}


async def _reference(test_context, **overrides):
    return await calculate_store_given_h(
        test_context,
        StoreInputGivenH(
            **{
                **REFERENCE_POLDER_ONLY,
                "return_period": 100,
                "time_of_year": "winter",
                "delta_h_available": 1.0,
                **overrides,
            }
        ),
    )


@pytest.mark.asyncio
async def test_summer_is_the_mild_end_at_every_return_period(test_context):
    """De notitie bij time_of_year, nagerekend over de hele statistiek."""
    for period in RETURN_PERIODS:
        winter = await _reference(test_context, return_period=period)
        summer = await _reference(
            test_context, return_period=period, time_of_year="summer"
        )
        assert (
            summer.data["rain_volume_gross_mm"] < winter.data["rain_volume_gross_mm"]
        ), period


@pytest.mark.asyncio
async def test_the_rise_is_near_inversely_proportional_to_open_water(test_context):
    """De notitie bij percentage_open_water: halveren verdubbelt de stijging."""
    for low, high in ((1, 2), (2.5, 5), (5, 10)):
        thin = await _reference(test_context, percentage_open_water=low)
        wide = await _reference(test_context, percentage_open_water=high)
        assert thin.dh_reference_m / wide.dh_reference_m == pytest.approx(2.0, rel=0.02)


@pytest.mark.asyncio
async def test_a_longer_event_brings_more_rain(test_context):
    """De notitie bij length_event_hrs, inclusief de genoemde getallen."""
    volumes = [
        (await _reference(test_context, length_event_hrs=hours)).data[
            "rain_volume_gross_mm"
        ]
        for hours in (48.0, 96.0, 192.0)
    ]
    assert volumes == sorted(volumes)
    assert [round(v) for v in volumes] == [77, 100, 129]


@pytest.mark.asyncio
async def test_the_regimes_run_from_ll_up_to_h(test_context):
    """De notitie bij rainfall_regime, inclusief de genoemde grenzen."""
    volumes = [
        (await _reference(test_context, rainfall_regime=regime)).data[
            "rain_volume_gross_mm"
        ]
        for regime in ("LL", "L", "R", "H")
    ]
    assert volumes == sorted(volumes)
    assert round(volumes[0]) == 82 and round(volumes[-1]) == 108


@pytest.mark.asyncio
async def test_the_pattern_moves_the_peak_and_not_the_total(test_context):
    """De notitie bij name_rainfall_pattern: gelijke som, andere piek."""
    results = [
        await _reference(test_context, name_rainfall_pattern=pattern)
        for pattern in ("p_0", "p1a", "p1b", "p1c", "p1d", "p2a", "p2b")
    ]
    volumes = {round(r.data["rain_volume_gross_mm"], 6) for r in results}
    rises = {round(r.dh_reference_m, 6) for r in results}

    assert len(volumes) == 1
    assert len(rises) == len(results)


@pytest.mark.asyncio
async def test_fewer_discharge_days_give_a_higher_rise(test_context):
    """De notitie bij days_to_discharge: minder dagen concentreert de afvoer."""
    rises = [
        (await _reference(test_context, days_to_discharge=days)).dh_reference_m
        for days in (2, 3, 4)
    ]
    assert rises == sorted(rises, reverse=True)


@pytest.mark.asyncio
async def test_retaining_longer_helps_more_and_moves_the_optimum(
    test_context, reference_case
):
    """De notitie bij days_to_retain_discharge."""
    shorter, longer = [
        await calculate_retention_given_h(
            test_context,
            RetentionInputGivenH(
                **reference_case, delta_h_available=0.10, days_to_retain_discharge=days
            ),
        )
        for days in (2, 3)
    ]

    assert longer.feasible_dh_min_m < shorter.feasible_dh_min_m
    assert (
        longer.data["magnitude_at_optimum_ha"] > shorter.data["magnitude_at_optimum_ha"]
    )


def test_no_note_points_at_something_the_reader_cannot_open():
    """Een notitie moet op zichzelf te begrijpen zijn.

    Hier stond eerder "uit Tabel 39 van HKV PR4991.10". Een agent kan daar niets mee: dat
    rapport zit niet in zijn context, en de verwijzing kost alleen ruimte in het enige
    veld dat hem moet helpen beslissen of hij de gebruiker iets moet vragen. De herkomst
    van een invoerveld hoort in de veldbeschrijving, waar een mens hem zoekt.
    """
    for field, notes in ASSUMPTION_NOTES.items():
        for language, note in notes.items():
            assert not re.search(
                r"\b(tabel|table|PR\d|STOWA|rapport|report)\b", note, re.IGNORECASE
            ), f"{field} ({language}): {note!r}"


def test_every_note_exists_in_both_languages():
    """`language: "en"` vertaalde alleen `description`, en dat is de vervelendste stand.

    Een Engelstalige gebruiker kreeg een Engelse zin met een Nederlandse motivering
    eronder. Half toepassen suggereert dat de rest ook gedekt is - erger dan een veld dat
    er niet is, en erger dan een veld dat aantoonbaar niets doet.
    """
    for field, notes in ASSUMPTION_NOTES.items():
        assert set(notes) == {"nl", "en"}, field
        assert notes["nl"] != notes["en"], field


def test_every_note_belongs_to_a_field_that_exists():
    """Een typfout in een veldnaam zou de notitie stilzwijgend laten verdwijnen.

    Alle invoermodellen samen, want niet elk veld staat op elke tool: `length_days` hoort
    bij het neerslagtekort en dus alleen bij aanvoeren.
    """
    known = set()
    for model in (
        StoreInputGivenH,
        DischargeInputGivenH,
        RetentionInputGivenH,
        SupplyInputGivenH,
    ):
        known |= set(model.model_fields)

    assert set(ASSUMPTION_NOTES) <= known


# Wat een MCP-client verstuurt die de standaardwaarden uit het schema zelf in de aanroep
# invult, in plaats van de weggelaten velden weg te laten. Gemeten bij Claude Code: exact
# dezelfde getallen als BARE_CALL, maar `assumptions` kwam leeg terug omdat server-side
# elk veld dan "opgegeven" is. De fallbackwaarden staan daarom niet meer als `default` in
# het schema; wat een client dan hoogstens invult is `null`.
CLIENT_FILLED_CALL = {
    **BARE_CALL,
    "time_of_year": None,
    "length_event_hrs": None,
    "rainfall_regime": None,
    "name_rainfall_pattern": None,
    "days_to_discharge": None,
    "percentage_open_water": None,
}


@pytest.mark.asyncio
async def test_null_counts_as_omitted_and_is_still_reported(test_context):
    """Een client die de velden op `null` zet krijgt dezelfde aannames te zien."""
    result = await calculate_store_given_h(
        test_context, StoreInputGivenH(**CLIENT_FILLED_CALL, delta_h_available=1.0)
    )

    # Wat deze tool kan melden zijn de notities voor velden die hij ook heeft; vasthouden
    # is de enige met `days_to_retain_discharge` en aanvoeren de enige met `length_days`.
    reportable = set(ASSUMPTION_NOTES) & set(StoreInputGivenH.model_fields)
    assert {a.field for a in result.assumptions} == reportable
    assert "Aangenomen omdat ze niet zijn opgegeven" in result.description


@pytest.mark.asyncio
async def test_null_and_omitted_give_the_same_answer(test_context):
    """En het blijft dezelfde berekening: `null` verandert alleen wie het invult."""
    filled = await calculate_store_given_h(
        test_context, StoreInputGivenH(**CLIENT_FILLED_CALL, delta_h_available=1.0)
    )
    bare = await calculate_store_given_h(
        test_context, StoreInputGivenH(**BARE_CALL, delta_h_available=1.0)
    )

    assert filled.data == bare.data
    assert filled.measure.before == bare.measure.before


@pytest.mark.asyncio
async def test_the_rain_balance_closes(test_context):
    """Bruto min verlies is de som van de netto dagreeks, in beide seizoenen.

    Hier ging het mis: de uitvoer meldde `volume_rain_mm` (bruto, uit de statistiek) en
    `rainfall_per_day` (netto, na het zomerse neerslagverlies) onder namen die een totaal
    met zijn delen suggereren. In de zomer scheelde dat 20 mm - 86,6 tegen 66,6 - en zomer
    is de standaardwaarde, dus juist de kale aanroep las als een rekenfout. In de winter
    is er geen verlies en viel het niet op.

    De marge van 0,05 mm is de restpost: het neerslagpatroon uit de tabel sommeert tot
    0,9998 in plaats van 1, wat op 86 mm ongeveer 0,02 mm scheelt.
    """
    for season, expected_loss in (("winter", 0.0), ("summer", 20.0)):
        result = await _reference(test_context, time_of_year=season)
        data = result.data

        assert data["rain_loss_mm"] == pytest.approx(expected_loss, abs=0.05), season
        assert sum(data["rainfall_per_day_net_mm"]) == pytest.approx(
            data["rain_volume_gross_mm"] - data["rain_loss_mm"], abs=0.05
        ), season


# --- `language` dekt het hele antwoord, niet alleen de eerste zin -------------------

NEDERLANDSE_WOORDEN = (
    " de ",
    " het ",
    " een ",
    " niet ",
    " wordt ",
    " zit ",
    " bij deze waarde ",
)


def _looks_dutch(text: str) -> bool:
    padded = f" {text.lower()} "
    return any(word in padded for word in NEDERLANDSE_WOORDEN)


@pytest.mark.asyncio
async def test_english_covers_the_assumptions_and_the_caveats_too(test_context):
    """`language: "en"` vertaalde alleen `description`.

    `assumptions[].why_it_matters` en alle `caveats` bleven Nederlands, terwijl de
    handleiding alle drie verplicht stelt in de terugkoppeling. Een Engelstalige gebruiker
    kreeg dus een Engelse zin met een Nederlandse motivering eronder, of de beller liet de
    caveats weg - en dan valt precies de relativering weg die het model eerlijk houdt.
    """
    result = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(**BARE_CALL, delta_h_available=1.0, language="en"),
    )

    assert result.assumptions, "een kale aanroep hoort aannames te melden"
    assert result.caveats, "een zomerbui hoort een caveat te hebben"

    for assumption in result.assumptions:
        assert not _looks_dutch(assumption.why_it_matters), assumption.why_it_matters
    for caveat in result.caveats:
        assert not _looks_dutch(caveat.topic), caveat.topic
        assert not _looks_dutch(caveat.what), caveat.what
        assert not _looks_dutch(caveat.consequence), caveat.consequence
    for item in result.sensitivity:
        for note in (item.low_note, item.high_note):
            assert note is None or not _looks_dutch(note), note


@pytest.mark.asyncio
async def test_dutch_stays_dutch(test_context):
    """De terugval is Nederlands, en dat is de standaardwaarde van het veld."""
    result = await calculate_store_given_h(
        test_context, StoreInputGivenH(**BARE_CALL, delta_h_available=1.0)
    )
    assert _looks_dutch(result.caveats[0].what)
    assert _looks_dutch(result.assumptions[0].why_it_matters)
