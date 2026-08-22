# Bouwdocument — WP8, WP9, WP10

Versie 1 · 22 augustus 2026

Uitvoeringsdocument bij [`PLAN_UITWISSELING_EN_NETWERK.md`](PLAN_UITWISSELING_EN_NETWERK.md).
Dat document zegt *waarom*; dit document zegt *wat*, in welke volgorde, en waaraan je ziet
dat het klaar is. Alle getallen hierin zijn op 22 augustus 2026 nagerekend tegen de
codebase; §7 is de complete ankertabel.

**Doel:** dit in één sessie kunnen uitvoeren zonder terug te hoeven naar het ontwerp. Elke
keuze die tijdens het bouwen zou opkomen staat in §2 al beslist, met de reden erbij.

---

## 0. Protocol

### De volgorde is niet vrij

```
Fase 1 (WP8)  de tweezijdige kern          — raakt de rekenkern, niet de toolgrens
Fase 2 (WP9)  verbinding en uitwisseling   — raakt de toolgrens, heeft fase 1 nodig
Fase 3 (WP10) het netwerk                 — additief, heeft fase 2 nodig
```

Na elke fase is de suite groen en is de fase een eigen PR. Stoppen na fase 1 of 2 is een
geldige uitkomst; beginnen aan fase 3 zonder fase 2 is dat niet, want `Connection` is de
knoop.

### Vijf invarianten. Als een hiervan breekt: stoppen, niet repareren

| # | invariant | hoe je het ziet |
|---|---|---|
| I1 | De gouden regressie tegen `TttE_v03.xlsx` blijft op 1·10⁻¹² m | `tests/src/tools/test_reference_ton.py` groen, tolerantie ongewijzigd |
| I2 | `dh_max` van de referentiecasus is `1.8057576857142845` | staat in §7; wijkt hij af, dan is de balans veranderd |
| I3 | De zes bestaande functienamen, modulepaden, MCP-endpoints en FastAPI-routes blijven bestaan | `test_tools_router.py`, `test_mcp_schema.py` |
| I4 | Bestaande invoervelden blijven werken; alleen aanvullingen en aliassen | `test_characterisation.py` |
| I5 | `simulate()` blijft onder 1 ms en een inverse onder 10 ms | de prestatietests in de suite |

I1 en I2 zijn de belangrijkste. Fase 1 en fase 2 zijn **generalisaties**: het bestaande
geval moet er als bijzonder geval exact in zitten. Verschuift er een getal, dan is het geen
generalisatie geworden maar een wijziging, en dan is de aanname in §2 fout in plaats van de
implementatie.

### Basislijn, vastgesteld voor aanvang

```bash
.pixi/envs/default/bin/python -m pytest -q
```

```
245 passed, 2 warnings in 8.70s
```

En de ankers uit §7, die als script in de repo staan zodat ze niet op hun woord geloofd
hoeven te worden:

```bash
.pixi/envs/default/bin/python scripts/verify_wp8_anchors.py
```

Exitcode 0 betekent dat elk anker in §7 nog staat waar het staat. Draai dit **eerst**, en
na elke fase opnieuw. Het script bevat `clamped_scan` en `slack_of` in hun kortste vorm; de
implementatie in `simulate.py` moet ze reproduceren en er niet van afwijken.

De twee warnings zijn bestaand en verwacht (`percentage_open_water > 10` in twee tests).
Wordt het er één meer, dan is dat een nieuwe waarschuwing en die hoort onderzocht.

### Werkwijze per fase

1. Branch `feat/<dutch-kebab-case>` vanaf `main`.
2. Bouwen in de volgorde van de fase-secties: eerst de kern, dan de modellen, dan de tools,
   dan de teksten, dan de tests.
3. `.pixi/envs/default/bin/python -m pytest -q` na elke stap, niet alleen aan het eind.
4. `.pixi/envs/default/bin/pre-commit run --all-files` voor de commit.
5. Conventionele commit in het Nederlands, zoals de historie: `feat:`, `fix:`,
   `refactor!:` bij een breuk.
6. PR met `gh pr create`; de PR-beschrijving noemt de gewijzigde ankers uit §7.

---

## 1. Wat de wijzigingsoppervlakte werkelijk is

Nagegaan met `grep`, zodat er tijdens het bouwen geen verrassingen zijn.

**`water_level_series`** — 3 plaatsen in `src`, 3 testbestanden:

| plaats | rol |
|---|---|
| `tools/toolset_rules_of_thumb/simulate.py:35` | de definitie |
| `simulate.py:97` (`max_water_level`) en `:311` (`simulate`) | de twee aanroepers |
| `tests/src/tools/test_reference_ton.py:95` | reconstrueert de rekenbladbalans; **hier mag niets aan uitkomen veranderen** |
| `tests/src/tools/test_kern_properties.py:80, :507` | eigenschapstests |

**`pump_capacity_m3_per_sec`** — 21 plaatsen, waarvan 12 in `src`:

| bestand | aantal | aard |
|---|---|---|
| `models/.../state.py` | 2 | de velddefinitie en `from_water_system_input` |
| `models/.../actions.py` | 7 | `AfvoerenAction` in zijn geheel |
| `tools/.../simulate.py` | 5 | parameternaam, niet de toestand |
| `tools/.../discharge.py` | 3 | één echte uitlezing (`:54`), rest docstring |
| tests | 9 | assertions op `state_after` |

**Twee plekken die de zes-tool-oppervlakte hard vastleggen** en die fase 2 moet bijwerken:

- `tests/src/router/test_mcp_schema.py:25` — `TOOL_INPUT_MODELS`, de dict waar alle
  schema-tests over parametriseren.
- `tests/src/router/test_tools_router.py:46` — `test_all_six_routes_are_mounted`; die naam
  wordt onwaar en moet mee veranderen.

Verder: `tools/.../descriptions.py` heeft drie dicts (`_OTHER_MEASURES`,
`_OTHER_MEASURES_EN`, `_MEASURE_EN`) die per maatregel een sleutel nodig hebben. Een
nieuwe maatregel zonder sleutel geeft een `KeyError` in de tekstlaag, niet in de rekenlaag —
dus dat valt pas in een tooltest op.

---

## 2. Besluiten die al genomen zijn

Hier niet opnieuw over nadenken tijdens het bouwen. Elk besluit heeft een reden en, waar
relevant, een geverifieerd getal.

### B1 — Eén primitief: `clamped_scan`, en `slack` levert alle uitlezingen

De recursie `h[t] = clamp(h[t-1] + d[t], lo, hi)` is een associative scan over geklemde
translaties `(a, l, u)` met

```
combine((a1,l1,u1), (a2,l2,u2)) = (a1+a2,
                                   clamp(l1+a2, l2, u2),
                                   clamp(u1+a2, l2, u2))
```

En dan is er **één** afgeleide grootheid nodig:

```
slack[t] = h[t] - (h[t-1] + d[t])      # > 0 : de ondergrens vulde aan
                                        # < 0 : de bovengrens voerde af
```

Daaruit volgt alles, met alleen een teken en een schaalfactor `c = 3600 / A_openwater_m2`:

| uitlezing | uit `slack` |
|---|---|
| werkelijk weggepompt debiet (natte kant) | `capacity_out - slack/c` |
| onbenutte gemaalcapaciteit | `slack/c` |
| werkelijk aangevoerd debiet (droge kant) | `capacity_in + slack/c` |
| onvervulde vraag, oftewel tekort | `slack` waar `h` op de ondergrens zit, maal `A/1000` in mm |

**Geverifieerd:** `capacity_out − slack/c` reproduceert de bestaande
`pumped_m3_per_sec` op **1,7·10⁻¹³ m³/s**, en de massabalans sluit op **5,6·10⁻⁹ m³** van
5.168.000 m³ (relatief 1·10⁻¹⁵). `slack > 0` komt alleen voor waar `h == 0`.

Daarmee vervalt de aparte `unused_capacity`-boekhouding in `water_level_series`. Dat is
minder code, niet meer.

> **Wijziging ten opzichte van het ontwerpdocument §4.2.** Daar staat de scan als de
> vervanger van de cumsum-truc en de `pumped`-reeks als een tweede retourwaarde. Het is
> netter: één scan, één `slack`, en `pumped` is een afgeleide. Het ontwerpdocument is
> hierop niet fout, alleen minder scherp.

### B2 — De peilband is twee velden, geen veld met een teken

| veld | betekenis | klemt | eenheid |
|---|---|---|---|
| `target_level_rise_m` | het streefpeil staat hoger dan het oorspronkelijke peil | verschuift het nulpunt | m, ≥ 0 |
| `level_margin_m` | hoe diep onder het streefpeil het systeem mag zakken | `lo = −level_margin_m` | m, ≥ 0 |

Ze zijn **niet** hetzelfde met een teken, en dat is een correctie op een eerdere lezing.
Peilverlaging is lineair en onbegrensd: elke centimeter lager streefpeil is een centimeter
marge tot de inundatienorm. Voorbemaling binnen de marge **verzadigt**: op de referentiebui
levert 10 cm marge 10,00 cm winst en levert 30 cm marge nog steeds 10,51 cm, want het
gemaal maalt 0,3086 m/dag en de droge uren vóór de piek zijn op.

Twee grootheden, twee prijzen, twee vormen. Ze vormen samen de band `[−margin, +rise]` rond
het oorspronkelijke peil.

### B3 — `level_margin_m` default 0,0, en verplicht op de aanvoertools

Default 0,0 reproduceert het huidige gedrag exact (I2). Voor de aanvoertools is 0,0
degeneratief — zonder buffer is elke niet-gedekte vraag direct een tekort — dus daar is het
veld **verplicht**, precies zoals `delta_h_available` verplicht is op de natte tools omdat
het gebiedsspecifiek is. Op de zes bestaande tools blijft het optioneel met een
`ASSUMPTION_NOTES`-regel.

### B4 — De droogtevraag omzeilt de neerslag-afvoerrelatie

Tabel 39 beschrijft hoe neerslag tot *afvoer* komt. Een tekort is geen negatieve afvoer maar
een *vraag* — capillaire opstijging, gewasverdamping, wegzijging — en die komt onvertraagd
uit het oppervlaktewater. Dus: `days_to_discharge` en `retention_fraction` doen niets op de
droge kant, en de tekortreeks gaat rechtstreeks in de balans.

Dat is precies de asymmetrie uit ontwerpdocument §2: dezelfde transitie, een andere exogene
route ernaartoe.

### B5 — De droogteforcering is expliciet, geen statistiek

`Deficit(deficit_mm_per_day, length_days)`, twee getallen. **Niet** de KNMI-neerslagtekort­
statistiek, want V7 staat open en een verkeerd gekozen statistiek is erger dan een expliciet
getal. De twee termen zijn de exacte spiegel van de natte kant:

```
landvraag        = deficit_mm_per_day/1000 * area_land_ha*1e4 / 86400     [m3/s]
open-watervraag  = deficit_mm_per_day/1000 / 24                          [m/uur, direct]
```

### B6 — De toestand heeft twee capaciteiten, de actie één richting

```python
class Connection(BaseModel):
    to: str = "OUTSIDE"
    capacity_out_m3_per_sec: float = 0.0     # gemaal
    capacity_in_m3_per_sec: float = 0.0      # inlaat
    head_max_m: float | None = None          # None = peilonafhankelijk

class WaterExchangeAction(Action):
    direction: Literal["out", "in"]
    delta_m3_per_sec: float = Field(..., ge=0.0)
```

Waarom niet één signed capaciteit: een gemaal en een inlaat zijn twee kunstwerken met twee
prijzen die beide kunnen bestaan. Zie ontwerpdocument §5.1.

`AfvoerenAction` blijft bestaan als dunne subklasse van `WaterExchangeAction` met
`direction="out"`, zodat de negen testassertions en de tool niets merken.

### B7 — `OUTSIDE` is een echte knoop

Oneindige berging, vast peil. Wat erin gaat verdwijnt, wat eruit komt is er altijd. Dat maakt
de huidige eenpolder-casus de graaf met één polder plus één randvoorwaardeknoop, en dus geen
bijzonder geval in de code.

### B8 — Vectorisatie zit in de breedte, passes in de diepte

Knopen op dezelfde topologische diepte worden in één scan gedaan; het aantal sequentiële
passes is de **diepte** van de graaf, niet het aantal knopen. Voor Nederland is die diepte 3
à 4 (peilvak → polderboezem → boezem → zee) tegen een breedte van duizenden.

**Geverifieerd:** 8500 polders plus één boezem, diepte 2, 168 uur, tweezijdige scan in
numpy: **77,7 ms**. Met 1000 polders 6,6 ms.

### B9 — Geen JAX in deze bouw

`clamped_scan` wordt geschreven in de numpy-deelverzameling die JAX één-op-één ondersteunt
(zie ontwerpdocument §7), en er komt een test die dat afdwingt. Maar `jax` komt niet in
`pixi.toml`. WP11 beslist dat.

---

## 3. Fase 1 — WP8: de tweezijdige kern

Branch: `feat/tweezijdige-waterbalans`

### 3.1 `tools/toolset_rules_of_thumb/simulate.py`

**Nieuw: `clamped_scan(delta, lo, hi, h0=0.0)`**

```python
def clamped_scan(delta, lo, hi, h0=0.0):
    """Los h[t] = clamp(h[t-1] + delta[t], lo, hi) op als associative scan.

    Geklemde translaties `f(x) = clamp(x + a, l, u)` zijn gesloten onder compositie, dus
    de recursie is een prefix-scan met log-diepte in plaats van een lus. De cumsum-truc
    die hier eerder stond is het bijzondere geval lo=0, hi=+inf; deze vorm doet ook de
    gespiegelde klem die de droogtekant nodig heeft, en de tweezijdige band van een
    peilbeheer met marge.

    `lo` en `hi` mogen scalair of per tijdstap zijn. De laatste as is de tijd, zodat er
    een knoop-as voor kan staan.
    """
```

Implementatie: verdubbelende `step` over de laatste as, drie arrays `A`, `L`, `U`. Geen
python-lus over de tijd (B9). `lo <= hi` valideren.

**Nieuw: `slack_of(levels, delta, h0=0.0)`** — B1, drie regels.

**Gewijzigd: `water_level_series(...)`** — zelfde signatuur, plus `level_margin_m: float = 0.0`.
Retourneert onveranderd `(water_level_m, pumped_m3_per_sec)`, nu afgeleid via `clamped_scan`
en `slack_of`. De docstring die de cumsum-truc uitlegt wordt vervangen door de scan-uitleg;
de alinea over `Q[t-1]` versus `Q[t]` in het rekenblad blijft staan.

**Gewijzigd: `SimulationResult`** — drie velden erbij:

| veld | betekenis |
|---|---|
| `slack_m` | de reeks uit B1; alle andere uitlezingen zijn hiervan afgeleid |
| `level_margin_m` | de gebruikte marge, zodat de uitvoer zelfstandig leesbaar is |
| `dh_min_m` | de laagste stand; ≤ 0, en 0 zolang `level_margin_m == 0` |

`pumped_m3_per_sec` blijft als property bestaan, nu afgeleid uit `slack_m`.

**Gewijzigd: `simulate(...)`** — geeft `state.level_margin_m` door als `lo = -level_margin_m`.

### 3.2 `models/modelset_rules_of_thumb/state.py`

Veld `level_margin_m: float = Field(0.0, ge=0.0, description=...)`. De docstring legt B2
vast: dit is de onderkant van de band, `target_level_rise_m` de bovenkant, en ze zijn niet
uitwisselbaar.

### 3.3 `models/modelset_rules_of_thumb/actions.py`

**Nieuw: `PeilmargeAction(delta_level_margin_m)`**, met `upper_bound` = een fysieke
bovengrens op de bruikbare slootdiepte; default 1,0 m en melden als hij geraakt wordt.

`unit_cost = None` — voorbemaling is een bedrijfsvoeringsafspraak en geen investering, en
een verzonnen prijs is erger dan geen prijs. `cost` geeft dan `None`, wat het bestaande
model al ondersteunt.

### 3.4 `models/modelset_rules_of_thumb/results.py`

`OptimumKind.SATURATED` naast `PLATEAU`. Het verschil in de beschrijving:

| waarde | betekenis voor de lezer |
|---|---|
| `PLATEAU` | meer maatvoering verandert niets meer; verspilling, niet schadelijk |
| `SATURATED` | meer *afspraak* verandert niets meer, want een andere grootheid is de klem — bij voorbemaling de leegmaalsnelheid van het gemaal |

### 3.5 `tools/toolset_rules_of_thumb/solve.py`

`classify_optimum` krijgt de `SATURATED`-tak. De bestaande logica blijft: `UPPER_BOUND` als
het optimum op de grens ligt, `INTERIOR` als het voorbij het optimum slechter wordt. Nieuw:
`SATURATED` als de curve vlak wordt terwijl de bovengrens niet is bereikt **en** de
maatvoering niet de bindende grootheid is. Praktisch onderscheid met `PLATEAU`: bij een
plateau is de responswaarde de fysieke ondergrens van de maatregel, bij verzadiging niet.

### 3.6 Tests — `tests/src/tools/test_kern_properties.py`

| test | assertie |
|---|---|
| `test_clamped_scan_reproduces_the_recursion` | scan == sequentiële lus, over de vijf `(lo, hi)`-paren uit §7.C, tolerantie 1e-12 |
| `test_clamped_scan_is_the_generalisation_of_the_cumsum_trick` | `lo=0, hi=inf` == `water_level_series` over de 216 combinaties uit §7.B, tolerantie 1e-12 |
| `test_slack_reproduces_the_pumped_series` | B1, tolerantie 1e-12 |
| `test_slack_is_only_nonzero_at_a_clamp` | `slack != 0` impliceert `h == lo` of `h == hi` |
| `test_the_mass_balance_closes_with_slack` | aanvoer == weggepompt + eindberging, relatief 1e-12 |
| `test_prereleasing_saturates_at_the_pump_rate` | de sweep uit §7.D, met 10 cm → 10,00 cm en 30 cm → 10,51 cm |
| `test_the_level_margin_default_changes_nothing` | `level_margin_m=0` geeft exact I2 |
| `test_the_core_uses_only_the_portable_numpy_subset` | statische check op `simulate.py`: geen `.item()`, geen `float(` binnen de kern, geen `for` over de tijdas (B9) |

Die laatste is een AST-check, geen tekstgrep. Hij faalt luidruchtig zodra iemand een lus
terugzet, en dat is precies de regressie die WP11 duur maakt.

### 3.7 Klaar als

- [x] Suite groen, 245 + 30 nieuwe tests, warnings nog steeds 2
- [x] I1 t/m I5 gehouden
- [x] `grep -n "minimum.accumulate" src/` leeg — de truc is opgegaan in de scan
- [x] `simulate()` < 1 ms gemeten: 0,060 ms, en een inverse 4 tot 5 ms

---

## 4. Fase 2 — WP9: verbinding en uitwisseling

Branch: `feat/uitwisseling-in-twee-richtingen`

### 4.1 De verhuizing van `pump_capacity_m3_per_sec`

Nieuw bestand `models/modelset_rules_of_thumb/connection.py` met `Connection` (B6) en
`OUTSIDE` (B7).

`PolderState` krijgt `connections: tuple[Connection, ...]`. En — dit is de sleutel voor I4 —
`pump_capacity_m3_per_sec` blijft bestaan als **property**:

```python
@property
def pump_capacity_m3_per_sec(self) -> float:
    """De uitgaande capaciteit van de enige verbinding.

    Blijft bestaan omdat de toolgrens en negen tests hem gebruiken. Heeft de polder meer
    dan een UITGAANDE verbinding - twee gemalen naar twee bestemmingen, of aanvoer uit
    een ander systeem dan waar de afvoer naartoe gaat - dan heeft "de gemaalcapaciteit
    van deze polder" geen antwoord, en hoort de aanroeper de verbinding te noemen.
    Daarom raises hij dan.

    Let op wat hier GEEN twee verbindingen zijn. Een gemaal en een inlaat naar dezelfde
    buur zijn er een, want `Connection` draagt beide capaciteiten (B6). En polders die op
    dezelfde knoop lozen geven die knoop geen tweede verbinding: `connections` bevat
    alleen uitgaande kanten, en inkomende volgen uit `edge_to` (zie 5.1).
    """
```

Zo blijft de eenpolder-casus letterlijk werken en wordt de meerknoopcasus niet stil
verkeerd. Het is een vangrail op een dubbelzinnige *vraag*, geen beperking op de topologie:
fan-in en fan-out zijn onbeperkt.

> **Bijgesteld tijdens de bouw.** Een leesproperty is niet genoeg. Drie tests en
> `from_water_system_input` **construeren** `PolderState` met `pump_capacity_m3_per_sec=`
> als kwarg, en een property kan geen constructie aannemen. Er is dus ook een
> constructie-alias nodig: een `model_validator(mode="before")` die het losse getal in een
> `Connection` naar `OUTSIDE` omzet. Zonder die tak is het verhuizen van een veld naar een
> object een breuk in plaats van een generalisatie, en sneuvelt I4.
>
> En omdat `replace()` op `model_copy` rust en die de validators overslaat, kan een
> capaciteit niet meer als los veld worden bijgewerkt. Vandaar `with_capacity(...)`, dat
> `AfvoerenAction.apply` en `AanvoerenAction.apply` gebruiken.

`from_water_system_input` bouwt één `Connection(to=OUTSIDE, capacity_out=...)`.

### 4.2 Acties

`WaterExchangeAction` volgens B6. `AfvoerenAction` wordt:

```python
class AfvoerenAction(WaterExchangeAction):
    """Afvoeren: meer gemaalcapaciteit. Bestaat als eigen naam omdat de toolgrens,
    de kostenonderbouwing en de teksten hem zo kennen; de transitie is de generieke."""
    direction: Literal["out"] = "out"
```

met `delta_pump_capacity_m3_per_sec` als `AliasChoices` op `delta_m3_per_sec`. Nieuw:
`AanvoerenAction` met `direction="in"` en `unit_cost=None` — de prijs van aanvoer is in een
tekort geen investering maar een verdelingsvraag, en die staat als V8 open.

### 4.3 De droogtekant

`models/modelset_rules_of_thumb/deficit.py`: `DeficitInput` volgens B5, met
`length_days` in `FIELD_FALLBACKS` (30) en in `ASSUMPTION_NOTES`.

`simulate.py` krijgt `simulate_deficit(state, deficit)` — of `simulate` krijgt een
forcering-argument dat beide aankan. **Kies het eerste**: twee functienamen met één kern
eronder, want de exogene routes verschillen (B4) en een schakelaar in `simulate` zou die
twee routes in één functie mengen.

Uitlezingen op `SimulationResult`, alle afgeleid uit `slack_m`:

| veld | betekenis |
|---|---|
| `dh_min_m` | de diepste uitzakking, ≤ 0 |
| `days_until_buffer_empty` | wanneer `h` de ondergrens raakt; `inf` als dat niet gebeurt |
| `shortfall_mm` | onvervulde vraag over de polder |
| `supplied_mm` | wat de inlaat werkelijk heeft geleverd |

`shortfall_mm + supplied_mm + buffer` moet de totale vraag zijn; dat is de massabalanstest,
en hij sluit in §7.E op alle vier de rijen.

### 4.4 Twee nieuwe tools

`tools/toolset_rules_of_thumb/supply.py`, hetzelfde patroon als `discharge.py`:

| functie | vraag |
|---|---|
| `calculate_supply_given_h` | hoeveel inlaatcapaciteit houdt het peil boven de ondergrens? |
| `calculate_supply_given_supply` | wat doet deze inlaatcapaciteit met het peil en het tekort? |

De namen volgen het bestaande `given_x`-patroon, ook waar dat lelijk is: consistentie met
`calculate_discharge_given_discharge` weegt zwaarder dan schoonheid.

Registreren in: `tools/__init__.py`, `models/__init__.py`,
`routers/tools_router_RulesOfThumb.py` (met `@mcp.tool()`, `@router.post()`,
`@auto_docstring()`, `@as_tool_error` in díe volgorde), en de twee testplekken uit §1.

`descriptions.py`: sleutel `"aanvoeren"` in de drie dicts, `_MEASURE_EN["aanvoeren"] = "supply"`,
en `_magnitude_nl`/`_magnitude_en` een tak voor `unit == "m3/s inlaat"`. En twee nieuwe
tekstfuncties, want de droge kant vertelt een ander verhaal: niet "de stijging blijft onder
X" maar "het peil zakt Y cm en er blijft Z mm vraag onvervuld".

### 4.5 Statusonderscheid

`SolveStatus.INFEASIBLE` splitst in `ACTION_INFEASIBLE` en `PROBLEM_INFEASIBLE`
(ontwerpdocument §8). `INFEASIBLE` blijft bestaan als alias-waarde met een deprecatienoot in
de beschrijving, zodat bestaande uitvoer leesbaar blijft. Op één polder met één maatregel
vult `solve` altijd `ACTION_INFEASIBLE`; `PROBLEM_INFEASIBLE` is voor WP11 en wordt hier
alleen gedefinieerd.

### 4.6 De naad rechtzetten

`DischargeInputGivenDischarge.delta_discharge_capacity_l_s_ha` belooft in zijn beschrijving
dat negatieve waarden mogen; `calculate_discharge_given_discharge` weigert ze met een
`ModelRetry`. Rechttrekken door de belofte te schrappen en in de `ModelRetry` naar
`calculate_supply_given_supply` te wijzen: capaciteit die wégvalt is een kleinere
`capacity_out`, en water dat de andere kant op gaat is aanvoer. Twee verschillende vragen,
en nu bestaan er twee tools voor.

### 4.7 Tests

| bestand | test |
|---|---|
| `test_kern_properties.py` | `test_one_connection_to_outside_reproduces_the_scalar_capacity`; `test_pump_capacity_property_raises_on_multiple_connections` |
| `test_supply.py` (nieuw) | de vier rijen uit §7.E als ankers; massabalans; `given_h → given_supply → given_h` sluit |
| `test_characterisation.py` | ongewijzigd groen — dit is de I4-test |
| `test_mcp_schema.py` | `TOOL_INPUT_MODELS` uitgebreid; alle bestaande parametrische tests gelden dan ook voor de twee nieuwe |
| `test_tools_router.py` | `test_all_six_routes_are_mounted` → `test_all_eight_routes_are_mounted` |
| `test_uitlegbaarheid.py` | de aanvoerteksten noemen een uitzakking geen stijging — de D11-fout, nu gespiegeld |

### 4.8 Klaar als

- [x] Alle ankers uit §7.E kloppen, en de inverse geeft 0,4225 l/s/ha
- [x] I1 t/m I5 gehouden; `test_characterisation.py` ongewijzigd
- [x] Acht tools in het MCP-schema, elk binnen `MAX_DESCRIPTION_CHARS`
- [x] `grep -rn "pump_capacity_m3_per_sec" src/` levert alleen de property en aliassen

---

## 5. Fase 3 — WP10: het netwerk

Branch: `feat/netwerk-van-knopen`

Additief: één nieuw bestand plus tests. De toolgrens verandert **niet** — er komt geen
netwerktool in deze fase (dat is WP11, ontwerpdocument §8).

### 5.1 `models/modelset_rules_of_thumb/system.py`

`SystemState` als struct-of-arrays volgens ontwerpdocument §6.2, met:

```python
@classmethod
def from_polders(cls, polders: Sequence[PolderState]) -> "SystemState": ...
def to_polders(self) -> tuple[PolderState, ...]: ...
def topological_levels(self) -> tuple[np.ndarray, ...]: ...
```

`PolderState` blijft de leesbare projectie; `SystemState` is de rekenvorm. `topological_levels`
levert de knoopindices per diepte (B8) en gooit een `ValueError` bij een cyclus.

**De diepte is de langste pad-afstand tot een bron, niet de kortste.** Dat is geen detail.
Neem A → C, B → C, A → D, D → C. Met kortste-pad-diepte komt C op diepte 1 te staan, samen
met D — en dan wordt C gerekend terwijl zijn voorganger D nog niet klaar is. Met
langste-pad-diepte staat C op 2 en klopt de invariant die de hele pass-structuur draagt:

> elke voorganger van een knoop ligt op een strikt kleinere diepte

Nagerekend op precies dat diamantje: langste pad geeft `A=0, B=0, D=1, C=2` en de invariant
houdt; kortste pad geeft `C=1` en de invariant breekt.

**Fan-in is onbeperkt en is geen bijzonder geval.** `connections` is een adjacentielijst van
*uitgaande* kanten; inkomende kanten staan niet op de knoop maar volgen uit `edge_to`. Dat
A en B beide op C lozen betekent dus niet dat C meer dan één `Connection` heeft, en de
property uit §4.1 raakt het niet. Wat wél moet: de aanvoer van een knoop is de **som** over
alle kanten die erop uitkomen, dus een scatter-add en geen toewijzing:

```python
np.add.at(inflow, edge_to, exchange[edge_from])       # niet inflow[edge_to] = ...
```

Het prototype in ontwerpdocument §6.3 deed `inflow[1:] = pumped[:-1]`, en dat is een ketting.
Voor een graaf is dat fout zodra twee knopen op dezelfde knoop uitkomen: de tweede
toewijzing overschrijft de eerste in plaats van hem op te tellen.

### 5.2 `tools/toolset_rules_of_thumb/network.py`

```python
def simulate_network(system, storm, max_iterations=50) -> NetworkResult:
    """Reken een graaf van knopen door.

    Zonder kopafhankelijke capaciteit is een pass per topologische diepte exact. Met
    derating is het een vast-puntiteratie die begint bij vrije afstroming - de maximale
    uitstroom overal - en die daarna alleen kan verlagen. Monotoon dalend en begrensd door
    nul, dus convergent zonder stabiliteitsvoorwaarde.
    """
```

Harde eisen in de implementatie:

- assertie dat elke iteratie de uitstroom niet verhóógt; breekt die, dan is de
  koppelingswet niet monotoon en moet dat luidruchtig falen in plaats van door te rekenen;
- bij het raken van `max_iterations`: rapporteren, niet stil teruggeven — de tussenliggende
  iteraties zijn optimistisch over de afvoer en dus **onveilig** over de standen;
- `NetworkResult` levert de klem: vrije afstroming als ondergrens op de standen, volledig
  geblokkeerd als bovengrens. Is die klem smal genoeg, dan hoeft er niet geïtereerd te
  worden.

### 5.3 Tests — `test_network.py` (nieuw)

| test | assertie |
|---|---|
| `test_a_single_node_equals_the_polder_model` | één knoop plus `OUTSIDE` == `simulate`, tolerantie 1e-12 |
| `test_without_derating_one_pass_per_depth_is_exact` | keten van 4 == knoop-voor-knoop met doorgegeven uitwisseling, tolerantie 1e-12 |
| `test_derating_converges_monotonically` | de uitstroomreeks daalt monotoon; keten van 5 convergeert |
| `test_a_cycle_is_rejected` | `ValueError`, geen oneindige lus |
| `test_fan_in_sums_the_upstream_exchange` | A → C en B → C: de aanvoer van C is de som, niet de laatste; tolerantie 1e-12 |
| `test_depth_is_the_longest_path_not_the_shortest` | op A → C, B → C, A → D, D → C is de indeling `A=0, B=0, D=1, C=2`, en elke voorganger ligt strikt lager |
| `test_the_mass_balance_closes_over_the_network` | som van alle aanvoer == som van alle uitstroom naar `OUTSIDE` plus alle berging |
| `test_national_scale_stays_within_budget` | 8500 knopen + 1 boezem, diepte 2, 168 uur onder 100 ms (§7.G: 77,7 ms) |
| `test_the_clamp_brackets_the_iterated_answer` | de geconvergeerde standen liggen tussen vrije afstroming en volledig geblokkeerd |

### 5.4 Klaar als

- [ ] Eén knoop is bitgelijk aan `simulate` binnen 1e-12
- [ ] 8500 knopen onder 100 ms
- [ ] I1 t/m I5 gehouden; de toolgrens is niet aangeraakt

---

## 6. Wat er expliciet NIET in deze bouw zit

Dit is een scope-hek, geen achterstand. Bij twijfel tijdens het bouwen: dit hek geldt.

| onderwerp | waarom niet | waar wel |
|---|---|---|
| JAX als afhankelijkheid | B9; de kern wordt alleen *geschikt* gemaakt | WP11 |
| Gradiënten, adjoint, SLSQP | vraagt een backendbesluit | WP11 |
| De pakketzoektocht `optimize(...)` | vraagt de vier acties én de twee constraints | WP11 |
| Een netwerktool of MCP-resource | ontwerpdocument §8; de graaf komt de toolgrens niet over | WP11 |
| De verdringingsreeks als LP | ontwerpdocument §6.4 | na WP11 |
| KNMI-neerslagtekortstatistiek als exogene as | V7 open; B5 is de interim | na V7 |
| Verzilting en doorspoeling | V8 open; het is een randvoorwaarde, geen toestandsvariabele | na V8 |
| Een prijs voor peilopzet, peilmarge en aanvoer | drie keer een verdelingsvraag, geen investeringspost | na V8 |
| Echte waterschapstopologie | WP10 werkt op synthetische ketens en bomen | na WP10 |

---

## 7. Ankertabel

Alles hieronder is op 22 augustus 2026 nagerekend tegen de codebase op commit `5a77020`.
Referentiecasus tenzij anders vermeld: winter, T = 1000, 96 uur, p1a, `days_to_discharge=4`,
regime R, polder 4000 ha, 3,5 % open water (140 ha open water, 3860 ha land), gemaal 5 m³/s.

### A — invariant

| grootheid | waarde |
|---|---|
| `dh_max` productiebalans | `1.8057576857142845` m |
| `dh_max` rekenbladbalans (`REFERENCE_DH_M`) | `1.7023330857142858` m |
| suite | 245 passed, 2 warnings, 8,70 s |
| gemaal 5 m³/s op 140 ha | 0,3086 m/dag |

### B — `clamped_scan(lo=0, hi=+∞)` versus `water_level_series`

216 combinaties van seizoen × duur {48, 96, 192} × T {10, 100, 1000} × patroon
{p_0, p1a, p1c, p2b} × `days_to_discharge` {2, 3, 4}:

**grootste afwijking 6,661·10⁻¹⁵ m**

### C — tweezijdige scan versus de sequentiële lus

| `lo` | `hi` | afwijking |
|---|---|---|
| 0 | +∞ | 3,331·10⁻¹⁵ |
| −0,30 | +∞ | 3,109·10⁻¹⁵ |
| −∞ | 0 | 5,551·10⁻¹⁷ |
| −0,30 | 0 | 5,551·10⁻¹⁷ |
| −0,20 | +0,20 | 1,110·10⁻¹⁶ |

### D — voorbemaling verzadigt

| `level_margin_m` | piek boven streefpeil | winst |
|---|---|---|
| 0 cm | 180,5758 cm | — |
| 5 cm | 175,5758 cm | 5,0000 cm |
| 10 cm | 170,5758 cm | 10,0000 cm |
| 15 cm | 170,0628 cm | 10,5130 cm |
| 20 cm | 170,0628 cm | 10,5130 cm |
| 30 cm | 170,0628 cm | 10,5130 cm |
| 100 cm | 170,0628 cm | 10,5130 cm |

### E — droogte: tekort 4 mm/dag, 30 dagen, `level_margin_m = 0,30`

Vraag: land 1,7870 + open water 0,0648 = **1,8519 m³/s**, oftewel 0,4630 l/s/ha over de
polder. Totale vraag over 30 dagen: 120,0 mm.

| aanvoer | inlaat | laagste stand | buffer leeg na | tekort | aangevoerd |
|---|---|---|---|---|---|
| geen | 0,000 m³/s | −30,00 cm | 2,58 d | 109,50 mm | 0,0 mm |
| norm 0,3 l/s/ha | 1,200 m³/s | −30,00 cm | 7,42 d | 31,74 mm | 77,8 mm |
| norm 0,4 l/s/ha | 1,600 m³/s | −30,00 cm | 19,29 d | 5,82 mm | 103,7 mm |
| net dekkend | 1,852 m³/s | 0,00 cm | nooit | 0,00 mm | 120,0 mm |

Massabalans op de derde rij: 103,7 aangevoerd + 10,5 uit de buffer + 5,8 tekort = 120,0 mm.

De inverse hoort daar 0,4225 l/s/ha uit te komen, en niet 0,4630. De berging levert 10,5 mm
over 30 dagen, oftewel 0,35 van de 4 mm/dag, dus de inlaat hoeft maar 3,65 mm/dag te dekken.
Algemeen: `nodig = volle_vraag x (tekort - berging/duur) / tekort`. Bij 90 dagen is dat
0,4495 en bij 365 dagen 0,4597 - hij kruipt naar de volle vraag toe zonder er te komen,
want de berging koopt tijd en geen dekking. En de aanvoernorm van 0,4 l/s/ha zit op 95 % van
wat deze polder bij dit tekort over een maand nodig heeft.
De 10,5 mm buffer is `0,30 × 0,035 × 1000` — exact `retained_volume_mm` uit deel 1 §8.2.
Dat de droogte-uitlezing en de bufferomvang hetzelfde getal zijn, is de bevestiging dat het
ontwerp klopt.

Twee dingen om te weten bij deze tabel. De aanvoernorm van 0,4 l/s/ha dekt **86 %** van de
vraag van deze polder bij dit tekort, niet alles. En de bruikbaarste uitlezing is niet de mm
maar de dag: met de norm blijft de polder 19 van de 30 dagen boven de ondergrens.

### F — `slack` generaliseert `pumped`

| toets | uitkomst |
|---|---|
| `capacity_out − slack/c` versus `pumped_m3_per_sec` | 1,723·10⁻¹³ m³/s |
| massabalans aanvoer = gepompt + berging | 5.168.000 = 2.876.818,17 + 2.291.181,83; rest 5,6·10⁻⁹ m³ |
| `slack ≠ 0 ⟹ h` op een klem | waar |

### G — schaal

Indicatief — dit zijn de enige ankers die van de machine afhangen. De grens die telt is de
100 ms uit §5.3, en die zit er ruim boven.

| geval | tijd |
|---|---|
| 100 knopen × 168 uur, eenzijdig, cumsum | 0,15 ms |
| 1.000 knopen × 168 uur, eenzijdig, cumsum | 1,47 ms |
| 8.500 knopen × 168 uur, eenzijdig, cumsum | 11,6 ms (1,4 µs/knoop) |
| 100 knopen × 168 uur, tweezijdige scan | 0,6 ms |
| 1.000 knopen × 168 uur, tweezijdige scan | 6,7 ms |
| 8.500 knopen × 168 uur, tweezijdige scan | 67,4 ms (7,9 µs/knoop) |
| 8.500 polders + 1 boezem, diepte 2, met `slack` | 77,7 ms |
| keten van 5 met derating, tot convergentie | 2 passes, 0,057 ms |

De tweezijdige scan is ongeveer zes keer duurder per knoop dan de cumsum-truc — log-diepte
kost meer werk dan één cumsum. Dat is de prijs van de generalisatie, en op de schaal die
telt is hij betaalbaar.

### H — JAX, ter informatie (niet in deze bouw)

`jax.lax.associative_scan` op dezelfde monoïde, 240 tijdstappen, laptop-CPU:

| knopen | voorwaarts | gradiënt |
|---|---|---|
| 1.000 | 1,2 ms | 3,6 ms |
| 8.500 | 6,2 ms | 39 ms |
| 50.000 | 36 ms | 254 ms |

Float32 geeft 1·10⁻⁷ m afwijking tegen de sequentiële lus; de kern moet dus in float64
blijven voor de gouden test, en float32 hoort alleen bij de netwerkschaal met een eigen
tolerantie.

---

## 8. Faalscenario's

| symptoom | vermoedelijke oorzaak | wat te doen |
|---|---|---|
| I2 verschuift in fase 1 | `lo` of `hi` niet op 0 respectievelijk +∞ in het bestaande pad, of `slack` met het verkeerde teken | teken van `slack` controleren tegen §7.F; het is `capacity − slack/c`, niet `+` |
| Gouden test loopt van 1e-12 naar ~1e-8 | float32 binnengeslopen via een `np.float32`-literal | dtype forceren in `clamped_scan` |
| Fase 2 breekt negen testassertions op `state_after` | `pump_capacity_m3_per_sec` niet als property teruggezet | §4.1; de property is verplicht, geen luxe |
| `KeyError` in een tooltest, niet in de rekenlaag | een van de drie dicts in `descriptions.py` mist `"aanvoeren"` | §1 laatste alinea |
| MCP-descriptions over budget | de twee nieuwe tools hebben te lange docstrings | `MAX_DESCRIPTION_CHARS` is 1500; `test_the_description_stays_within_its_budget` |
| Netwerkiteratie convergeert niet | koppelingswet niet monotoon | niet de tolerantie verruimen; de assertie uit §5.2 is het echte antwoord |
| Fase 3 is bitgelijk maar traag | scan per knoop in plaats van per laag | B8: vectoriseer de breedte, niet de diepte |
| Fase 3 klopt op een ketting maar niet op een graaf, zonder foutmelding | de aanvoer wordt toegewezen in plaats van opgeteld, dus twee bovenstroomse polders overschrijven elkaar | §5.2: `np.add.at`, en `test_fan_in_sums_the_upstream_exchange` |
| Een knoop krijgt aanvoer van een voorganger die nog niet gerekend is | laagindeling op kortste in plaats van langste pad | §5.2; op een ketting valt dit niet op, op een diamant wel |

**Terugvalopties.** Fase 1 is één PR en volledig terug te draaien zonder fase 2 te raken.
Blijkt de tweezijdige vorm de gouden test niet te kunnen houden, dan is de terugval:
`clamped_scan` ernaast zetten in plaats van eronder, en `water_level_series` de cumsum-vorm
laten houden. Dat kost duplicatie en levert WP10 nog steeds op — maar dan is B1 fout, en dat
zou verrassend zijn gegeven §7.B en §7.F.

---

## 9. Documenten bijwerken na de bouw

| document | wat |
|---|---|
| `PLAN_UITWISSELING_EN_NETWERK.md` | WP8, WP9, WP10 afvinken; de ankers in §4 en §6 vervangen door de gemeten waarden als ze afwijken |
| `PLAN_TOOLS_REFACTOR.md` §8.2 | `retained_volume_mm` verwijst nu naar de buffer die §7.E gebruikt; die twee moeten hetzelfde getal noemen |
| `deltares_software_days_presentation.md` §9 | de maatregeltabel: vier vormen in plaats van drie, en de verzadiging van voorbemaling |
| `docs/demo.qmd` | nalopen op verouderde uitkomsten, zoals WP7 ook deed |
| release note | `pump_capacity_m3_per_sec` is een property geworden; bij meer dan één verbinding raises hij |
