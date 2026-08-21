# Plan van aanpak — rules of thumb als world model

Versie 2 · 21 augustus 2026

## 1. Doel en scope

**In scope**

1. De zes bestaande rules-of-thumb tools correct laten rekenen en correct laten
   rapporteren.
2. Invoer- en uitvoermodellen die één canonieke toestand hebben in plaats van een
   dimensieloos percentage met een impliciet referentieoppervlak.
3. Tweerichtingsverkeer dat sluit waar de logica dat toelaat, en dat expliciet meldt waar
   het dat niet doet.
4. Een robuustheidscurve als demo: per terugkeertijd het goedkoopste maatregelpakket dat
   onder een norm blijft.

**Buiten scope** — expliciet, om scope creep te voorkomen

| onderwerp | reden |
|---|---|
| Zaagtandpatroon over een tijdas | vereist klimaatdrift op de neerslagstatistiek; niet nodig voor de robuustheidscurve |
| KNMI'23-veranderfactoren | volgt uit het bovenstaande |
| Cascade van polders (implementatie) | de interfaces worden vrijgehouden in WP3, de bouw komt na WP7 |
| Opstuwing / benedenstroomse begrenzing | vereist een gekoppelde tijdstap over knopen |
| Terugkerende kosten (energie, onderhoud, inundatievergoeding) | pas relevant met een tijdas |

Werkpakketten worden in volgorde WP0 → WP7 uitgevoerd. De demo krijgt geen regel code
voordat WP7 is afgerond.

---

## 2. Uitgangssituatie

### 2.1 Vaste randvoorwaarde: de rekenkern mag niet wijzigen

De waterbalans is gevalideerd tegen `scripts/scripts_Ton/TttE_v03.xlsx` en reproduceert
alle drie de maatregelcurves tot op machineprecisie, via de eigen neerslag- en
afvoerroutines:

| maatregel | vergeleken punten | grootste afwijking |
|---|---|---|
| bergen | 12 (3,5 % → 6,25 % open water) | 5,3·10⁻¹⁵ m |
| afvoeren | 12 (5 → 7 m³/s) | 8,9·10⁻¹⁶ m |
| vasthouden | 11 (0 → 100 %) | 5,8·10⁻¹⁵ m |

**Elke wijziging in dit plan moet die reproductie intact laten.** Wat fout is, zit in de
parameterisatie en de rapportage — niet in de fysica.

### 2.2 Referentiecasus

`scripts/scripts_Ton/drainage.csv` is de afvoerreeks van:

```
winter · T = 1000 jaar · 96 uur · patroon p1a · days_to_discharge = 4 · regime R
polder 4000 ha · 3,5 % open water · 5 m³/s gemaalcapaciteit
```

L1-fout tussen de berekende en de opgeslagen reeks: 0,00 mm. Deze casus is de gouden
regressietest. De defaults in `RainfallInput` zijn `p1c` en `days_to_discharge=3`, dus
wie de tool met defaults naast het rekenblad legt krijgt 2,16 m in plaats van 1,70 m.

### 2.3 Conventies die bewust blijven staan

| conventie | detail |
|---|---|
| Tijdstapverschuiving | Het rekenblad gebruikt `Q[t−1]` in `h[t]`, de Python-code `Q[t]`. De reeks is één stap verschoven; het maximum is identiek, en alleen het maximum wordt gebruikt. Vastleggen in een comment. |
| Haalbaarheidsgrens | Het rekenblad extrapoleert voorbij het fysiek haalbare (500 % open water). Deze implementatie rapporteert daar `INFEASIBLE`. Bewuste afwijking; vastleggen in de test. |

---

## 3. Doelarchitectuur

### 3.1 Toestand, actie, simulatie

Eén toestand, één simulatie, drie acties. `PolderState` bevat wat er van de polder bekend
moet zijn; `Storm` is de exogene bui; `simulate(state, storm)` levert de waterstandreeks
en haar maximum. Een maatregel is geen parameter in de simulatie maar een mutatie van de
toestand:

| maatregel | toestandscomponent |
|---|---|
| bergen | `pct_open_water` |
| afvoeren | `pump_capacity_m3_per_sec` |
| vasthouden | `retention_fraction` |

Vooruit rekenen is `simulate(action.apply(state), storm)`. Achteruit rekenen is bisectie
op de maatvoering van diezelfde actie. De maatregelnamen blijven bestaan als getypeerde
acties; wat verdwijnt is dat elke tool zijn eigen sweep, eigen interpolatie en eigen
referentieberekening heeft.

### 3.2 Bestandsindeling

```
models/modelset_rules_of_thumb/
    base_rule_of_thumb.py   AANPASSEN     Storm, WaterSystemInput (= toolgrens), to_state()
    state.py                NIEUW         PolderState
    actions.py              NIEUW         BergenAction, AfvoerenAction, VasthoudenAction
    results.py              NIEUW         SimulationResult, SolveResult, SolveStatus, LimitReason
    store.py                AANPASSEN     tool-I/O + state_after, bereik, status
    retain.py               AANPASSEN     idem
    discharge.py            AANPASSEN     idem

tools/toolset_rules_of_thumb/
    simulate.py             NIEUW         waterbalans + vertraging, gevectoriseerd
    solve.py                NIEUW         gulden snede, bisectie, haalbaarheid
    utils_rainfall.py       AANPASSEN     D8, V3-schakelaar
    utils_discharge.py      AANPASSEN     D2, D12
    utils_calculations.py   VERWIJDEREN   gaat op in simulate.py
    store.py                HERSCHRIJVEN  dunne wrapper
    retain.py               HERSCHRIJVEN  dunne wrapper
    discharge.py            HERSCHRIJVEN  dunne wrapper
```

Ongewijzigd: de zes functienamen en hun modulepaden, de zes MCP-endpoints en FastAPI-routes
in `tools_router_RulesOfThumb.py`, en de modelnamen in `models/__init__.py`. Voor de agent
verandert niets.

### 3.3 Rekenkern

**Waterstand.** De recursie `h[t] = max(h[t−1] + d[t], 0)` met `h[0] = 0` is een
gereflecteerde random walk en gelijk aan `h[t] = S[t] − min(S[0..t])`:

```python
def water_level_series(drainage_l_s_ha, area_open_water_ha, area_land_ha,
                       pump_capacity_m3_per_sec, inflow_m3_per_sec=None):
    """Waterstandstijging boven streefpeil [m] en werkelijk verplaatst debiet [m3/s].

    Neemt losse getallen en geen PolderState: de fysica hoeft geen pydantic-model te
    kennen. `simulate` doet de vertaling.
    """
    q = drainage_l_s_ha * area_land_ha / 1000.0                  # m3/s
    if inflow_m3_per_sec is not None:
        q = q + inflow_m3_per_sec
    c = 3600.0 / (area_open_water_ha * 1e4)                      # m3/s -> m per uur
    d = (q - pump_capacity_m3_per_sec) * c
    s = np.concatenate([[0.0], np.cumsum(d)])
    m = np.minimum.accumulate(s)
    return (s - m)[1:], pump_capacity_m3_per_sec + np.diff(m) / c
```

De tweede retourwaarde is het **werkelijk verplaatste debiet**: de toenames van
`minimum.accumulate(s)` zijn exact de ongebruikte gemaalcapaciteit per uur. Nodig voor de
cascade (§8.2), en gratis.

**Vertraging.** Spreid elke dagafvoer uit over `1 + dT` dagen:

```python
def delay_daily(daily, days_to_retain):
    w = 1 + days_to_retain
    return np.convolve(daily, np.ones(w) / w)                    # lengte len(daily) + w - 1
```

Massaconserverend per constructie, en bij `dT = 2` gelijk aan het bestaande
24-uursblokkenschema.

**Simulatie.**

```python
def simulate(state, storm, inflow_m3_per_sec=None) -> SimulationResult:
    rain_per_day = get_rainfall(storm)
    drainage_daily = get_drainage_daily(storm, rain_per_day)      # mm/dag

    if state.retention_fraction > 0:
        delayed = delay_daily(drainage_daily, state.days_to_retain)
        base = np.pad(drainage_daily, (0, len(delayed) - len(drainage_daily)))
        f = state.retention_fraction
        drainage_daily = (1 - f) * base + f * delayed

    drainage_hourly = np.repeat(drainage_daily / 24 * 10 / 3.6, 24)   # mm/dag -> l/s/ha
    h, pumped = water_level_series(drainage_hourly, state, inflow_m3_per_sec)
    return SimulationResult(dh_max_m=float(h.max()), water_level_m=h,
                            pumped_m3_per_sec=pumped, drainage_l_s_ha=drainage_hourly)
```

De reeks wordt met `days_to_retain` dagen verlengd zodat de vertraagde staart erin past.

**Prestatiebudget.** `simulate()` < 1 ms; een inverse aanroep < 10 ms. Huidige situatie:
0,86 s (bergen, afvoeren) en 1,47 s (vasthouden).

### 3.4 Modellen

**Toestand.**

```python
class PolderState(BaseModel):  # niet EngineerBaseModel: dat voegt `language` toe
    area_ha: float
    pct_open_water: float
    pump_capacity_m3_per_sec: float
    retention_fraction: float = 0.0        # fractie van het LANDoppervlak
    days_to_retain: int = 2                # ontwerpconstante van de polder

    @property
    def area_open_water_ha(self) -> float: ...
    @property
    def area_land_ha(self) -> float: ...    # area_ha - area_open_water_ha
```

Vier ontwerpbesluiten:

| besluit | reden |
|---|---|
| `retention_fraction` is een fractie van het **land**, niet van het totaal | dat is `O3` in het rekenblad (3860 ha); lost D4 op |
| `days_to_retain` hoort bij de toestand, niet bij de actie | anders is administratie per perceel nodig zodra er in twee stappen retentie wordt gebouwd met verschillende vertraging |
| Absoluut, niet relatief | maakt D3 en D4 onrepresenteerbaar, en "+50 %" is in een rollout niet stabiel |
| Eén canonieke eenheid per grootheid in de toestand | de multi-eenheid-comfort van `WaterSystemInput` blijft aan de toolgrens en wordt daar één keer omgezet via `to_state()` |

**Acties.**

```python
class Action(EngineerBaseModel):
    unit: ClassVar[str]
    cost_per_unit: float | None = None
    def apply(self, state: PolderState) -> PolderState: ...
    def at(self, magnitude: float) -> "Action": ...
    def upper_bound(self, state: PolderState) -> float: ...

class BergenAction(Action):      delta_open_water_ha: float
class AfvoerenAction(Action):    delta_pump_capacity_m3_per_sec: float
class VasthoudenAction(Action):  delta_retention_ha: float
```

| actie | bovengrens |
|---|---|
| bergen | `pct_open_water ≤ 100` |
| afvoeren | `max_pump_factor`, default 20× de huidige capaciteit; melden als hij geraakt wordt |
| vasthouden | `retention_fraction ≤ 1`, én het unimodale optimum (§3.5) |

**Uitvoer.** Elke tooluitvoer krijgt naast het bestaande `data`-dict en `description`:

```python
class SolveStatus(str, Enum):
    EXACT = "exact"
    NO_MEASURE_NEEDED = "no_measure_needed"
    INFEASIBLE = "infeasible"

class LimitReason(str, Enum):
    NONE = "none"
    MEASURE_OPTIMUM = "measure_optimum"
    PHYSICAL_UPPER_BOUND = "physical_upper_bound"
```

| veld | functie |
|---|---|
| `state_before`, `state_after` | uitvoertype = invoertype |
| `dh_reference_m` | waterstandstijging zonder maatregel |
| `dh_with_measure_m` | met maatregel |
| `dh_reduction_m` | het verschil, als eigen veld — lost D11 op |
| `feasible_dh_min_m`, `feasible_dh_max_m` | haalbaar bereik van deze maatregel |
| `status`, `limit_reason`, `best_achievable_dh_m` | lost D7 op; via `ModelRetry` kan de agent zich corrigeren |

### 3.5 Inverse en haalbaarheid

Gemeten vorm van de responscurves:

| maatregel | vorm | consequentie |
|---|---|---|
| bergen | monotoon dalend | bisectie; sluit per constructie |
| afvoeren | monotoon dalend | idem |
| vasthouden | unimodaal — dalend, dan stijgend; minimum bij 67 / 69 / 77 / 93 % afhankelijk van de bui | eerst het optimum lokaliseren, dan bisectie op de dalende tak |

De niet-monotonie van vasthouden staat ook in het rekenblad (minimum 1,46183 m bij 70 %,
daarna terug naar 1,51116 m bij 100 %) en is dus modelgedrag. De locatie schuift met de bui
mee en mag nooit een constante worden.

```python
def solve(state, storm, action, target_dh_m) -> SolveResult:
    dh_ref = simulate(state, storm).dh_max_m
    if dh_ref <= target_dh_m:
        return SolveResult(magnitude=0.0, status=NO_MEASURE_NEEDED, ...)

    hi = action.upper_bound(state)
    f = lambda m: simulate(action.at(m).apply(state), storm).dh_max_m

    m_best, dh_best = golden_section_min(f, 0.0, hi)
    if target_dh_m < dh_best:
        return SolveResult(magnitude=m_best, status=INFEASIBLE,
                           best_achievable_dh_m=dh_best,
                           limit_reason=MEASURE_OPTIMUM if m_best < hi else PHYSICAL_UPPER_BOUND,
                           ...)

    return SolveResult(magnitude=bisect(f, 0.0, m_best, target_dh_m), status=EXACT, ...)
```

Tolerantie 1·10⁻⁴ m op `dH`, met een harde iteratielimiet. Bij `INFEASIBLE` levert de tool
geen getal maar een uitleg met het optimum en een verwijzing naar de maatregelen die verder
komen.

---

## 4. Te herstellen defecten

| # | Defect | Locatie | Fix | Verificatie | WP |
|---|---|---|---|---|---|
| D1 | Neerslaginvoer wordt volledig genegeerd; T=10/100/1000 geven identiek 101,4 cm, en seizoen, regime, patroon, duur en `days_to_discharge` geven alle 1674 ha | `debug = True` in `store.py:166`, `retain.py:181`, `discharge.py:215` | vlag en CSV-inleesblokken verwijderen | gouden casus reproduceert het rekenblad zonder de CSV | WP2 |
| D2 | `length_event_hrs=192` crasht alle drie de tools; 9 van 27 geldige combinaties duur × `days_to_discharge` geven `IndexError` | `model_day_length=7` in `utils_discharge.py:74` | afleiden als `length_rainfall_days + days_to_discharge − 1` | volledige invoerruimte draait zonder exceptie | WP1 |
| D3 | Bergen rapporteert hectares 28,6× te groot: doel 1,0 m geeft 2809 ha in plaats van 98 ha extra open water | `prcA/100 * area_ha` in `store.py` | absolute toestand; conversie tegen `area_open_water_ha` | anker: doel 1,0 m → 98 ha extra (140 → 238 ha, 3,5 → 5,96 %) | WP4 |
| D4 | Vasthouden rapporteert hectares 3,6 % te groot | `prcA/100 * area_ha` in `retain.py` | conversie tegen `area_land_ha` | anker: 30 % → 1158 ha (= 0,30 × 3860) | WP4 |
| D5 | `days_to_retain_discharge` is alleen geldig bij de waarde 2; volumebehoud is 304 % bij dT=0, 152 % bij dT=1, 101,3 % bij dT=2, 27,6 % bij dT=10 | vast venster van 3 dagen met factor `1/(1+dT)` in `compute_drainage1_mtr` | `delay_daily` (§3.3) | massabalans = 100 % voor dT = 0 t/m 10 | WP3 |
| D6 | Massalek van 1,3 % ook bij dT=2, doordat `.loc[0:24]`, `.loc[24:48]`, … label-slicing is en dus inclusief; de blokken overlappen één rij | `compute_drainage1_mtr` | vervalt met D5 | zie D5 | WP3 |
| D7 | `np.interp` klemt stil buiten het haalbare bereik: doel 5,0 m geeft 0 ha zonder melding, `area_available_ha=8000` op 4000 ha wordt geaccepteerd, `−500 ha` geeft de referentiewaarde | alle zes de tools | bisectie met expliciet bereik en `status` (§3.5) | buiten het bereik komt `INFEASIBLE` met optimum, nooit een geklemd getal | WP5 |
| D8 | Negatieve neerslag bij zomer + 192 u; T=100 geeft −2,17 en −5,11 mm op dag 1 en 2 | `get_rainfall` in `utils_rainfall.py` | verlies clippen op nul en het restant doorschuiven tot de 20 mm op is | geen enkele geldige combinatie levert negatieve neerslag | WP1 |
| D9 | `percentage_open_water`-validator vuurt nooit: `ModelRetry(...)` zonder `raise`, en de `elif` is onbereikbaar na de `> 10`-tak. `percentage_open_water=-50` wordt geaccepteerd → −2000 ha open water | `base_rule_of_thumb.py` | `raise` toevoegen, takken herstructureren, ondergrens 0 afdwingen | negatieve en > 100 % invoer wordt afgewezen | WP1 |
| D10 | Nederlandse afvoertekst verwart toename en totaal: "met 58 % (474 m3/min) toenemen" — 474 is de nieuwe totaalcapaciteit, de toename is 174 | `discharge.py`, `description_nl` | de toename gebruiken | tekst-assertie | WP6 |
| D11 | Store en discharge noemen een stijging een verlaging; `dH_mtr [m]` is de maximale stijging mét maatregel | `store.py`, `discharge.py` | `dh_reduction_m` als eigen veld, teksten herschrijven | tekst-assertie | WP6 |
| D12 | `days_to_discharge`-validator staat `[2, 3, 4]` toe, `_get_discharge_curve` ondersteunt 2 t/m 10 | `base_rule_of_thumb.py`, `utils_discharge.py` | gelijktrekken op 2 t/m 10 | validator en implementatie dekken hetzelfde bereik | WP1 |
| D13 | Dode code en ruis: `get_retained_discharge` wordt nergens aangeroepen; `prcAlst`/`maxMtrLst` als moduleglobals in drie bestanden; een no-op zelftoekenning in `discharge.py`; `if language == "nl"` / `if == "en"` zonder `else` laat `description` ongebonden | diverse | verwijderen; taalkeuze via een dict | `grep -r prcA src/` leeg | WP6, WP7 |
| D14 | `tests/testing_tools.ipynb` gebruikt `discharge_capacity_m3_per_min=5` bij bergen en `m3_per_sec=5` bij de overige vier — een factor 60 | notebook | eenheden gelijktrekken, gouden casus als eerste cel | notebook doorgerekend | WP7 |
| D15 | `PLAN_INVERSE_TOOLS.md` beschrijft `hold`/`days_to_hold_discharge` en een algoritme dat anders is geïmplementeerd | repo-root | verwijderen; dit document vervangt het | bestand weg | WP7 |

---

## 5. Werkpakketten

Elk pakket laat de suite groen achter.

### WP0 — Vangnet

- Karakteriseringstest die het huidige gedrag van alle zes de tools vastlegt op een
  handvol invoeren, zodat elke gedragsverandering hierna zichtbaar en bedoeld is.
- Fixture voor de referentiecasus (§2.2).
- De drie sweeptabellen uit `TttE_v03.xlsx` extraheren naar `tests/data/`, zodat de suite
  niet van Excel en openpyxl afhangt.

**Klaar als:** de sweeptabellen als testdata in de repo staan en de karakteriseringstest
groen is.

### WP1 — Losse defecten, nog geen refactor

D2, D8, D9, D12, plus de `apply_summer_loss`-schakelaar uit V3.

**Klaar als:** alle geldige combinaties van seizoen × T × duur × patroon ×
`days_to_discharge` draaien zonder exceptie, en geen enkele combinatie levert negatieve
neerslag.

### WP2 — `debug = True` eruit

D1. `drainage.csv` blijft als testdata, met een `README` die vastlegt welke bui het is.

**Klaar als:** de drie curves het rekenblad reproduceren zonder de CSV, tolerantie
1·10⁻¹² m, en die tolerantie staat in de test.

### WP3 — Rekenkern

- `simulate.py`: `water_level_series`, `delay_daily`, `simulate` (§3.3).
- `utils_calculations.py` verwijderen; de drie `clcMax_*` gaan erin op. D5 en D6 vervallen.
- Cascade-interfaces vrijhouden (§8.2): `SimulationResult` bevat de `pumped`-reeks,
  `simulate()` accepteert een optionele `inflow_m3_per_sec`, en niets in de toollaag neemt
  aan dat er precies één polder is.

**Klaar als:** de regressietest uit WP2 groen is via de nieuwe kern, `simulate()` < 1 ms,
de massabalans van `delay_daily` 100 % is voor dT = 0 t/m 10, en
`sum(pumped)·3600 + berging == sum(aanvoer)·3600`.

### WP4 — Toestand en acties

- `PolderState`, de drie acties, `to_state()` op de toolgrens (§3.4). D3 en D4 opgelost.
- `prcA` verdwijnt uit de codebase.
- Vlag `land_area_follows_open_water`, default `False` zolang V1 open staat, zodat de
  gouden test het rekenblad exact blijft reproduceren én het meekrimpende landoppervlak
  testbaar is.
- `Action.cost_per_unit` per actietype, met drie verschillende eenheden (§8.1).

**Klaar als:** de hectare-ankers kloppen, `grep -r prcA src/` leeg is, en beide takken van
`land_area_follows_open_water` getest zijn.

### WP5 — Inverse en haalbaarheid

`solve.py` (§3.5). D7 opgelost.

**Klaar als:** `given_h → given_area → given_h` sluit binnen 1·10⁻³ m over het hele
haalbare bereik van alle drie de maatregelen; buiten dat bereik komt `INFEASIBLE` met een
optimum; bergen en afvoeren zijn aantoonbaar monotoon en vasthouden unimodaal; een inverse
aanroep < 10 ms.

### WP6 — Tools, modellen, teksten

- De zes tools worden dunne wrappers. D10, D11, D13.
- Uitvoermodellen uitbreiden (§3.4).
- Naamgeving gelijktrekken (`area_available_ha` → `delta_open_water_ha`) met
  `AliasChoices`, zodat de oude namen blijven werken.
- `RetentionOutput.description` heeft "Table relationships" als omschrijving — opruimen.

**Klaar als:** de MCP-schema's geldig zijn, de agent-tests groen, en geen tekst een
stijging een verlaging noemt.

### WP7 — Opruimen

D14, D15, en `get_retained_discharge` verwijderen als die na WP3 ongebruikt blijft.
`docs/demo.qmd` nalopen op verouderde uitkomsten.

**Klaar als:** `pixi run pre-commit` en `pixi run pytest` schoon zijn en de notebook
opnieuw is doorgerekend.

---

## 6. Teststrategie

| laag | inhoud | doel |
|---|---|---|
| Referentie | de drie sweeptabellen uit het rekenblad, tolerantie 1·10⁻¹² m | de enige externe waarheid; mag niet stil wegdrijven |
| Eigenschappen | massabalans van `delay_daily`; gevectoriseerd == recursief voor zowel waterstand als `pumped`-reeks; monotoon respectievelijk unimodaal per maatregel; rondje sluit over het hele bereik; nooit negatieve neerslag | dekt de defectklassen, niet de losse defecten |
| Invoerruimte | elke geldige combinatie van seizoen × T × duur × patroon × `days_to_discharge` × maatregel draait zonder exceptie | D2 was een geldige invoer die crashte |
| Prestatie | `simulate()` < 1 ms, inverse < 10 ms | de demo hangt erop |

**Ankerwaarden**, referentiecasus uit §2.2:

```
dh_referentie                                    1,70233 m
afvoerreeks per dag [mm]   6,44  17,95  27,25  32,30  25,86  14,35  5,05   som 129,20

bergen      3,75 % open water                    1,58884 m
            4,00 %                               1,48954 m
            6,25 %                               0,95331 m
            7,00 %                               0,85117 m
afvoeren    5,1 m3/s                             1,67148 m
            6,0 m3/s                             1,39376 m
            7,0 m3/s                             1,12160 m
            13,25 m3/s  (795 m3/min)             0,07284 m
vasthouden  10 %                                 1,66404 m
            30 %                                 1,58746 m   -> 1158 ha
            70 %  (optimum)                      1,46183 m
            100 %                                1,51116 m

hectare-ankers   30 % vasthouden = 1158 ha
                 bergen doel 1,0 m = 98 ha extra open water
```

---

## 7. Openstaande vragen

Vijf vragen aan Ton Botterhuis. Geen ervan blokkeert een werkpakket; voor elk staat het
vastgestelde interimgedrag erbij. V1 en V2 verschuiven de uitkomsten of hun labels en
worden daarom als eerste gesteld.

### V1 — verdwijnt het land dat in open water verandert? · **beantwoord en afgerond**

**Antwoord (Ton Botterhuis, augustus 2026).** De waterstandverandering is *de neerslag die
direct op het open water valt, plus het water dat op het landoppervlak tot afvoer komt*.
Land dat in open water verandert voert dus niet meer af, maar de neerslag die erop valt
verdwijnt niet. Tot 10 % open water blijft de fout acceptabel; bij 30 % is het een
interactie.

Dat legt twee ontbrekende termen bloot, niet één. Het rekenblad houdt het afvoerende
oppervlak vast, **en** de neerslag die direct op het open water valt ontbreekt volledig.

**Gemeten effect** op de referentiebui. De twee termen werken tegen elkaar in — krimpend
land verlaagt de stand, directe neerslag verhoogt hem — maar heffen elkaar niet op:

| % open water | rekenblad | + land krimpt | + directe neerslag | volledige balans |
|---|---|---|---|---|
| 3,5 % | 1,7023 m | 1,7023 m | 1,8058 m | **1,8058 m** (+10,3 cm) |
| 7 % | 0,8512 m | 0,7923 m | 0,9546 m | 0,8957 m |
| 30 % | 0,1986 m | 0,0972 m | 0,3125 m | 0,2054 m |

Netto wordt bergen dus **minder** effectief, niet meer: het doel 0,10 m gaat van 2243 ha
naar 2837 ha extra open water. En de ontbrekende term is al bij 3,5 % open water 10 cm
waard, dus hij is niet pas bij 30 % relevant.

> **Correctie op een eerdere versie van dit document.** Hier stond dat het rekenblad voor
> dH = 0,10 m 19860 ha extra open water vraagt en dat het meerekenen van krimpend land dat
> terugbrengt naar circa 1060 ha, "een factor 19". Dat legde de hele kloof bij het
> landoppervlak en dat is onjuist. In het ongewijzigde model is dH exact omgekeerd
> proportioneel met het open water, en dan wordt 0,10 m al bij 2384 ha (59,6 %) gehaald.
> De 20000 ha in het rekenblad zit er een factor 8,4 naast omdat `x = schatting` de
> zoekmethode was. Het landoppervlak verklaart een factor 2 van de kloof, niet 19.

**Implementatie.** Eén samenhangende schakelaar `PolderState.water_balance` in plaats van
twee losse vlaggen, zodat de fysisch inconsistente combinatie niet bestaat:

- `POLDER` (default) — de balans zoals hierboven: krimpend land én directe neerslag.
- `SPREADSHEET` — reproduceert `TttE_v03.xlsx` exact, uitsluitend zodat de gouden
  regressietest kan blijven draaien.

De directe neerslag komt onvertraagd binnen: er is geen bodem om door te sijpelen. En
neerslag op open water verhoogt de stand met exact de neerslagdiepte, onafhankelijk van het
oppervlak — het volume is `P/1000 × A` en gedeeld door datzelfde `A` blijft `P/1000` m over.

**Gevolg dat hieruit voortkwam: bergen is niet langer monotoon.** Dichtbij 100 % open water
draait de curve om, want dan is er geen land meer dat de afvoer over meerdere dagen spreidt
en ontvangt het open water de neerslag ongedempt. Bergen is daarmee unimodaal, net als
vasthouden, en `solve` kon daar al mee om. Bij realistische percentages weegt de
bergingswinst zwaarder.

**Twee vervolgvragen, beide beantwoord (Ton Botterhuis, augustus 2026).**

*Geldt het neerslagverlies ook voor de neerslag die op het open water valt?* **Nee.** Het
verlies is een bodemproces — infiltratie in het freatisch pakket plus verdamping — en er
is geen bodem in een sloot. De afvoer van het land rekent dus met de gereduceerde
neerslag, de directe term met de volle. In de winter zijn die gelijk.

Het effect op de piek is kleiner dan de 20 mm suggereert, en dat is leerzaam: bij een
gemaal van 5 m³/s staat het peil aan het eind van dag 1 en 2 nog op nul, dus de extra
neerslag is weggepompt voordat de piek arriveert. Hij telt pas mee als de polder in die
eerste dagen al nat is — een zwakker gemaal of een extremer bui:

| zomerbui | gemaal | piek |
|---|---|---|
| T=10 | 5 m³/s | onveranderd |
| T=100 | 5 m³/s | onveranderd |
| T=1000 | 5 m³/s | +1,7 cm |
| T=100 | 1 m³/s | +1,7 cm |

Voor de massabalans maakt het altijd verschil, voor de gerapporteerde waterstand alleen
in die gevallen. Begrensd door 20 mm, dus maximaal 2 cm.

*Zit de directe neerslag al impliciet in de neerslag-afvoerrelatie van Tabel 39?* **Nee**,
en het antwoord hierboven laat dat zien. Dat het verlies wél voor land en níet voor open
water geldt, betekent dat het model de twee oppervlakken scheidt. En zodra je ze voor het
verlies scheidt, is Tabel 39 de relatie voor het land — anders zou de vraag of het verlies
op open water geldt niet te stellen zijn.

Een onafhankelijk argument uit de vorm van de curves: `[0,35 0,65]`, `[0,25 0,5 0,25]` en
`[0,25 0,25 0,25 0,25]` leggen het zwaartepunt op dag 2 of verdelen symmetrisch. Dat is het
profiel van een bodem- en drainagerespons. Een relatie die het open water zou meenemen
heeft een ongedempte dag-1-component nodig, en geen van de drie curves heeft die.

Wat als restpunt blijft staan, klein genoeg om te laten liggen: is Tabel 39 geijkt op
gemeten gebiedsafvoer van een echte polder, dan zat in die meting een paar procent
directe neerslag op water, en schrijft de relatie dat nu aan het land toe. Dat is een
bias van de orde van het open-waterpercentage van de ijkpolder, en hij schaalt niet mee
met het onze.

### V2 — is de "summer"-tabel de jaarrondstatistiek?

**Wat er nu gebeurt.** `_get_sum_summer_dict()` en `_get_sum_winter_dict()` bevatten twee
kolommen uit tabel 38. Het bijschrift noemt *"gedurende het gehele jaar en het
winterhalfjaar"* — er is geen zomerhalfjaarkolom. Het commentaar bij de regimefactoren
zegt het expliciet: *"voor de zomer gelden de factoren voor het gehele jaar"*.

| duur | T | "zomer" | winter |
|---|---|---|---|
| 48 u | 100 | 70,7 mm | 76,8 mm |
| 96 u | 100 | 86,6 mm | 100,4 mm |
| 192 u | 100 | 108,1 mm | 129,3 mm |

Een echte zomerstatistiek voor 8 dagen ligt ver onder de winterwaarde, want lange duren
worden door winter gedomineerd. 108,1 tegen 129,3 past bij een jaarrondstatistiek.

**Vraag.** Is de jaarrondkolom bedoeld als benadering van de zomer — verdedigbaar voor
korte duren, waar zomerse onweersbuien domineren — of bestaat er een zomerhalfjaarstatistiek
die gebruikt had moeten worden?

**Interim.** Intern hernoemen met een comment; de getallen blijven identiek. De demo-as mag
niet "zomerbui eens per 100 jaar" heten zolang dit niet bevestigd is.

### V3 — wordt het 20 mm neerslagverlies dubbel geteld?

**Wat er nu gebeurt.** `get_rainfall` pakt de tabelwaarde, verdeelt die met het patroon over
de dagen, en haalt er dan 20 mm af van de eerste twee dagen. Die 20 mm is gereconstrueerd
als `300 mm freatische berging × 0,04 bergingscoëfficiënt + 8 mm verdamping`.

Het bijschrift van tabel 38 luidt: *"bewerking van tabel 36 met in de zomer het
neerslagverlies van 20 mm en de reductiefactoren van tabel 6"*. Zit het verlies al in
tabel 38, dan wordt het twee keer afgehaald. De code verwijst echter naar bijlage E.3, die
het aftrekken voorschrijft.

**Vraag.** Rekent de werkwijze in E.3 vanaf tabel 36 (ruwe extremen, verlies moet er nog
af) of vanaf tabel 38 (verlies zit er al in)? Een derde mogelijkheid: de reconstructie via
`300 × 0,04 + 8` suggereert dat het verlies gebiedsafhankelijk moest worden — andere bodem,
andere grondwaterstand. Dan moet de 20 mm uit de tabel er eerst *bij*, en het
gebiedsspecifieke verlies eraf.

**Effect.** Zomer 96 u T=10 gaat van 59,0 naar 39,0 mm — een derde eraf. Bij dubbeltelling
zijn alle zomeruitkomsten systematisch te gunstig.

**Interim.** Schakelaar `apply_summer_loss`, default `True` (huidig gedrag), beide takken
getest.

### V4 — waar landt het verlies bij een 2-daags en een 8-daags patroon?

**Wat er nu gebeurt.** De regel uit E.3: het verlies gaat van de eerste twee dagen af,
beide met hetzelfde percentage, en dat percentage is 20 mm gedeeld door de som van die
twee dagen. Die regel past bij het vierdaagse patroon, waar de piek op dag 2 valt.

| duur | verdeling over de dagen (p1c) | piek |
|---|---|---|
| 48 u | 58 / 42 % | dag 1 |
| 96 u | 9 / 48 / 37 / 6 % | dag 2 |
| 192 u | 3,5 / 8,3 / 7,6 / 36 / 26 / 8 / 6 / 4 % | dag 4 |

Bij 192 u dragen dag 1 en 2 samen 12 % van de bui. Zomer T=100, 192 u: dag 1 + 2 =
12,72 mm, waarvan 20 mm af moet → −2,17 en −5,11 mm. Bij 48 u T=1 zijn dag 1 en 2 de hele
bui (22,0 mm), waarvan 20 mm af gaat: er blijft 2,0 mm over.

**Vraag.** Is de "eerste twee dagen"-regel specifiek voor het vierdaagse patroon? Bij 2 en
8 dagen zijn er drie opties: eerste twee dagen met afkap op nul en het restant doorschuiven;
de twee natste dagen; of proportioneel over de hele bui.

**Interim.** Clippen op nul en doorschuiven tot de 20 mm op is — massacorrect, nooit
negatief, werkt bij elke duur (D8).

### V5 — de LL-correctiefactor voor de zomer

**Wat er nu gebeurt.**

```
winter : LL=0,82  L=0,90  R=1,00  H=1,08
zomer  : LL=1,00  L=0,92  R=1,00  H=1,09
```

De winterrij is monotoon van laag naar hoog. In de zomerrij ligt LL boven L en gelijk aan
de referentie R.

**Vraag.** Wat staat er in tabel 3 voor het gehele jaar bij regime LL? Als daar geen waarde
staat: is 1,00 de bedoelde default, of moet LL voor de zomer gelijk zijn aan L?

**Effect.** Alleen gebieden met regime LL.

**Interim.** Laten staan met een `TODO` en een verwijzing naar deze vraag.

---

## 8. Demo: robuustheidscurve

Kies een norm, zoek per terugkeertijd het goedkoopste maatregelpakket dat eronder blijft,
plot investering tegen terugkeertijd. De buitenste loop is een `solve()` per maatregel per
terugkeertijd plus een goedkoopste-combinatie-zoektocht; bij `simulate()` onder 1 ms is een
curve over dertien terugkeertijden een kwestie van tienden van seconden.

De bui is hier een **testas**, geen stochastische trekking. Er zit dus geen aanname over de
toekomst in.

### 8.1 Kosten — onderbouwd, en de aanname was fout

Drie maatregelen, drie prijzen. De eenheden zijn niet uitwisselbaar, ook niet tussen de
twee die "per ha" zijn: bij bergen wordt de grond gekocht, bij vasthouden het recht om hem
af en toe onder water te zetten. Daarom hoort `cost_per_unit` bij het actietype en niet in
één gedeelde prijslijst.

| maatregel | eenheidskosten | prijspeil | onderbouwing |
|---|---|---|---|
| **afvoeren** | € 31.000 – 34.000 per m³/min geïnstalleerd vermogen | 2024/25 | gemaal De Poel (Scheldestromen): € 9,1 mln voor 270 m³/min → € 33.700. Gemaal Galgenrak (Drents Overijsselse Delta): € 16,9 mln voor 550 m³/min → € 30.700 |
| **bergen** | € 120.000 – 230.000 per ha open water | 2024/25 | grondverwerving € 86.400/ha grasland tot € 106.700/ha bouwland (Kadaster/NVM, gemiddeld € 95.400 over 2025), plus grondwerk. Blauwe Poort (Laarbeek): € 3,4 mln voor 15 ha inclusief grond = € 227.000/ha, maar dat is kleinschalig |
| **vasthouden** | € 1.250 – 2.400 per ha land | ~2020 | peilgestuurde drainage: € 2.400/ha voor een volledig nieuw systeem, € 1.250/ha als het op bestaande drainage wordt aangesloten. Waterschapssubsidies dekken € 400 – 3.000/ha, wat de bandbreedte bevestigt |

Twee dingen om te weten bij deze getallen. De grondprijs is in beweging — het gemiddelde
steeg van € 85.300/ha in 2024 naar € 95.400 in 2025 en brak in het vierde kwartaal door de
€ 100.000 — en de regionale spreiding is enorm: Friesland € 64.100, Flevoland € 182.100. En
de bergen-onderbouwing is de dunste van de drie: één project van 15 ha, waar
schaalvoordelen nog niet gepakt zijn.

#### De gemaalprijs heeft twee leeswijzen, en dat is beslissend

Beide gemaalprojecten zijn **volledige vervangingen**. De Poel kocht 50 m³/min extra
capaciteit voor € 9,1 mln, Galgenrak 210 m³/min extra voor € 16,9 mln. Per eenheid
geïnstalleerd vermogen is dat opvallend consistent, maar per eenheid *extra* vermogen
respectievelijk € 182.000 en € 80.000 per m³/min. Afvoeren is dus een **trapkost**, geen
lineaire kost: je koopt een gemaal, niet een m³/min.

Dat maakt `cost_per_unit × magnitude` de verkeerde vorm voor `AfvoerenAction`. Voor de
robuustheidscurve is dat geen detail maar de uitkomst.

#### Wat het model zegt met deze prijzen

Referentiebui, stijging 181 cm zonder maatregelen, polder van 4000 ha:

| norm | bergen | afvoeren (alleen de toename) | afvoeren (heel gemaal) |
|---|---|---|---|
| 170 cm | € 1,2 mln | € 0,7 mln | € 10,3 mln |
| 150 cm | € 3,8 mln | € 1,9 mln | € 11,5 mln |
| 120 cm | € 9,4 mln | € 4,0 mln | € 13,6 mln |
| **100 cm** | **€ 15,0 mln** | € 5,6 mln | **€ 15,2 mln** |
| 60 cm | € 37,1 mln | € 9,2 mln | € 18,8 mln |
| 30 cm | € 90,6 mln | € 12,3 mln | € 21,9 mln |

**Hier zit het knikpunt, en het is een ander dan aangenomen.** Reken je een gemaal als
trapkost, dan snijden bergen en afvoeren elkaar bij ongeveer 100 cm: voor bescheiden
ambities is bergen goedkoper omdat je geen heel nieuw gemaal hoeft te kopen, en daarboven
wint afvoeren omdat bergen kwadratisch duur wordt.

#### De aanname in de vorige versie was fout

Daar stond: *"is vasthouden goedkoop per ha, dan zet een kostenminimaliserende loop het
eerst in tot zijn optimum en nemen bergen en afvoeren het daarna over."* Dat klopt niet.
Vasthouden is per hectare vijftig tot honderd keer goedkoper dan bergen, maar het heeft
3314 ha nodig voor 26 cm. Diezelfde 26 cm kost:

| maatregel | maatvoering | investering |
|---|---|---|
| afvoeren | 0,8 m³/s | € 1,6 mln |
| bergen | 23 ha | € 3,1 mln |
| **vasthouden** | **3314 ha** | **€ 8,0 mln** |

Vasthouden is dus de **duurste** manier om die eerste 26 cm te kopen, ondanks de laagste
prijs per hectare. Goedkoop per eenheid is niet goedkoop per centimeter, en dat is precies
het soort omkering waarvoor je een model nodig hebt in plaats van een vuistregel over
eenheidsprijzen.

#### Wat er buiten deze getallen valt

Alleen investeringskosten. Vier dingen die de rangorde kunnen kantelen en die bewust niet
zijn meegenomen:

- **Energie en onderhoud.** Een gemaal kost per jaar geld, een hectare open water niet.
  Over een levensduur van dertig jaar drukt dat afvoeren omhoog.
- **Grond is een bezit.** De € 95.000/ha die je voor bergen betaalt is grotendeels
  vermogen dat je terugziet; een pomp schrijft af naar nul.
- **Vasthouden levert de grondgebruiker geld op.** Peilgestuurde drainage geeft
  € 100/ha/jaar bij maïs tot € 400 bij aardappelen en uien. De netto kosten voor het
  waterschap kunnen dus ver onder de investering liggen — bij bergen verdwijnt het
  landgebruik juist permanent.
- **Afvoeren schuift het probleem stroomafwaarts.** Wat dit gemaal wegpompt is de aanvoer
  van de volgende polder. Zolang de cascade niet in het model zit, ziet afvoeren er
  goedkoper uit dan het voor het systeem als geheel is. Zie §8.2.

Dat laatste is geen voetnoot: het is het argument waarom de robuustheidscurve per polder
een tussenstap is en niet het eindantwoord.

#### Bronnen

- [Kadaster, agrarische grondprijzen lange termijn](https://www.kadaster.nl/documents/d/kadaster.nl/themabericht-2025q4-lange-termijn-agrarische-grondprijs) en [NVM, agrarische grondprijs nadert € 100.000](https://www.nvm.nl/nieuws/2026/nvm-gemiddelde-agrarische-grondprijs-nadert-100000-per-hectare/)
- [Waterforum, aanneemkosten gemaal De Poel](https://www.waterforum.net/aanneemkosten-nieuwbouw-gemaal-de-poel-fors-hoger-dan-gepland/) en [Waterschap Scheldestromen, bouw gemaal De Poel](https://scheldestromen.nl/actueel/nieuws/waterschap-start-met-bouw-nieuw-gemaal-de-poel)
- [Infrasite, gemaal Galgenrak € 16,9 mln](https://www.infrasite.nl/waterbouw-deltas/2024/11/05/bouw-nieuw-gemaal-overijssel-kost-17-miljoen-euro/)
- [H2O Waternetwerk, Blauwe Poort Laarbeek](https://www.h2owaternetwerk.nl/h2o-actueel/blauwe-poort-in-laarbeek-zowel-waterberging-als-waterhouderij)
- [Waterschap Rivierenland, factsheet peilgestuurde drainage](https://www.waterschaprivierenland.nl/_flysystem/media/factsheet-4-drainage_def.pdf) en [STOWA Deltafact regelbare drainage](https://www.stowa.nl/deltafacts/zoetwatervoorziening/droogte/regelbare-drainage)
- [Deltares, tabellen aanleg- en beheerkosten](https://publicwiki.deltares.nl/display/AST/Tabellen+aanleg-+en+beheerkosten) — stedelijk georiënteerd (€ 225/m² voor extra wateroppervlak) en dus **niet** bruikbaar op polderschaal; hier vermeld zodat niemand die tabel per ongeluk toepast

### 8.2 Cascade van polders — voorbereid, niet gebouwd

Een polder staat in een cascade: wat A wegpompt is de aanvoer van B. Dat is niet
`pump_capacity`, want het gemaal draait alleen als er water is — precies de informatie die
de `max(..., 0)`-afkap weggooit. `water_level_series` (§3.3) levert daarom de werkelijke
`pumped`-reeks mee.

`PolderState` is dan een knoop en de cascade een gerichte graaf, met per knoop
`d_i[t] = (Q_eigen_i[t] + Q_in_i[t] − pump_i)·c`. Voor een keten is dat één doorloop in
topologische volgorde: geen iteratie, en de vectorisatie blijft intact.

**Bekende beperking.** Geen opstuwing. Staat de boezem hoog, dan kan het gemaal niet op
capaciteit draaien, en zonder dat effect ziet een bovenstroomse maatregel er beter uit dan
hij is. Opstuwing meenemen vereist een gekoppelde tijdstap over alle knopen, waarmee de
vectorisatie zijn nut verliest. De beperking wordt expliciet vermeld in de uitvoer.

De bouw komt na WP7. WP3 houdt de drie interfaces vrij zodat het uitbreiden is en geen
herbouw.

---

## 9. Compatibiliteit

| onderdeel | verandert |
|---|---|
| zes functienamen en modulepaden | nee |
| zes MCP-endpoints en FastAPI-routes | nee |
| modelnamen in `models/__init__.py` | nee |
| invoervelden | nee — alleen aanvullingen en aliassen |
| uitvoervelden | aanvullingen, plus één betekeniscorrectie |
| `utils_calculations.py` | verdwijnt (intern) |

Eén release note, met D3 als kop: eerder uit de bergen-tool verkregen hectares waren
28,6× te groot en moeten opnieuw worden gerekend.

---

## 10. Risico's

| risico | kans | mitigatie |
|---|---|---|
| Het rekenblad en de kern lopen uiteen op een casus die niet getest is | laag | WP0 legt drie volledige sweeps vast, geen losse punten |
| D3 verandert eerder gecommuniceerde getallen | zeker | expliciete release note; bugfix, geen regressie |
| V1 blijkt "land moet meekrimpen" en alle bergen-uitkomsten schuiven tot 10 cm | midden | vlag in WP4 maakt het een configuratiewijziging; beide takken getest |
| V3 blijkt een dubbeltelling en alle zomergetallen schuiven | midden | schakelaar in WP1 maakt het een configuratiewijziging |
| Vasthouden blijkt niet unimodaal op een bui die niet getest is | midden | gulden snede valt terug op een grofmazige scan met een assertie; de test dekt alle patronen |
| De cascade blijkt nodig vóór de demo | laag | WP3 levert de `pumped`-reeks en een `inflow`-ingang: uitbreiden, niet herbouwen |
| Scope kruipt naar de demo voordat de tools kloppen | reëel | WP0 t/m WP7 eerst |

---

## 11. Definition of done

- [ ] `pixi run pytest` groen; `pixi run pre-commit` schoon
- [ ] De drie sweeptabellen gereproduceerd zonder `drainage.csv`, tolerantie 1·10⁻¹² m
- [ ] Geen geldige invoercombinatie crasht; negatieve neerslag is onmogelijk
- [ ] `grep -r prcA src/` en `grep -rn "debug = True" src/` leeg
- [ ] Rondje sluit over het hele haalbare bereik van alle drie de maatregelen
- [ ] Buiten het bereik komt `INFEASIBLE` met optimum en uitleg, nooit een geklemd getal
- [ ] `simulate()` < 1 ms, inverse < 10 ms, gemeten in de suite
- [ ] `simulate()` levert de `pumped`-reeks; massabalans sluit (aanvoer = gepompt + berging)
- [ ] Massabalans van `delay_daily` is 100 % voor dT = 0 t/m 10
- [ ] Hectare-ankers kloppen: 30 % vasthouden = 1158 ha; bergen 1,0 m = 98 ha extra
- [ ] Beide takken van `land_area_follows_open_water` getest
- [ ] `testing_tools.ipynb` doorgerekend, eenheden consistent, gouden casus als eerste cel
- [ ] `PLAN_INVERSE_TOOLS.md` verwijderd

---

## 12. Gevolgen voor de talk

Verwerkt in `deltares_software_days_presentation.md` (versie 21 aug 2026):

| § | wijziging | status |
|---|---|---|
| kop | Werktitel en inzenders (Ton en Mattijn) vastgelegd | ✅ |
| §4 | Score wordt een voor/na-tabel; slide 10 toont alleen de linkerkolom, anders vervalt de spanning die slide 11 en 12 oplossen | ✅ |
| §5 | Prijslijst drie posten in plaats van twee; zaagtand vervangen door het omslagpunt tussen de maatregelen | ✅ |
| §8 | Slide 12 toont de robuustheidscurve | ✅ |
| §9 | Demo deel 2 herschreven; gemeten runtimes toegevoegd; het optimum van vasthouden als resultaat | ✅ |
| §10b | De waarschuwing over `compute_drainage1_mtr` is opgelost en omgezet in het sterkste stuk van de talk | ✅ |
| §11 | Besloten en openstaand gescheiden; de vijf vragen aan Ton opgenomen | ✅ |

Nog te besluiten door Mattijn en Ton: of de gevonden fouten (met name de debugvlag) als
één regel op slide 11 komen als illustratie van auditeerbaarheid. Zie §11 van het
presentatiedocument.
