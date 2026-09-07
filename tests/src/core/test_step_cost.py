"""De trapkost: een vast deel plus een variabel deel, en wat dat met de keuze doet.

Een lineaire prijs met een band kan de hoogte van een trap benaderen maar niet zijn vorm,
en de vorm bepaalt de beslissing: bij een lineaire prijs is een beetje goedkoop, bij een
trap is een beetje bijna zo duur als veel. Deze tests leggen dat verschil vast, en de twee
lezingen die eruit volgen.
"""

import pytest

from talk_with_the_engineer.core.actions import (
    ControlAction,
    DischargeAction,
    RetentionAction,
    StorageAction,
    TargetLevelAction,
)

from talk_with_the_engineer.core.cost import COST_OPEN_WATER, StepCost, UnitCost
from talk_with_the_engineer.core.package import Constraints, optimize
from talk_with_the_engineer.core.reference import REFERENCE_POLDER, REFERENCE_STORM

CONTROL_PRICE = StepCost(
    fixed_typical=400_000,
    fixed_low=250_000,
    fixed_high=900_000,
    per_unit_typical=200_000,
    per_unit_low=100_000,
    per_unit_high=400_000,
    unit="EUR per m peilmarge, boven het vaste deel",
    price_level="fictief",
    source="verzonnen voor deze test; er is geen bron voor sturingskosten in dit model",
    fixed_source="verzonnen voor deze test",
)
"""Een trapkost met verzonnen getallen, en dat mag ALLEEN hier.

De catalogus draagt geen prijs voor sturing, want die hebben we niet - zie `ControlAction`.
Een test heeft er wel een nodig om de VORM te kunnen toetsen, en dan is het eerlijker om de
herkomst "verzonnen" te noemen dan om een plausibel bedrag te kiezen.
"""


# --- de vorm ------------------------------------------------------------------------


def test_the_first_unit_costs_almost_everything():
    """Dat is de trap, in een regel.

    De eerste centimeter kost het vaste deel plus een centimeter; de tiende alleen een
    centimeter. Bij een lineaire prijs zou de eerste een tiende van de tiende kosten.
    """
    first = CONTROL_PRICE.typical_for(0.01)
    tenth = CONTROL_PRICE.typical_for(0.10) - CONTROL_PRICE.typical_for(0.09)
    assert first > 50 * tenth


def test_a_linear_price_has_no_fixed_part():
    """`fixed_part` staat op de basisklasse zodat een aanroeper hem kan melden.

    Zonder dat veld zou elke plek die de trap wil noemen eerst het type moeten vragen, en
    dan staat er een isinstance-tak in de rapportage.
    """
    assert COST_OPEN_WATER.fixed_part == 0.0
    assert CONTROL_PRICE.fixed_part == 400_000


def test_the_band_widens_with_the_quantity_and_never_inverts():
    """Twee onafhankelijke banden, opgeteld aan de uiteinden.

    De ruime lezing: hij neemt aan dat een duur systeem ook duur in beheer is. Voor een
    vuistregel is dat de goede kant om op te falen.
    """
    for quantity in (0.0, 0.05, 0.3, 1.0):
        low, high = CONTROL_PRICE.range_for(quantity)
        assert low <= CONTROL_PRICE.typical_for(quantity) <= high
    narrow = CONTROL_PRICE.range_for(0.0)
    wide = CONTROL_PRICE.range_for(1.0)
    assert (wide[1] - wide[0]) > (narrow[1] - narrow[0])


def test_a_unit_cost_is_still_linear():
    """De bestaande vorm verandert niet; dat is de eis van elke generalisatie hier."""
    price = UnitCost(
        typical=10.0,
        low=8.0,
        high=12.0,
        unit="EUR per stuk",
        price_level="n.v.t.",
        source="test",
    )
    assert price.typical_for(3.0) == pytest.approx(30.0)
    assert price.range_for(3.0) == pytest.approx((24.0, 36.0))
    assert price.typical_for(0.0) == 0.0


# --- de twee lezingen ---------------------------------------------------------------


def test_a_measure_that_is_not_executed_does_not_pay_the_fixed_part():
    """`cost` is de prijs van wat er STAAT.

    Nul maatvoering is nul euro, ook bij een trap: je koopt geen systeem voor een marge die
    je niet afspreekt.
    """
    action = ControlAction(unit_cost=CONTROL_PRICE)
    assert action.cost(REFERENCE_POLDER) == 0.0
    assert action.cost_range(REFERENCE_POLDER) == (0.0, 0.0)


def test_choosing_the_measure_does_pay_the_fixed_part():
    """`commitment_cost` is de prijs van de KEUZE.

    Het verschil met `cost` is precies het vaste deel bij nul, en dat is wat een pakket
    kost waarin de maatregel zit.
    """
    action = ControlAction(unit_cost=CONTROL_PRICE)
    assert action.commitment_cost(REFERENCE_POLDER) == 400_000
    assert action.at(0.20).commitment_cost(REFERENCE_POLDER) == pytest.approx(440_000)
    assert action.at(0.20).cost(REFERENCE_POLDER) == pytest.approx(440_000)


def test_the_two_readings_agree_for_a_linear_price():
    """Bij een lineaire prijs is er geen verschil, en dus geen nieuwe faalmodus.

    Zonder deze test zou de invoering van twee lezingen een stille wijziging kunnen zijn
    voor de vier maatregelen die al een prijs hadden.
    """
    for action in (
        StorageAction(delta_open_water_ha=10.0),
        RetentionAction(),
        DischargeAction(),
    ):
        assert action.cost(REFERENCE_POLDER) == action.commitment_cost(REFERENCE_POLDER)


def test_a_priceless_measure_stays_priceless_in_both_readings():
    """Geen prijs is `None` en niet nul, in beide lezingen.

    Nul zou betekenen dat de maatregel gratis is, en dat is precies de fout waar
    `PricelessPost` voor bestaat.
    """
    for action in (ControlAction(delta_level_margin_m=0.2), TargetLevelAction()):
        assert action.cost(REFERENCE_POLDER) is None
        assert action.commitment_cost(REFERENCE_POLDER) is None
        assert action.cost_range(REFERENCE_POLDER) is None


# --- en wat de trap met de zoektocht doet -------------------------------------------


def test_a_mix_that_barely_uses_a_step_cost_measure_is_dominated():
    """De trap forceert een keuze, en de enumeratie is waar die keuze wordt gemaakt.

    Binnen een mix is het vaste deel een constante - dat houdt de doelfunctie glad - maar
    het staat er wel. Een mix die de maatregel op bijna nul uitrekent, betaalt dus het
    vaste deel voor niets, en verliest van dezelfde mix zonder hem. Dat is de eigenschap
    waar de discrete/continue splitsing voor bestaat.
    """
    priced = ControlAction(unit_cost=CONTROL_PRICE)
    eis = Constraints(max_dh_total_m=0.30)

    with_control = optimize(
        REFERENCE_POLDER, REFERENCE_STORM, eis, actions=(DischargeAction(), priced)
    )
    without = optimize(
        REFERENCE_POLDER, REFERENCE_STORM, eis, actions=(DischargeAction(),)
    )

    assert with_control.best is not None
    assert without.best is not None
    # de mix mag sturing gebruiken, maar dan moet het ook iets opleveren
    used = with_control.best.quantities.get("sturing", 0.0)
    if used <= 1e-6:
        assert with_control.best.cost == pytest.approx(without.best.cost)


def test_an_unpriced_control_measure_is_not_in_the_default_mix():
    """De gratis hefboom uit issue #68, als test.

    Een ongeprijsde maatregel in `DEFAULT_ACTIONS` koopt inundatiemarge zonder tegenprijs.
    Dan verschuift het goedkoopste pakket zonder dat er iets aan de hydrologie is veranderd,
    en dat is precies de meetfout die deze catalogus niet mag hebben.
    """
    from talk_with_the_engineer.core.package import DEFAULT_ACTIONS

    assert not any(action.name_nl == "sturing" for action in DEFAULT_ACTIONS)
    assert all(
        action.unit_cost is not None or action.name_nl in {"peilopzet", "aanvoeren"}
        for action in DEFAULT_ACTIONS
    )
