"""Maatregel aanvoeren: meer inlaatcapaciteit.

Grijpt aan op `capacity_in_m3_per_sec` van de verbinding, en gebruikt dezelfde rekenkern
als de andere vijf tools met de klem gespiegeld. Zie `simulate_deficit`.
"""

from dataclasses import dataclass

from talk_with_the_engineer.epistemics.assumptions import (
    assumed_defaults,
    in_language,
)
from talk_with_the_engineer.epistemics.caveats import model_caveats
from talk_with_the_engineer.epistemics.priceless import priceless_posts
from talk_with_the_engineer.epistemics.uncertainty import Sensitivity
from talk_with_the_engineer.core.actions import (
    AanvoerenAction,
)
from talk_with_the_engineer.core.connection import Connection
from talk_with_the_engineer.interface.schemas.output import (
    MeasureChange,
    PricelessPost,
)
from talk_with_the_engineer.core.soil import SOIL_TYPES
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.interface.schemas.supply import (
    GROWING_SEASON_DAYS,
    SupplyInputGivenH,
    SupplyInputGivenSupply,
    SupplyOutput,
)
from talk_with_the_engineer.interface.descriptions import (
    append_assumptions,
    append_source,
    append_spread,
    describe_supply_forward,
    describe_supply_inverse,
)
from talk_with_the_engineer.core.results import SolveStatus
from talk_with_the_engineer.core.transition import (
    NO_SOIL,
    SoilRelease,
)
from talk_with_the_engineer.core.inverse import (
    evaluate_supply,
    solve_supply,
)
from talk_with_the_engineer.epistemics.uncertainty import sensitivity_of
from talk_with_the_engineer.utils.logging_utils import log_tool_call

SECONDS_PER_MINUTE = 60
MINUTES_PER_DAY = 60 * 24
LITRES_PER_M3 = 1000


@dataclass(frozen=True)
class Deficit:
    """De exogene droogte zoals `simulate_deficit` hem verwacht."""

    deficit_mm_per_day: float
    length_days: int
    available_source_volume_m3: float = float("inf")
    """Wat de bron over deze periode kan leveren [m3]; `inf` is onbeperkt.

    Onbeperkt is het gedrag dat er altijd was, en het is precies de aanname die de caveat
    over aanvoerbeschikbaarheid benoemde: dat het water bij de inlaat is. Vul hem in en die
    aanname wordt een getal.
    """


def _deficit(input, available_source_volume_m3=None) -> Deficit:
    """De exogene droogte zoals de rekenkern hem verwacht.

    Met een expliciet volume erbij is dit dezelfde droogte op een andere bron - wat
    `_source_spread` nodig heeft om het antwoord aan de randen van de beschikbaarheidsband
    uit te rekenen, zonder de invoer opnieuw te valideren.
    """
    if available_source_volume_m3 is None:
        available_source_volume_m3 = (
            float("inf")
            if input.available_source_volume_m3 is None
            else float(input.available_source_volume_m3)
        )
    return Deficit(
        input.deficit_mm_per_day,
        input.length_days,
        float(available_source_volume_m3),
    )


def _soil(input) -> SoilRelease:
    """De bodem zoals de rekenkern hem verwacht, of geen bodem.

    Geen bodem is `NO_SOIL` en niet een klein getal: een voorraad van nul verdiept de band
    niet en een oneindig plafond knijpt de vraag niet af, dus zonder gebiedstype is het
    antwoord tot op de bit wat het zonder bodem is.
    """
    if not input.soil_is_modelled:
        return NO_SOIL
    return SoilRelease(
        store_mm=float(input.soil_store_mm),
        transfer_mm_per_day=float(input.soil_transfer_mm_per_day),
        binding_link=input._soil_binding_link,
    )


def _state(input) -> PolderState:
    """Bouw de toestand zoals het gebied er NU voor staat.

    Dus met de inlaat die er al ligt, en niet met de inlaat die wordt doorgerekend. Dat
    onderscheid is wat `measure.before` en `measure.delta` betekenis geeft; de totale
    capaciteit gaat als los argument naar `solve_supply` en `evaluate_supply`.

    `drawdown_available_m` en `level_margin_m` zijn dezelfde grootheid vanuit twee kanten
    bekeken: hoe diep de waterstand mag zakken. Aan de toolgrens heet hij naar wat de beller
    weet, in de toestand naar wat de rekenkern ermee doet.

    `target_level_rise_m` blijft daarom nul, en dat is geen vergeten veld maar het sluitstuk
    van diezelfde vertaling. De kern rekent met `level_margin_m + target_level_rise_m` als
    bufferdiepte; `drawdown_available_m` IS die som, want hij wordt gemeten vanaf het peil
    waar het gebied nu op staat - opzet inbegrepen. Hem hier nog eens optellen zou de
    peilopzet dubbel tellen. Een aanroep die het toch probeert wordt geweigerd in plaats van
    genegeerd; zie `SupplyWaterSystemInput.refuse_the_two_field_level_band`.
    """
    return PolderState(
        area_ha=input.area_ha,
        pct_open_water=input.percentage_open_water,
        level_margin_m=input.drawdown_available_m,
        connections=(
            # alleen de inlaat. `capacity_out_m3_per_sec` blijft nul: in een tekort is er
            # niets weg te pompen, en de bovenklem op streefpeil in `simulate_deficit` doet
            # al wat een gemaal doet. Zie `refuse_the_pump_capacity`.
            Connection(capacity_in_m3_per_sec=input.supply_capacity_m3_per_sec),
        ),
    )


def _data(input, result) -> dict:
    """De echo van de vraag, plus het antwoord in alle eenheden waarin een inlaat wordt
    uitgedrukt.

    Wat hier NIET meer in staat: `demand_mm`, `supplied_mm`, `buffer_mm`, `shortfall_mm`,
    de uitzakking en `days_until_buffer_empty`. Die zes stonden zowel hier als op
    topniveau, en dubbele velden roepen bij een beller de vraag op of er verschil is - juist
    omdat ze in `data` "ruwe uitkomsten en tussenresultaten" heten en op topniveau een
    gedocumenteerd veld zijn. Er was geen verschil; ze staan nu alleen nog op topniveau,
    waar de beschrijving bij ze hoort.
    """
    per_sec = result.supply_capacity_m3_per_sec
    return {
        # de vraag waar dit antwoord op reageert
        "deficit_mm_per_day": input.deficit_mm_per_day,
        "length_days": input.length_days,
        "drawdown_available_m": input.drawdown_available_m,
        # en waar dat tekort vandaan komt, als het is opgezocht
        **_drought_source(input),
        # idem voor het aanbod: dezelfde statistiek, andere kant van de balans
        **_source_statistic(input),
        # de bodem, als hij meedoet, en de vraagverdeling, als er een regio bij staat
        **_soil_data(input),
        **_demand_data(input),
        # het antwoord, in alle eenheden waarin een inlaat wordt uitgedrukt
        "supply_capacity_m3_per_sec": per_sec,
        "supply_capacity_m3_per_min": per_sec * SECONDS_PER_MINUTE,
        "supply_capacity_m3_per_day": per_sec * SECONDS_PER_MINUTE * MINUTES_PER_DAY,
        "supply_capacity_l_s_ha": per_sec * LITRES_PER_M3 / input.area_ha,
        "supply_capacity_mm_d": per_sec
        * SECONDS_PER_MINUTE
        * MINUTES_PER_DAY
        / input.area_m2
        * LITRES_PER_M3,
    }


def _drought_source(input) -> dict:
    """De herkomst van het tekort, als het uit de statistiek komt.

    Leeg wanneer de beller het tekort zelf opgaf; dan is er niets op te zoeken en zou een
    leeg blok alleen maar suggereren dat er iets ontbreekt. Staat er wel iets, dan is dit
    wat een terugkoppeling moet noemen: welk waterschap, welk scenario, welke herhaaltijd,
    en over welk venster het cumulatieve tekort is uitgesmeerd.
    """
    chosen = input.drought_statistic_choice
    if not chosen:
        return {}
    return {
        "drought_statistic": {
            **chosen,
            "cumulative_deficit_mm": input.cumulative_deficit_mm,
            # het venster van de STATISTIEK, en dus vast. Het venster van de AANROEP staat
            # eronder, want dat is een keuze van de beller; ze onder een naam zetten maakt
            # van `length_days: 90` een eigenschap van STOWA. Dat is dezelfde tweedeling
            # waar de handleiding elders scherp op is: wat je overkomt tegenover wat je
            # afspreekt.
            "window_days": GROWING_SEASON_DAYS,
            "concentrated_over_days": input.length_days,
            "source": "STOWA 2025-23",
        }
    }


def _source_statistic(input) -> dict:
    """Waar het bronvolume vandaan komt, als het is afgeleid.

    Leeg wanneer de beller het volume zelf opgaf of weglaat - dan is er niets opgezocht.
    Staat er wel iets, dan hoort dit er compleet in: welke rivier, welke fractie, hoe hard
    dat verband is en hoe breed de band eromheen. Alleen de fractie zou een puntwaarde
    suggereren die bij `r` rond -0,3 niet bestaat.
    """
    availability = input.source_availability
    if availability is None:
        return {}
    normal = input.source_volume_normal_year_m3
    return {
        "source_statistic": {
            "river": input.source_river,
            "availability_fraction": availability.fraction,
            "spread_factor": [availability.spread_low, availability.spread_high],
            "fit_r": availability.fit_r,
            "source_volume_normal_year_m3": normal,
            "available_source_volume_m3": input.available_source_volume_m3,
            "available_source_volume_range_m3": [
                normal * availability.fraction * availability.spread_low,
                normal * availability.fraction * availability.spread_high,
            ],
            "indicator": "minimale 7-daagse rivierafvoer",
            "source": "STOWA 2025-23",
        }
    }


def _source_spread(input, answer_for) -> list[Sensitivity]:
    """Het antwoord aan de twee randen van de beschikbaarheidsband.

    Alleen in de afgeleide tak. Gaf de beller het volume zelf op, dan is de onzekerheid van
    hem en niet van ons - dezelfde regel die `sensitivity_of` op de aangenomen velden hanteert.

    En het is precies het veld waar die regel voor bedoeld is: bij een correlatie van -0,3
    tussen tekort en rivierafvoer loopt de band van ongeveer 0,8 tot 1,3 maal de fractie, en
    dat is een groter bereik dan de meeste aannames op de natte kant opleveren.
    """
    availability = input.source_availability
    if availability is None:
        return []
    middle = input.available_source_volume_m3
    low_volume = middle * availability.spread_low
    high_volume = middle * availability.spread_high
    low_answer, low_note = answer_for(low_volume)
    high_answer, high_note = answer_for(high_volume)
    return [
        Sensitivity(
            field="available_source_volume_m3",
            low_value=f"{low_volume / 1e6:.2f} mln m3",
            high_value=f"{high_volume / 1e6:.2f} mln m3",
            low_answer=low_answer,
            high_answer=high_answer,
            low_note=low_note,
            high_note=high_note,
        )
    ]


def _varied_deficit(input, variant) -> Deficit:
    """Het tekort bij een gevarieerde invoer, met de herkomst gerespecteerd.

    `sensitivity_of` maakt zijn varianten met `model_copy(update=...)`, en dat slaat de
    validators over - terecht, want die zouden een afgeleid tekort als "dubbelop" weigeren.
    De afleiding moet daarom hier gebeuren, en ze verschilt per herkomst:

    * komt het tekort uit de STATISTIEK, dan ligt het cumulatieve volume vast en verdeelt
      een korter venster datzelfde volume over minder dagen - precies het concentratie-effect
      dat `length_days` beschrijft;
    * gaf de beller `deficit_mm_per_day` zelf op, dan blijft dat getal staan en verandert
      alleen de duur.

    Zonder dit onderscheid vertienvoudigt of achtst de rij voor `length_days` bij een
    opgezochte droogte stil het volume, en rekent hij dus een andere droogte door.
    """
    total = input.cumulative_deficit_mm
    per_day = (
        total / variant.length_days if total is not None else input.deficit_mm_per_day
    )
    return Deficit(
        per_day,
        variant.length_days,
        float("inf")
        if input.available_source_volume_m3 is None
        else float(input.available_source_volume_m3),
    )


def _variant_state(variant, input) -> PolderState:
    """De toestand bij een gevarieerde invoer; alleen `percentage_open_water` beweegt hier."""
    return PolderState(
        area_ha=variant.area_ha,
        pct_open_water=variant.percentage_open_water,
        level_margin_m=variant.drawdown_available_m,
        connections=(
            Connection(capacity_in_m3_per_sec=input.supply_capacity_m3_per_sec),
        ),
    )


def _assumed_spread(input, answer_for) -> list[Sensitivity]:
    """De spreiding over de velden die de beller heeft weggelaten.

    Dezelfde routine als de natte tools gebruiken; alleen de doorrekening is van hier.
    Zonder deze rijen meldt de tool `percentage_open_water` wel als aanname - met de tekst
    dat het van alle invoervelden de uitkomst het sterkst stuurt - en zegt hij er geen getal
    bij over hoeveel het scheelt.
    """
    return sensitivity_of(input, answer_for)


def _status_note(status, language: str) -> str | None:
    """De opmerking bij een rand die een ander soort antwoord geeft dan een getal."""
    if status is SolveStatus.NO_MEASURE_NEEDED:
        return in_language(
            {
                "nl": "bij dit bronvolume is er geen maatregel nodig",
                "en": "at this source volume no measure is needed",
            },
            language,
        )
    if status is SolveStatus.ACTION_INFEASIBLE:
        return in_language(
            {
                "nl": "bij dit bronvolume is het doel met aanvoeren niet haalbaar",
                "en": "at this source volume the target cannot be reached by supply",
            },
            language,
        )
    return None


def _drought_caveat_context(input) -> dict:
    """Wat de droogtestatistiek-caveats nodig hebben om zichzelf te schrijven."""
    availability = input.source_availability
    source = (
        {
            "source_volume_from_statistic": True,
            "source_spread_in_sensitivity": True,
            "source_river": input.source_river,
            "source_availability_fraction": availability.fraction,
            "source_spread_factor": [availability.spread_low, availability.spread_high],
            "source_fit_r": availability.fit_r,
        }
        if availability is not None
        else {}
    )
    chosen = input.drought_statistic_choice
    if not chosen:
        return source
    return {
        "drought_statistic": chosen,
        "cumulative_deficit_mm": input.cumulative_deficit_mm,
        "window_days": GROWING_SEASON_DAYS,
        "concentrated_over_days": input.length_days,
        **source,
    }


def _soil_caveat_context(input) -> dict:
    """Wat de bodemcaveats nodig hebben om zichzelf te schrijven.

    Leeg zonder bodem, en dan blijft de caveat staan die zegt dat de voorraad alleen het
    open water is.
    """
    if not input.soil_is_modelled:
        return {}
    return {"soil_store_is_modelled": True, "soil_type": input.soil_type}


def _demand_caveat_context(input) -> dict:
    """Wat de vraagpostcaveat nodig heeft, als er een regio bij staat."""
    posts = input.demand_posts
    if posts is None:
        return {}
    return {
        "demand_post_choice": input.demand_post_choice,
        "demand_share": posts.demand_share,
        "demand_share_is_coarse": posts.is_coarse,
        "demand_share_resolution": posts.share_resolution,
    }


def _soil_output(input, result) -> dict:
    """De bodemvelden in de uitvoer, of alle zes op null.

    Zes velden en niet vijf: `binding_link` staat er ook zonder bodem, want de vraag welke
    schakel knelt is dan nog steeds te beantwoorden - de bron of de inlaat.
    """
    if not input.soil_is_modelled:
        return {"binding_link": result.binding_link}
    return {
        "soil_store_mm": result.soil_store_mm,
        "soil_transfer_mm_per_day": input.soil_transfer_mm_per_day,
        "soil_supplied_mm": result.soil_supplied_mm,
        "unreachable_mm": result.unreachable_mm,
        "days_until_soil_empty": _finite(result.days_until_soil_empty),
        "binding_link": result.binding_link,
    }


def _soil_data(input) -> dict:
    """De bodem in `data`: de twee getallen en waar ze vandaan komen.

    Leeg zonder bodem. Staat er wel iets, dan hoort de herkomst erbij - een gebiedstype of
    een opgegeven waarde - want de twee dragen een verschillende zekerheid.
    """
    if not input.soil_is_modelled:
        return {}
    table = SOIL_TYPES.get(input.soil_type) if input.soil_type else None
    return {
        "soil_release": {
            "soil_type": input.soil_type,
            "store_mm_per_land": input.soil_store_mm,
            "transfer_mm_per_day_per_land": input.soil_transfer_mm_per_day,
            "limits_mm_per_day_per_land": dict(table.limits) if table else None,
            "storage_coefficient": table.storage_coefficient if table else None,
            "drawdown_m": table.drawdown_m if table else None,
            "infiltration_resistance_days": (
                table.infiltration_resistance_days if table else None
            ),
            "source": "gebiedstype" if table else "opgegeven",
        }
    }


def _demand_data(input) -> dict:
    """De vraagverdeling in `data`, als er een regio bij staat."""
    posts = input.demand_posts
    if posts is None:
        return {}
    return {
        "demand_posts": {
            **input.demand_post_choice,
            "demand_share": posts.demand_share,
            "coverage": posts.coverage,
            "shortfall_share": posts.shortfall_share,
            "total_coverage": posts.total_coverage,
            "share_resolution": posts.share_resolution,
            "which_post_this_model_computes": (
                "beregening, plus het deel van peilbeheer dat op het open water verdampt"
            ),
            "source": "werkopgave 2025 (DPZW fase 3, BP18)",
        }
    }


def _required_volume_m3(input, result) -> float:
    """Het volume dat door de inlaat moet, over de hele periode.

    Staat in de caveat omdat een debiet haalbaar klinkt en een volume uitnodigt tot
    narekenen: 1,81 m3/s is een pompje, 4,7 miljoen m3 in een maand is een vraag aan het
    regionale systeem. Nul bij nul capaciteit, en dan gaat de caveat niet af.
    """
    return (
        result.supply_capacity_m3_per_sec
        * input.length_days
        * SECONDS_PER_MINUTE
        * MINUTES_PER_DAY
    )


def _finite(value) -> float | None:
    """`inf` is geen geldige JSON, dus wat het volhoudt of onbeperkt is wordt `None`."""
    return None if value == float("inf") else value


def _supply_measure(result) -> MeasureChange:
    """Het `measure`-blok voor de aanvoerkant.

    Eigen functie en niet `MeasureChange.from_solve_result`, want de droogtekant heeft een
    eigen resultaattype: `SupplySolveResult` kent geen `magnitude`/`unit` maar een
    inlaatcapaciteit. De inhoud is dezelfde vraag - van welke waarde naar welke - en de vorm
    naar buiten hoort dus gelijk te zijn aan die van de natte tools.
    """
    before = result.state_before.supply_capacity_m3_per_sec
    after = result.supply_capacity_m3_per_sec
    delta = after - before
    return MeasureChange(
        name_nl=AanvoerenAction.name_nl,
        unit=AanvoerenAction.unit,
        before=before,
        after=after,
        delta=delta,
        delta_relative=(delta / before) if before else None,
        # een inlaat is een capaciteit en geen aandeel van het gebied
        delta_percentage_points=None,
    )


@log_tool_call
async def calculate_supply_given_h(ctx, input: SupplyInputGivenH) -> SupplyOutput:
    """Hoeveel inlaatcapaciteit dekt het neerslagtekort zonder dat de waterstand te diep zakt?

    Aanvoeren = supply.
    """
    state = _state(input)
    deficit = _deficit(input)
    soil = _soil(input)
    result = solve_supply(state, deficit, soil=soil)

    def answer_for(volume):
        variant = solve_supply(state, _deficit(input, volume), soil=soil)
        note = _status_note(variant.status, input.language)
        return (None if note else variant.supply_capacity_m3_per_sec), note

    def answer_for_variant(variant):
        solved = solve_supply(
            _variant_state(variant, input), _varied_deficit(input, variant), soil=soil
        )
        note = _status_note(solved.status, input.language)
        return (None if note else solved.supply_capacity_m3_per_sec), note

    assumptions = assumed_defaults(input)
    caveats = model_caveats(
        input,
        is_drought=True,
        required_supply_volume_m3=_required_volume_m3(input, result),
        source_volume_is_modelled=input.available_source_volume_m3 is not None,
        salinisation_is_the_next_step=True,
        **_soil_caveat_context(input),
        **_demand_caveat_context(input),
        **_drought_caveat_context(input),
    )
    sensitivity = _assumed_spread(input, answer_for_variant) + _source_spread(
        input, answer_for
    )
    return SupplyOutput(
        data=_data(input, result),
        description=append_assumptions(
            append_source(
                # het bereik erbij, net als op de natte kant: het gemelde debiet is het
                # midden van een band die de beller anders niet ziet
                append_spread(
                    describe_supply_inverse(result, input, input.language),
                    sensitivity,
                    result.supply_capacity_m3_per_sec,
                    "m3/s",
                    input.language,
                ),
                result,
                input,
                input.language,
            ),
            assumptions,
            input.language,
        ),
        status=result.status,
        assumptions=assumptions,
        caveats=caveats,
        sensitivity=sensitivity,
        priceless=[
            PricelessPost(**post)
            for post in priceless_posts(input, AanvoerenAction.name_nl)
        ],
        measure=_supply_measure(result),
        supply_capacity_m3_per_sec=result.supply_capacity_m3_per_sec,
        demand_mm=result.demand_mm,
        supplied_mm=result.supplied_mm,
        buffer_mm=result.buffer_mm,
        shortfall_mm=result.shortfall_mm,
        drawdown_m=result.drawdown_m,
        days_until_buffer_empty=_finite(result.days_until_buffer_empty),
        available_source_volume_m3=_finite(result.available_source_volume_m3),
        source_volume_used_m3=result.source_volume_used_m3,
        days_until_source_empty=_finite(result.days_until_source_empty),
        **_soil_output(input, result),
    )


@log_tool_call
async def calculate_supply_given_supply(
    ctx, input: SupplyInputGivenSupply
) -> SupplyOutput:
    """Wat doet deze inlaatcapaciteit met de waterstand en met de onvervulde watervraag?

    Aanvoeren = supply.
    """
    state = _state(input)
    deficit = _deficit(input)
    soil = _soil(input)
    capacity = input.supply_capacity_m3_per_sec + input.delta_supply_capacity_m3_per_sec
    result = evaluate_supply(state, deficit, capacity, soil=soil)

    def answer_for(volume):
        variant = evaluate_supply(state, _deficit(input, volume), capacity, soil=soil)
        # de voorwaartse tool meldt wat er overblijft, dus dat is wat er varieert
        return variant.shortfall_mm, None

    def answer_for_variant(variant):
        evaluated = evaluate_supply(
            _variant_state(variant, input),
            _varied_deficit(input, variant),
            capacity,
            soil=soil,
        )
        return evaluated.shortfall_mm, None

    assumptions = assumed_defaults(input)
    caveats = model_caveats(
        input,
        is_drought=True,
        required_supply_volume_m3=_required_volume_m3(input, result),
        source_volume_is_modelled=input.available_source_volume_m3 is not None,
        salinisation_is_the_next_step=True,
        **_soil_caveat_context(input),
        **_demand_caveat_context(input),
        **_drought_caveat_context(input),
    )
    sensitivity = _assumed_spread(input, answer_for_variant) + _source_spread(
        input, answer_for
    )
    return SupplyOutput(
        data=_data(input, result),
        description=append_assumptions(
            append_source(
                append_spread(
                    describe_supply_forward(result, input, input.language),
                    sensitivity,
                    result.shortfall_mm,
                    "mm onvervulde vraag"
                    if input.language != "en"
                    else "mm of unmet demand",
                    input.language,
                ),
                result,
                input,
                input.language,
            ),
            assumptions,
            input.language,
        ),
        status=result.status,
        assumptions=assumptions,
        caveats=caveats,
        sensitivity=sensitivity,
        priceless=[
            PricelessPost(**post)
            for post in priceless_posts(input, AanvoerenAction.name_nl)
        ],
        measure=_supply_measure(result),
        supply_capacity_m3_per_sec=result.supply_capacity_m3_per_sec,
        demand_mm=result.demand_mm,
        supplied_mm=result.supplied_mm,
        buffer_mm=result.buffer_mm,
        shortfall_mm=result.shortfall_mm,
        drawdown_m=result.drawdown_m,
        days_until_buffer_empty=_finite(result.days_until_buffer_empty),
        available_source_volume_m3=_finite(result.available_source_volume_m3),
        source_volume_used_m3=result.source_volume_used_m3,
        days_until_source_empty=_finite(result.days_until_source_empty),
        **_soil_output(input, result),
    )
