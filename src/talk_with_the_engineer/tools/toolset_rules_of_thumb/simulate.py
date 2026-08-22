"""Waterbalans van een polder: de rekenkern van de vuistregels.

Vier stappen, elk gevectoriseerd:

1. `delay_daily`  - vertraag de afvoer van een deel van het gebied (maatregel vasthouden)
2. `clamped_scan` - de geklemde peilrecursie, het enige primitief van de balans
3. `water_level_series` - de waterbalans zelf, uitgedrukt in dat primitief
4. `max_water_level` - de maximale waterstandstijging, waar de vuistregels op sturen

De uitkomsten zijn gevalideerd tegen `scripts/scripts_Ton/TttE_v03.xlsx`; zie
tests/src/tools/test_reference_ton.py.
"""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_discharge import (
    _get_discharge_curve,
    _get_model_matrix,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_rainfall import (
    get_rainfall,
)

HOURS_PER_DAY = 24
M3_PER_SEC_PER_L_PER_SEC_PER_HA = (
    1e-3  # l/s/ha maal ha geeft l/s, gedeeld door 1000 m3/s
)
SQUARE_METRES_PER_HECTARE = 1e4
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86_400


def clamped_scan(
    delta: np.ndarray,
    lower_bound_m: float = 0.0,
    upper_bound_m: float = np.inf,
    initial_level_m: float = 0.0,
) -> np.ndarray:
    """Los `h[t] = clamp(h[t-1] + delta[t], lo, hi)` op over de laatste as van `delta`.

    Dit is het enige primitief van de waterbalans. De klem *is* het peilbeheer: de
    ondergrens is het niveau waar het gemaal stopt, de bovengrens het niveau waar de
    inlaat stopt. Drie standen van dezelfde functie:

        lo=0,   hi=+inf   wateroverlast - het gemaal pompt tot streefpeil en niet verder
        lo=-inf, hi=0     watertekort   - de inlaat vult tot streefpeil en niet verder
        lo=-m,  hi=+inf   peilbeheer met marge - het gemaal mag `m` meter voormalen

    Geklemde translaties `f(x) = clamp(x + a, l, u)` zijn gesloten onder compositie:

        combine((a1,l1,u1), (a2,l2,u2)) = (a1+a2,
                                           clamp(l1+a2, l2, u2),
                                           clamp(u1+a2, l2, u2))

    Die compositie is associatief, dus de recursie is een prefix-scan met log-diepte in
    plaats van een lus over de tijd. Hier stond eerder `cumsum` met `minimum.accumulate`;
    dat is exact het bijzondere geval `lo=0, hi=+inf`, en het kon de gespiegelde klem van
    de droogtekant niet aan.

    De laatste as is de tijd, zodat er een knoop-as voor kan staan: een heel netwerk van
    polders op dezelfde topologische diepte gaat in een aanroep.

    Geschreven in de numpy-deelverzameling die JAX een-op-een ondersteunt - geen lus over
    de tijd, geen `if` op een arraywaarde, geen `.item()` - zodat dezelfde kern later
    differentieerbaar en op een GPU te draaien is. `test_the_core_uses_only_the_portable_numpy_subset`
    houdt dat vast.
    """
    if np.any(np.asarray(lower_bound_m) > np.asarray(upper_bound_m)):
        raise ValueError("lower_bound_m kan niet boven upper_bound_m liggen")

    # Snelpad: met maar EEN eindige grens is dit nog steeds een gewone gereflecteerde walk,
    # ook als die grens niet nul is. Substitueer g = h - lo en je hebt de recursie
    # `g[t] = max(g[t-1] + d[t], 0)` met startwaarde `g0 = h0 - lo`, en daarvoor geldt
    #
    #     g[t] = S[t] - min(-g0, min_{s<=t} S[s])   met S = cumsum(d)
    #
    # Dat is een `cumsum` en een `minimum.accumulate` in plaats van log(T) passes over drie
    # arrays, en op 8500 knopen is dat het verschil tussen 125 en 25 ms. De volledige scan
    # blijft nodig zodra beide grenzen eindig zijn - de droogteband - en dat is per definitie
    # een reeks per knoop en geen netwerk.
    #
    # De bovengrens is gespiegeld hetzelfde, dus die gaat via een tekenwisseling.
    if np.all(np.isposinf(upper_bound_m)):
        return _reflected_scan(delta, lower_bound_m, initial_level_m)
    if np.all(np.isneginf(lower_bound_m)):
        return -_reflected_scan(
            -np.asarray(delta, dtype=float),
            -np.asarray(upper_bound_m),
            -initial_level_m,
        )

    shift = np.asarray(delta, dtype=float).copy()
    length = shift.shape[-1]
    lower = np.broadcast_to(np.asarray(lower_bound_m, dtype=float), shift.shape).copy()
    upper = np.broadcast_to(np.asarray(upper_bound_m, dtype=float), shift.shape).copy()

    step = 1
    while step < length:
        shift_right = shift[..., step:].copy()
        lower_right = lower[..., step:].copy()
        upper_right = upper[..., step:].copy()
        shift_left = shift[..., :-step]
        lower_left = lower[..., :-step]
        upper_left = upper[..., :-step]

        shift[..., step:] = shift_left + shift_right
        lower[..., step:] = np.minimum(
            np.maximum(lower_left + shift_right, lower_right), upper_right
        )
        upper[..., step:] = np.minimum(
            np.maximum(upper_left + shift_right, lower_right), upper_right
        )
        step *= 2

    return np.minimum(np.maximum(initial_level_m + shift, lower), upper)


def _reflected_scan(delta, lower_bound_m, initial_level_m=0.0) -> np.ndarray:
    """`h[t] = max(h[t-1] + delta[t], lo)` via cumsum; het snelpad van `clamped_scan`.

    `lower_bound_m` moet broadcastbaar zijn tegen `delta`, dus scalair of met een tijdas
    van lengte 1 - net als bij `clamped_scan`. Voeg er geen as aan toe: met een grens van
    vorm (n, 1) tegen een reeks van vorm (n, T) levert een extra as (n, n, T) op, en dat is
    op 8500 knopen 15 TB in plaats van 15 MB. Dat is precies een keer gebeurd.
    """
    delta = np.asarray(delta, dtype=float)
    lower_bound_m = np.asarray(lower_bound_m, dtype=float)
    start_above_floor = np.asarray(initial_level_m, dtype=float) - lower_bound_m

    zeros = np.zeros(delta.shape[:-1] + (1,))
    cumulative = np.concatenate([zeros, np.cumsum(delta, axis=-1)], axis=-1)
    running_minimum = np.minimum(
        np.minimum.accumulate(cumulative, axis=-1), -start_above_floor
    )
    return (cumulative - running_minimum)[..., 1:] + lower_bound_m


def slack_of(
    water_level_m: np.ndarray, delta: np.ndarray, initial_level_m: float = 0.0
) -> np.ndarray:
    """Wat de klem per tijdstap heeft toegevoegd of weggenomen [m].

        slack[t] = h[t] - (h[t-1] + delta[t])

    Positief betekent dat de ondergrens de stand omhoog hield: het gemaal draaide onder
    capaciteit, of - op de droogtekant - er was vraag die de inlaat niet kon leveren.
    Negatief betekent dat de bovengrens water heeft afgevoerd.

    Dit is de enige afgeleide grootheid die de balans nodig heeft. Het werkelijk
    weggepompte debiet, de onbenutte capaciteit, het aangevoerde debiet en de onvervulde
    vraag zijn er alle vier een teken en een factor van verwijderd. Eerder werd de
    onbenutte capaciteit apart uit `minimum.accumulate` gehaald; dat werkte alleen voor
    de eenzijdige klem.
    """
    previous = np.concatenate(
        [
            np.full(water_level_m.shape[:-1] + (1,), initial_level_m),
            water_level_m[..., :-1],
        ],
        axis=-1,
    )
    return water_level_m - (previous + np.asarray(delta, dtype=float))


def water_balance(
    drainage_l_s_ha: np.ndarray,
    area_open_water_ha: float,
    area_land_ha: float,
    pump_capacity_m3_per_sec: float,
    inflow_m3_per_sec: np.ndarray | None = None,
    direct_precipitation_m: np.ndarray | None = None,
    level_margin_m: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Waterstand [m], werkelijk verplaatst debiet [m3/s] en de slack-reeks [m].

    De recursie is `h[t] = clamp(h[t-1] + d[t], -level_margin_m, +inf)` met `d[t]` de
    peilverandering per uur als het gemaal op capaciteit draait; zie `clamped_scan`.

    `level_margin_m` is hoe diep onder het streefpeil het gemaal mag doormalen. Nul is het
    klassieke gedrag: het gemaal stopt op streefpeil. Groter dan nul is voorbemaling, en
    dan kan `h` negatief worden.

    Het gemaal draait alleen als er water is. `slack_of` levert precies de ongebruikte
    capaciteit, en dus is het werkelijk verplaatste debiet daaruit af te leiden. Dat is
    nodig zodra polders in een cascade staan: wat de een wegpompt is de aanvoer van de
    ander.

    `water_level_series` is deze functie zonder de slack-reeks, en bestaat omdat zes
    aanroepplekken twee retourwaarden verwachten. Wie de slack wil - de cascade, en elke
    massabalanstest - roept deze aan en rekent hem niet terug uit `pumped`.

    Het rekenblad gebruikt `Q[t-1]` waar deze functie `Q[t]` gebruikt. De reeks is daarmee
    een tijdstap verschoven; het maximum is identiek en alleen het maximum wordt gebruikt.
    """
    if area_open_water_ha <= 0:
        raise ValueError("area_open_water_ha moet groter dan nul zijn")
    if level_margin_m < 0:
        raise ValueError("level_margin_m kan niet negatief zijn")

    inflow = np.asarray(drainage_l_s_ha, dtype=float) * area_land_ha
    inflow *= M3_PER_SEC_PER_L_PER_SEC_PER_HA
    if inflow_m3_per_sec is not None:
        inflow = inflow + np.asarray(inflow_m3_per_sec, dtype=float)

    # peilverandering per uur bij een gemaal dat op capaciteit draait
    metres_per_m3_per_sec = SECONDS_PER_HOUR / (
        area_open_water_ha * SQUARE_METRES_PER_HECTARE
    )
    delta = (inflow - pump_capacity_m3_per_sec) * metres_per_m3_per_sec
    if direct_precipitation_m is not None:
        delta = delta + np.asarray(direct_precipitation_m, dtype=float)

    water_level_m = clamped_scan(delta, -level_margin_m, np.inf)
    slack_m = slack_of(water_level_m, delta)
    pumped_m3_per_sec = pump_capacity_m3_per_sec - slack_m / metres_per_m3_per_sec
    return water_level_m, pumped_m3_per_sec, slack_m


def water_level_series(
    drainage_l_s_ha: np.ndarray,
    area_open_water_ha: float,
    area_land_ha: float,
    pump_capacity_m3_per_sec: float,
    inflow_m3_per_sec: np.ndarray | None = None,
    direct_precipitation_m: np.ndarray | None = None,
    level_margin_m: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Waterstand ten opzichte van streefpeil [m] en werkelijk verplaatst debiet [m3/s].

    `water_balance` zonder de slack-reeks. Zie daar voor de recursie en de conventies.
    """
    water_level_m, pumped_m3_per_sec, _ = water_balance(
        drainage_l_s_ha,
        area_open_water_ha,
        area_land_ha,
        pump_capacity_m3_per_sec,
        inflow_m3_per_sec,
        direct_precipitation_m,
        level_margin_m,
    )
    return water_level_m, pumped_m3_per_sec


def max_water_level(
    drainage_l_s_ha: np.ndarray,
    area_open_water_ha: float,
    area_land_ha: float,
    pump_capacity_m3_per_sec: float,
    inflow_m3_per_sec: np.ndarray | None = None,
) -> float:
    """De maximale waterstandstijging [m]; de grootheid waar de vuistregels op sturen."""
    water_level_m, _ = water_level_series(
        drainage_l_s_ha,
        area_open_water_ha,
        area_land_ha,
        pump_capacity_m3_per_sec,
        inflow_m3_per_sec,
    )
    return float(water_level_m.max())


def delay_daily(daily: np.ndarray, days_to_retain: int) -> np.ndarray:
    """Spreid elke dagafvoer uit over `1 + days_to_retain` dagen.

    Massaconserverend per constructie: de kernel telt op tot 1, dus het totale volume
    verandert niet. De uitvoer is `days_to_retain` dagen langer dan de invoer, want de
    staart schuift door.

    Dit vervangt een schema van negen hardgecodeerde 24-uursblokken dat een vast venster
    van drie dagen gebruikte met een factor `1/(1 + days_to_retain)`. Massa bleef daarmee
    alleen behouden bij `days_to_retain = 2`, en het schema indexeerde hard tot uur 216
    waardoor het op kortere reeksen omviel. Bij `days_to_retain = 2` geeft deze
    convolutie dezelfde waarden als dat schema.
    """
    if days_to_retain < 0:
        raise ValueError("days_to_retain kan niet negatief zijn")
    window = 1 + days_to_retain
    return np.convolve(np.asarray(daily, dtype=float), np.ones(window) / window)


def to_daily(hourly: np.ndarray) -> np.ndarray:
    """Sample een uurreeks die per dag constant is terug naar dagwaarden."""
    hourly = np.asarray(hourly, dtype=float)
    if len(hourly) % HOURS_PER_DAY:
        raise ValueError(f"uurreeks van {len(hourly)} uur is geen heel aantal dagen")
    return hourly.reshape(-1, HOURS_PER_DAY)[:, 0]


def to_hourly(daily: np.ndarray) -> np.ndarray:
    """Herhaal dagwaarden naar uurwaarden."""
    return np.repeat(np.asarray(daily, dtype=float), HOURS_PER_DAY)


def blend_retention(
    drainage_daily: np.ndarray, days_to_retain: int, retention_fraction: float
) -> np.ndarray:
    """Meng de onvertraagde en de vertraagde afvoer naar rato van het retentie-areaal.

    `retention_fraction` is de fractie van het LANDoppervlak waarvan de afvoer wordt
    vertraagd; de rest van het gebied voert onvertraagd af.
    """
    if not 0.0 <= retention_fraction <= 1.0:
        raise ValueError(
            f"retention_fraction moet tussen 0 en 1 liggen, kreeg {retention_fraction}"
        )
    if retention_fraction == 0.0:
        return np.asarray(drainage_daily, dtype=float)

    delayed = delay_daily(drainage_daily, days_to_retain)
    undelayed = np.zeros_like(delayed)
    undelayed[: len(drainage_daily)] = drainage_daily
    return (1.0 - retention_fraction) * undelayed + retention_fraction * delayed


@dataclass
class SimulationResult:
    """Uitkomst van een doorrekening, met twee uitlezingen van dezelfde doorrekening.

    `dh_max_m` is de wateroverlast-uitlezing: de maximale stijging boven het streefpeil.
    `retained_volume_mm` is de droogte-uitlezing: de voorraad die het gemaal niet wegpompt.
    Ze delen een schaarse grootheid - drooglegging - want peilopzet vergroot de voorraad en
    verkleint de marge tot inundatie met exact hetzelfde aantal centimeters. Dat is de
    spanning tussen te nat en te droog, mechanisch gemaakt.
    """

    dh_max_m: float
    water_level_m: np.ndarray
    pumped_m3_per_sec: np.ndarray
    slack_m: np.ndarray
    """Wat de klem per uur toevoegde of wegnam; zie `slack_of`.

    Alle debietuitlezingen zijn hiervan afgeleid. Staat in de uitkomst omdat de cascade
    hem nodig heeft en omdat een massabalanstest hem anders opnieuw moet uitrekenen.
    """
    level_margin_m: float
    """De peilmarge waarmee gerekend is; nul betekent dat het gemaal op streefpeil stopt."""
    dh_min_m: float
    """De laagste stand ten opzichte van het streefpeil [m]; nul zolang er geen marge is."""
    drainage_l_s_ha: np.ndarray
    rainfall_per_day_mm: np.ndarray
    """Neerslag op het land, dus na aftrek van het zomerse neerslagverlies."""
    rainfall_on_water_per_day_mm: np.ndarray
    """Neerslag op het open water, zonder aftrek; in de winter gelijk aan de vorige."""
    volume_rain_mm: float
    retained_volume_mm: float
    """Droogte-uitlezing: voorraad onder het streefpeil, in mm over de hele polder."""
    target_level_rise_m: float
    """De peilopzet waarmee die voorraad is opgebouwd; kost even zoveel drooglegging."""

    @property
    def rain_loss_mm(self) -> float:
        """Het neerslagverlies [mm]: het verschil tussen de twee reeksen hierboven.

        Nul in de winter. In de zomer 20 mm, of minder als er in de eerste twee dagen van
        het patroon minder valt. Uit het verschil van de reeksen en niet uit
        SUMMER_LOSS_MM, zodat het altijd is wat er werkelijk is afgetrokken.
        """
        return float(
            self.rainfall_on_water_per_day_mm.sum() - self.rainfall_per_day_mm.sum()
        )

    @property
    def dh_total_above_original_datum_m(self) -> float:
        """Stijging boven het OORSPRONKELIJKE streefpeil, dus inclusief de peilopzet.

        Dit is de grootheid waaraan een inundatienorm getoetst moet worden zodra er
        peilopzet in het spel is: `dh_max_m` meet boven het opgezette peil.
        """
        return self.target_level_rise_m + self.dh_max_m


def drainage_per_day(storm, rainfall_per_day_mm: np.ndarray) -> np.ndarray:
    """Neerslag-afvoerrelatie: dagneerslag [mm] naar dagafvoer [mm]."""
    discharge_curve = _get_discharge_curve(storm.days_to_discharge)
    flow_per_day, _ = _get_model_matrix(storm, rainfall_per_day_mm, discharge_curve)
    return flow_per_day


@lru_cache(maxsize=None)
def _drainage_daily_for_storm(
    return_period,
    time_of_year,
    length_event_hrs,
    rainfall_regime,
    name_rainfall_pattern,
    days_to_discharge,
    apply_summer_loss,
):
    """Dagafvoer en neerslag voor een bui, met en zonder neerslagverlies.

    Het zomerse neerslagverlies is een bodemproces - infiltratie in het freatisch pakket
    plus verdamping - en geldt dus alleen voor de neerslag die op het land valt. De
    neerslag die direct op het open water valt gaat er ongereduceerd in: er is geen bodem
    om in te zakken. Bevestigd door Ton Botterhuis, augustus 2026. Daarom twee reeksen.

    Gecacht om dezelfde reden als `_rainfall_for_storm`: de inverse tools rekenen een bui
    tientallen keren door en de bui verandert daarbij niet, alleen de toestand.
    """
    storm = _StormKey(
        return_period,
        time_of_year,
        length_event_hrs,
        rainfall_regime,
        name_rainfall_pattern,
        days_to_discharge,
    )
    # neerslag op land: met verlies, want daar zakt het in de bodem
    rainfall_on_land_mm, volume_rain_mm = get_rainfall(
        storm, apply_summer_loss=apply_summer_loss
    )
    # neerslag op open water: zonder verlies. In de winter zijn beide gelijk.
    rainfall_on_water_mm, _ = get_rainfall(storm, apply_summer_loss=False)
    return (
        drainage_per_day(storm, rainfall_on_land_mm),
        rainfall_on_land_mm,
        rainfall_on_water_mm,
        volume_rain_mm,
    )


@dataclass(frozen=True)
class _StormKey:
    """Minimale bui-representatie; wat `get_rainfall` en de modelmatrix nodig hebben."""

    return_period: int
    time_of_year: str
    length_event_hrs: float
    rainfall_regime: str
    name_rainfall_pattern: str
    days_to_discharge: int


def simulate(
    state: PolderState,
    storm,
    inflow_m3_per_sec: np.ndarray | None = None,
    apply_summer_loss: bool = True,
) -> SimulationResult:
    """Reken een bui door op een polder-toestand.

    Dit is de transitie `f(s, w)`. Maatregelen zitten niet in deze functie: die veranderen
    de toestand die erin gaat (zie `models/modelset_rules_of_thumb/actions.py`).
    """
    (
        drainage_daily_mm,
        rainfall_per_day_mm,
        rainfall_on_water_per_day_mm,
        volume_rain_mm,
    ) = _drainage_daily_for_storm(
        storm.return_period,
        storm.time_of_year,
        storm.length_event_hrs,
        storm.rainfall_regime,
        storm.name_rainfall_pattern,
        storm.days_to_discharge,
        apply_summer_loss,
    )

    if state.retention_fraction > 0:
        drainage_daily_mm = blend_retention(
            drainage_daily_mm, state.days_to_retain, state.retention_fraction
        )

    # mm/dag -> mm/uur -> l/s/ha
    drainage_l_s_ha = to_hourly(drainage_daily_mm / HOURS_PER_DAY * 10 / 3.6)

    # Neerslag die direct op het open water valt, verhoogt de stand met exact de
    # neerslagdiepte: het volume is P/1000 maal het oppervlak, en gedeeld door datzelfde
    # oppervlak blijft P/1000 m over. Onvertraagd, want er is geen bodem om door te
    # sijpelen, en zonder neerslagverlies om dezelfde reden.
    per_hour_m = to_hourly(rainfall_on_water_per_day_mm / HOURS_PER_DAY) / 1000.0
    direct_precipitation_m = np.zeros(len(drainage_l_s_ha))
    overlap = min(len(per_hour_m), len(direct_precipitation_m))
    direct_precipitation_m[:overlap] = per_hour_m[:overlap]

    water_level_m, pumped_m3_per_sec, slack_m = water_balance(
        drainage_l_s_ha,
        state.area_open_water_ha,
        state.area_land_ha,
        state.pump_capacity_m3_per_sec,
        inflow_m3_per_sec,
        direct_precipitation_m,
        state.level_margin_m,
    )
    return SimulationResult(
        dh_max_m=float(water_level_m.max()),
        water_level_m=water_level_m,
        pumped_m3_per_sec=pumped_m3_per_sec,
        slack_m=slack_m,
        level_margin_m=state.level_margin_m,
        dh_min_m=float(water_level_m.min()),
        drainage_l_s_ha=drainage_l_s_ha,
        rainfall_per_day_mm=rainfall_per_day_mm,
        rainfall_on_water_per_day_mm=rainfall_on_water_per_day_mm,
        volume_rain_mm=float(volume_rain_mm),
        retained_volume_mm=state.retained_volume_mm,
        target_level_rise_m=state.target_level_rise_m,
    )


@dataclass
class DeficitResult:
    """Uitkomst van een droogtedoorrekening: dezelfde kern, gespiegelde klem.

    Waar de natte kant vraagt hoe hoog het water komt, vraagt de droge kant hoe diep het
    zakt en hoeveel vraag onvervuld blijft. Beide komen uit `clamped_scan`; het verschil
    zit in de klem en in de exogene reeks, niet in de recursie.
    """

    dh_min_m: float
    """De diepste uitzakking onder streefpeil [m]; negatief of nul."""
    water_level_m: np.ndarray
    slack_m: np.ndarray
    supplied_m3_per_sec: np.ndarray
    """Werkelijk ingelaten debiet; de spiegel van `pumped_m3_per_sec`."""
    demand_mm: float
    """Totale vraag over de periode, in mm over het hele gebied."""
    supplied_mm: float
    """Wat de inlaat heeft geleverd."""
    buffer_mm: float
    """Wat uit de eigen berging onder streefpeil is gekomen."""
    shortfall_mm: float
    """Vraag die noch de inlaat noch de berging kon dekken.

    Dit is de spiegel van de onbenutte gemaalcapaciteit: `slack` op de ondergrens. En het
    is een bruikbare droogte-uitlezing waar het weggepompte volume dat niet was, want hij
    is begrensd door een fysieke ondergrens en niet door de lengte van het rekenvenster.
    Zie PLAN_TOOLS_REFACTOR.md Sec. 8.2 voor de uitlezing die daarop sneuvelde.
    """
    days_until_buffer_empty: float
    """Wanneer de stand de ondergrens raakt [dagen]; `inf` als dat niet gebeurt."""
    level_margin_m: float

    @property
    def is_covered(self) -> bool:
        """Dekt de aanvoer de vraag, zodat het streefpeil gehouden wordt?"""
        return self.shortfall_mm <= 0.0


def simulate_deficit(state: PolderState, deficit) -> DeficitResult:
    """Reken een neerslagtekort door op een polder-toestand.

    Dezelfde transitie als `simulate`, met de klem gespiegeld: `lo = -level_margin_m` en
    `hi = 0`, want de inlaat vult tot streefpeil en niet verder. Zonder die tweezijdige
    vorm is droogte onzichtbaar - met de eenzijdige klem staat de hele reeks op nul.

    Twee verschillen met de natte kant, en beide zijn bewust:

    * de vraag omzeilt de neerslag-afvoerrelatie. Tabel 39 beschrijft hoe neerslag tot
      *afvoer* komt; een tekort is geen negatieve afvoer maar een *vraag* - capillaire
      opstijging, gewasverdamping, wegzijging - en die komt onvertraagd uit het
      oppervlaktewater. `days_to_discharge` en `retention_fraction` doen hier dus niets.
    * de forcering is twee expliciete getallen en geen statistiek. Welke droogtereeks hier
      thuishoort staat open (PLAN_UITWISSELING_EN_NETWERK.md V7), en een verkeerd gekozen
      statistiek is erger dan een expliciet getal.

    De twee vraagtermen zijn de exacte spiegel van de natte kant: het land vraagt naar rato
    van zijn oppervlak, en het open water verliest de tekortdiepte direct.
    """
    hours = int(deficit.length_days) * HOURS_PER_DAY
    area_open_water_m2 = state.area_open_water_ha * SQUARE_METRES_PER_HECTARE
    metres_per_m3_per_sec = SECONDS_PER_HOUR / area_open_water_m2

    demand_land_m3_per_sec = (
        deficit.deficit_mm_per_day
        / 1000.0
        * state.area_land_ha
        * SQUARE_METRES_PER_HECTARE
        / SECONDS_PER_DAY
    )
    demand_open_water_m_per_hour = deficit.deficit_mm_per_day / 1000.0 / HOURS_PER_DAY
    supply_capacity = state.supply_capacity_m3_per_sec

    delta = np.full(
        hours,
        (supply_capacity - demand_land_m3_per_sec) * metres_per_m3_per_sec
        - demand_open_water_m_per_hour,
    )
    water_level_m = clamped_scan(delta, -state.level_margin_m, 0.0)
    slack_m = slack_of(water_level_m, delta)
    # De twee klemmen betekenen iets anders, en dat is het hele punt van een tweezijdige
    # band. Op de ONDERGRENS kan het peil niet verder zakken: de inlaat draait voluit en
    # wat er ontbreekt is onvervulde vraag, dus `slack > 0` is het tekort. Op de
    # BOVENGRENS kan het peil niet boven streefpeil komen: de inlaat knijpt dan af, dus
    # `slack < 0` is capaciteit die niet is gebruikt.
    unmet_m = np.maximum(slack_m, 0.0)
    throttled_m = np.minimum(slack_m, 0.0)
    supplied_m3_per_sec = supply_capacity + throttled_m / metres_per_m3_per_sec

    over_polder = (
        area_open_water_m2 / (state.area_ha * SQUARE_METRES_PER_HECTARE) * 1000.0
    )
    shortfall_mm = float(unmet_m.sum()) * over_polder
    demand_mm = deficit.deficit_mm_per_day * deficit.length_days
    # uit de reeks en niet uit de capaciteit maal de tijd: een inlaat die groter is dan de
    # vraag levert de vraag en niet zijn capaciteit, en anders sluit de balans niet
    supplied_mm = (
        float(supplied_m3_per_sec.sum())
        * SECONDS_PER_HOUR
        / (state.area_ha * SQUARE_METRES_PER_HECTARE)
        * 1000.0
    )

    on_the_floor = water_level_m <= -state.level_margin_m + 1e-12
    days_until_buffer_empty = (
        float(np.argmax(on_the_floor)) / HOURS_PER_DAY
        if bool(on_the_floor.any())
        else float("inf")
    )
    return DeficitResult(
        dh_min_m=min(float(water_level_m.min()), 0.0),
        water_level_m=water_level_m,
        slack_m=slack_m,
        supplied_m3_per_sec=supplied_m3_per_sec,
        demand_mm=demand_mm,
        supplied_mm=supplied_mm,
        # abs en niet max: `max(-0.0, 0.0)` geeft in Python -0.0 terug, en dan staat er
        # "-0 mm berging" in de uitvoer
        buffer_mm=abs(min(float(water_level_m.min()), 0.0)) * over_polder,
        shortfall_mm=shortfall_mm,
        days_until_buffer_empty=days_until_buffer_empty,
        level_margin_m=state.level_margin_m,
    )
