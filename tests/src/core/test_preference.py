"""De voorkeursvolgorde: dezelfde eis langs een rooster bedreigingen.

Wat hier wordt vastgelegd is niet een getal maar een VERSCHIL: één pakket bij één bui zegt
iets anders dan de telling over alles wat de statistiek kan trekken. Het volledige rooster
is 312 doorrekeningen en duurt minuten, dus deze tests draaien op een klein rooster en
toetsen de eigenschappen die niet van de roostergrootte afhangen.
"""

import pytest

from talk_with_the_engineer.core.package import Constraints
from talk_with_the_engineer.core.preference import (
    Preference,
    measures_in_the_cheapest_package,
    over_the_grid,
    storm_grid,
)
from talk_with_the_engineer.core.reference import REFERENCE_POLDER, REFERENCE_STORM

NORM = Constraints(max_dh_total_m=0.18)
"""De eis van de demo: de piek onder achttien centimeter."""


def _small_grid(return_periods=(10.0, 25.0, 100.0)):
    return list(
        storm_grid(
            REFERENCE_STORM,
            return_periods,
            [192.0],
            ["summer"],
            ["R"],
        )
    )


def test_the_grid_spans_every_combination_of_its_axes():
    """Vier assen, en het rooster is hun product.

    Geen steekproef: de statistiek is discreet, dus dit IS de verzameling bedreigingen en
    niet een benadering ervan.
    """
    grid = list(
        storm_grid(
            REFERENCE_STORM,
            [10.0, 100.0],
            [96.0, 192.0],
            ["summer", "winter"],
            ["R", "H"],
        )
    )
    assert len(grid) == 2 * 2 * 2 * 2
    assert (
        len(
            {
                (s.return_period, s.length_event_hrs, s.time_of_year, s.rainfall_regime)
                for s in grid
            }
        )
        == 16
    )


def test_the_grid_leaves_the_reference_storm_alone():
    """Een variant mag de referentie niet verschuiven.

    Zou hij dat wel doen, dan rekent de rest van het rooster met een andere bui dan er
    staat - en dat is aan de uitkomst niet te zien.
    """
    before = REFERENCE_STORM
    _small_grid()
    assert REFERENCE_STORM == before
    assert REFERENCE_STORM.return_period == 10.0


def test_a_heavier_storm_never_needs_fewer_measures_on_this_norm():
    """Monotonie in de bedreiging: zwaarder weer maakt de opgave niet kleiner.

    Niet dat het pakket hetzelfde blijft - dat is juist het punt van de voorkeursvolgorde -
    maar dat er niet minder te doen is. Slaat dit om, dan zit er een tekenfout in het
    rooster of in de eis.
    """
    light = measures_in_the_cheapest_package(REFERENCE_POLDER, _small_grid()[0], NORM)
    heavy = measures_in_the_cheapest_package(REFERENCE_POLDER, _small_grid()[-1], NORM)
    assert sum(heavy.values()) >= sum(light.values())


def test_the_count_only_divides_by_the_threats_that_need_a_measure():
    """De noemer is niet het hele rooster.

    Een bui waarbij niets hoeft zegt niets over de voorkeur; hem meetellen zou elke
    maatregel verdunnen naarmate je meer lichte buien in het rooster stopt.
    """
    preference = Preference(
        counts={"afvoeren": 2},
        threats=10,
        threats_needing_a_measure=2,
    )
    assert preference.share_of("afvoeren") == pytest.approx(1.0)
    assert preference.share_of("bergen") == pytest.approx(0.0)


def test_an_empty_grid_does_not_divide_by_zero():
    """Nul bedreigingen is een leeg antwoord en geen fout."""
    preference = over_the_grid(REFERENCE_POLDER, NORM, [])
    assert preference.threats == 0
    assert preference.ordered == []
    assert preference.share_of("afvoeren") == 0.0


def test_the_pump_is_in_nearly_every_answer_and_retention_in_two_of_three():
    """De uitspraak op de laatste beat van de presentatie, op het kleine rooster.

    Het gemaal staat in elk pakket en vasthouden in een deel ervan: dat is precies het
    verschil tussen een maatregel die robuust is tegen wat je niet weet en een die aan de
    bui hangt. Bergen en peilopzet koopt de zoeker bij deze eis niet.
    """
    preference = over_the_grid(REFERENCE_POLDER, NORM, _small_grid())

    assert preference.threats == 3
    assert preference.threats_needing_a_measure == 3
    assert preference.share_of("afvoeren") == pytest.approx(1.0)
    assert 0.0 < preference.share_of("vasthouden") < 1.0
    assert preference.share_of("bergen") == pytest.approx(0.0)
    assert preference.share_of("peilopzet") == pytest.approx(0.0)
    assert preference.ordered[0][0] == "afvoeren"


def test_a_measure_that_is_not_used_does_not_appear_at_all():
    """De optimalisatie levert continue hoeveelheden, dus 'niet gebruikt' is 1e-12 en geen nul.

    Zonder de ondergrens staat elke maatregel in elk pakket en is de telling zinloos.
    """
    measures = measures_in_the_cheapest_package(
        REFERENCE_POLDER, _small_grid()[0], NORM
    )
    assert all(quantity > 1e-9 for quantity in measures.values())
    assert "bergen" not in measures
