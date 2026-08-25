# Plan van aanpak — de droogte-eis als waterstand

Versie 2 · 25 augustus 2026 · **gebouwd**

Dit document sluit aan op `PLAN_TOOLS_REFACTOR.md` (deel 1, WP0–WP7) en
`PLAN_UITWISSELING_EN_NETWERK.md` (deel 2, WP8–WP11). Het beantwoordt de vraag uit
[issue #35](https://github.com/HKV-products-services/talk-with-the-engineer/issues/35):
waarom kan aanvoeren niet meedoen in de pakketzoeker, en wat is de kleinste eerlijke stap
om dat te veranderen.

## 0. Premisse — dit plan valt onder het ontwerp-doel

Het ontwerp-doel is bevestigd: de tool bedient de **strategische beleidsmedewerker** die in
een klimaatadaptieve brainstorm op grote lijnen wil zien welke ideeën kans van slagen
hebben — dus een **ontwerp-screening**, geen operationele sturing. Alle keuzes hieronder
volgen daaruit; wordt dat doel ooit anders, dan hoort de droogte-eis bij de operationele
episode (#37 §4B) en vervalt een deel ervan.

**Stand van zaken: §4.1 tot en met §4.5 zijn gebouwd, met de toetsen uit §6.** Wat er
gemeten is:

| uitkomst | waarde |
|---|---|
| aanvoeren op de statische eis | inert - nul effect op beide uitlezingen, gradiënt exact nul |
| aanvoeren op de dynamische eis | tekort 120,0 → 87,6 → 55,2 → 0,0 mm bij inlaat 0 → 0,5 → 1,0 → 1,852 m³/s |
| peilopzet aan de droge kant | 0,20 m opzet geeft 7,0 mm buffer, en 7,0 mm minder tekort |
| statisch versus dynamisch | `buffer_mm` gelijk aan `retained_volume_mm` tot 1e-9 |
| het antwoord zonder droogte-eis | onveranderd: `{afvoeren 2,9116}`, 5,59 mln, drie onderscheiden pakketten |
| spookpakketten | geen: aanvoeren staat in nul van de 31 mixen zodra hij niets doet |
| prijsloze maatvoering | de kleinste die de eis haalt: inlaat 0,926 m³/s zet het tekort exact op 60 mm |
| schaduwprijs aanvoeren | omslag rond 14 mln per m³/s inlaat; daarboven komt peilopzet erbij |
| tests | 506 groen (was 484), looptijd van de suite ongewijzigd |
| `optimize` met vijf acties | 31 mixen in 1,2 s |

---

## 1. De eis, scherp gesteld: van de peil-as naar de waterstand-as

Na de terminologiecorrectie van Ton (peil = het streefpeil dat je nastreeft, een afspraak;
waterstand = het niveau dat ontstaat en dat je meet — zie de relabel in PR #40) is de kern
van #35 in één zin te vatten:

> **Aanvoeren is onzichtbaar omdat de droogte-eis een peil-uitspraak is. Een flux verandert
> de peilband niet; hij werkt op de waterstand over de tijd. Aanvoeren kan pas meedoen als
> de eis van de peil-as naar de waterstand-as verhuist.**

Concreet. De huidige droogte-eis is `Constraints.min_storage_mm`, gelezen als
`after.retained_volume_mm` (`state.py:102`):

```python
retained_volume_mm = target_level_rise_m * (area_open_water_ha / area_ha) * 1000.0
```

Dat is een **peil-uitspraak**: het volume onder het opgezette streefpeil, een statische
eigenschap van de peilband. Alleen peilopzet en bergen veranderen hem; een inlaatcapaciteit
(`capacity_in`) komt er niet in voor, en `simulate()` leest `capacity_in` nergens. Daarom is
aanvoeren inert: nul effect op beide eisen, en (sinds `unit_cost=None`) een gradiënt die
exact nul is.

`simulate_deficit` (`simulate.py`) rekent daarentegen een **waterstand-uitspraak**: gegeven
een tekort-scenario zakt de waterstand uit, klemt op de bodem, en levert het resttekort.
Daar levert een inlaat wél millimeters. De hele oplossing van #35 is: **maak de droogte-eis
die tweede uitspraak.**

### Waarom dit alle drie de maatregelen op hun plek zet

| maatregel | op de peil-as (nu) | op de waterstand-as (voorstel) |
|---|---|---|
| **peilopzet** | de enige zichtbare — koopt `retained_volume_mm` | zet de startstand hoger, dus meer ruimte om uit te zakken |
| **peilmarge / voorbemaling** | onzichtbaar | zet de bodem lager (`-level_margin_m` in de klem) |
| **aanvoeren** | onzichtbaar (inert) | vult de waterstand bij over de tijd |

Op de peil-as bestaat alleen peilopzet. Op de waterstand-as doen ze alle drie mee. Dat is de
eis, en de rest van dit plan is techniek.

---

## 2. Het besluit, in vijf punten

1. **De droogte-eis wordt een waterstand-traject over een karakteristieke droogte.** Via
   `simulate_deficit`, gedreven door een statistische droge zomer (`deficit_mm_per_day ×
   length_days`), analoog aan de STOWA-ontwerpbui op de natte kant. Geen uur-voor-uur
   voorspelling — dat zou het een operationeel instrument maken.

2. **De peilband wordt context-invoer.** `WaterSystemInput` krijgt velden voor peilopzet en
   peilmarge, zodat een beleidsmedewerker de staande configuratie kan meegeven ("mijn polder
   draait al 20 cm opzet"). Dit dicht het gat uit de #35-analyse (de MCP-schil kan de
   peilband nu niet eens ontvangen). Het is **staat**, geen zoekruimte.

3. **De zoekmaatregelen (`DEFAULT_ACTIONS`):** peilopzet blijft, **aanvoeren erbij** (niet
   langer inert), **peilmarge blijft eruit** — dat is de operationele hefboom, geen staande
   investering. Peilmarge zit wél in de staat (punt 2), niet in de zoeker.

4. **Geen verzonnen prijzen.** Peilopzet kost drooglegging, aanvoeren kost beschikbaarheid
   van de bron; allebei prijsloos. `Package.priceless` + `switch_price_of` rapporteren de
   schaduwprijs waarbij het antwoord kantelt. Dat is de eerlijke screening-uitkomst.

5. **Aanvoeren's échte ontwerpvraag ligt op het netwerk.** Op polderniveau met een
   aangenomen bron is aanvoeren-erbij de eerste eerlijke stap, maar de strategische vraag
   ("kán er water komen, waarvandaan, langs welke lijn") is de topologie-as
   (`kaart-is-een-keuze.svg`, `de-knoop-is-oppervlak.svg`) en hoort in een eigen issue.

---

## 3. In scope / buiten scope

**In scope**

| onderwerp | |
|---|---|
| Een dynamische droogte-eis (`max_shortfall_mm`) naast de statische | §4.1, §4.2 |
| De peilband als bufferdiepte in `simulate_deficit` | §4.3 |
| De peilband als context-invoer op de toolgrens | §4.4 |
| Aanvoeren toevoegen aan de zoeker, prijsloos | §4.5 |
| De statische `min_storage_mm` behouden als goedkope variant | §4.1 |

**Buiten scope** — expliciet

| onderwerp | reden |
|---|---|
| Een eindige, gedeelde bron voor aanvoeren | dat is de netwerk/topologie-frontier (#37 §7.3), een eigen issue |
| De operationele episode (peilmarge als per-bui-knop) | ander doel; #37 §4B |
| RL / geleerde componenten | op polder-/regioschaal is dit begrensde continue optimalisatie; `optimize` doet dat exact (#37 §6, §10) |
| Een prijs voor peilopzet of aanvoeren | verdringingsvraag, geen investeringspost; `switch_price_of` leest de grens af |
| Klimaatdrift op de droogtestatistiek | zoals de natte kant: buiten scope tot er een tijdas is |

---

## 4. Technische uitwerking

Alle wijzigingen zitten in `tools/toolset_rules_of_thumb/optimize.py`,
`.../simulate.py` (of zijn `PolderState`-wrapper), `models/.../base_rule_of_thumb.py` en
`models/.../actions.py` — géén wijziging aan de rekenkern `clamped_scan`/`water_balance`
zelf, alleen aan wat hem aanroept.

### 4.1 `Constraints` krijgt een dynamische droogte-eis

`Constraints` (`optimize.py:118`) heeft nu twee velden. Er komt een derde bij, en de
statische blijft als goedkope variant:

```python
@dataclass(frozen=True)
class Constraints:
    max_dh_total_m: float | None = None      # inundatie (nat), boven het oorspronkelijke peil
    min_storage_mm: float | None = None      # statische voorraad (peil-as) — behouden
    max_shortfall_mm: float | None = None     # NIEUW: droogte-eis op de waterstand-as
```

Het droogte-**scenario** is exogeen, net als de `storm`, en wordt als los object meegegeven
— niet in `Constraints`, want `Constraints` zijn de eisen en niet de belasting. De canonieke
belasting is het maximaal cumulatief neerslagtekort uit STOWA 2025-23 (§5), met een venster;
een dagelijkse reeks is de getrouwe variant:

```python
@dataclass(frozen=True)
class Deficit:
    cumulative_deficit_mm: float          # STOWA-neerslagtekort bij de gekozen herhaaltijd/regio
    window_days: int                       # groeiseizoen tot de piekdatum, orde 150-180
    daily_deficit_mm: np.ndarray | None = None   # optioneel: het profiel van het karakteristieke jaar
```

De scalaire variant zet `daily_deficit_mm=None` en verdeelt `cumulative_deficit_mm` over
`window_days`; de getrouwe variant vult `daily_deficit_mm` met de P−E-reeks en voedt die aan
`simulate_deficit.direct_precipitation_m`.

### 4.2 `outcome_of` doet een tweede doorrekening

`outcome_of` (`optimize.py:259`) doet nu één `simulate(after, storm)` en leest twee dingen
uit dezelfde toestand. Er komt een derde uitlezing bij, uit een tweede doorrekening, en
alleen wanneer een droogte-scenario is meegegeven:

```python
def outcome_of(state, storm, deficit, actions, quantities) -> Outcome:
    after = _apply_all(state, actions, quantities)
    result = simulate(after, storm)
    shortfall = None
    if deficit is not None:
        shortfall = evaluate_deficit(after, deficit).max_shortfall_mm   # zie §4.3
    return Outcome(
        state_after=after,
        dh_total_m=result.dh_total_above_original_datum_m,   # nat
        storage_mm=after.retained_volume_mm,                  # statisch (behouden)
        max_shortfall_mm=shortfall,                           # NIEUW: dynamisch
        cost=cost,
        priceless=tuple(priceless),
    )
```

`Outcome` (de `NamedTuple`) krijgt het veld `max_shortfall_mm: float | None` erbij. De
haalbaarheidscheck en de marges (`optimize.py:375`, `:620`) krijgen een tak voor
`max_shortfall_mm` naast de bestaande voor `min_storage_mm`.

### 4.3 De bufferdiepte: peilopzet meenemen in de droge klem

Dit is de enige **modelinhoudelijke** keuze, en de reden dat de twee droogte-uitlezingen
weer één ding worden. `simulate_deficit` klemt de waterstand nu op `-level_margin_m`
(`simulate.py:684`, relatief aan het streefpeil). Peilopzet werkt daar niet in door.

**Voorstel (optie a):** de droge bufferdiepte is de héle peilband, dus de klem wordt

```python
lo = -(state.level_margin_m + state.target_level_rise_m)
```

Fysiek: een polder die 20 cm is opgezet kan 20 cm uitzakken naar het oorspronkelijke peil, en
daarna nog `level_margin_m` verder als het gemaal voormaalt. Dan geldt per constructie
`retained_volume_mm = target_level_rise_m × open_water-aandeel × 1000` als precies de
inhoud van de bovenste band — de statische en de dynamische uitlezing meten dan hetzelfde
water in plaats van twee formules op twee velden.

Dit raakt bestaand gedrag van de aanvoertools (`solve_supply`/`evaluate_supply` in
`solve.py`, `supply.py`), dus het raakt de invarianten. Daarom hoort er een test bij die
vastlegt dat opzet de droge buffer vergroot met exact zijn eigen centimeters (§6), en het
is het punt waarop Ton moet bevestigen dat dít de bedoelde bufferdiepte is.

### 4.4 De peilband als context-invoer

`WaterSystemInput` (`base_rule_of_thumb.py:235`) heeft nu geen peilveld; via elke MCP-tool
staat de peilband dus altijd op `[0, 0]`. Toevoegen:

```python
target_level_rise_m: float | None = Field(0.0, ge=0.0, description="Peilopzet [m] ...")
level_margin_m: float | None = Field(0.0, ge=0.0, description="Peilmarge / voorbemaling [m] ...")
```

Deze twee zijn **context**, geen maatregel. Ze zetten de startstand en de bodem; de zoeker
mag ze niet vergroten (peilmarge) respectievelijk vergroot ze alleen via `PeilopzetAction`
(§4.5).

### 4.5 `DEFAULT_ACTIONS` en de prijs van aanvoeren

```python
DEFAULT_ACTIONS = (
    VasthoudenAction(),
    BergenAction(),
    AfvoerenAction(),
    PeilopzetAction(),
    AanvoerenAction(),   # NIEUW — niet langer inert zodra de droogte-eis dynamisch is
)
```

Vijf acties in plaats van vier betekent 31 mixen in plaats van 15 (`max_mix_size` wordt
relevanter, en de melding welke mixen niet zijn onderzocht ook). `PeilmargeAction` komt hier
**niet** bij — operationeel, zie §2.3.

Aanvoeren houdt `unit_cost=None`. Twee dingen om op te letten:

* **De retry-tak** (`from_start(highs)`, `optimize.py:469`) laat een prijsloze actie nu op
  haar bovengrens staan omdat niets haar terugduwt. Zodra de droogte-eis dynamisch is, is er
  een reden om aanvoeren precies groot genoeg te maken en niet groter — maar de tak hoort
  expliciet te toetsen dat een prijsloze actie die de eis al haalt niet op haar zoekgrens
  blijft hangen (anders een spookpakket met `priceless=('aanvoeren',)`).
* **De gratis-lunch, eerlijk gemaakt.** Aanvoeren is prijsloos én gunstig voor de
  droogte-eis, dus de zoeker zou hem gratis inzetten en geprijsde maatregelen verdringen.
  Dat is geen bug maar precies de vraag die de tool moet stellen: `switch_price_of` leest af
  bij welke prijs (van beschikbaarheid) aanvoeren stopt het goedkoopste te zijn, en dat de
  werkelijke prijs de beschikbaarheid van een bron is — de topologie-vraag (§2.5). De
  screening-uitkomst wordt dan: "als er een bron is, is een inlaat het goedkoopste
  droogte-antwoord; de echte vraag is óf er een bron is."

---

## 5. De droogtestatistiek — ingevuld door STOWA 2025-23

De sub-beslissing "welke karakteristieke droogte" is nu beantwoord, en met eigen materiaal:
**STOWA 2025-23, _Droogtestatistiek KNMI'23-klimaatscenario's_** (HKV & KNMI, 2025 —
auteurs Glas en Pezij van HKV). Dit is de exacte tegenhanger van "welke STOWA-ontwerpbui"
op de natte kant: dezelfde herkomst (KNMI'23 / STOWA), dezelfde herhaaltijd-logica.

### 5.1 Wat het rapport levert

- **De hoofdindicator is het maximaal cumulatief neerslagtekort [mm]** over het
  groeiseizoen (1 april – 1 oktober — dezelfde periode die KNMI voor het neerslagtekort
  hanteert). Dat is precies een grootheid in **mm over het gebied**, en dus direct
  vergelijkbaar met de buffer en het tekort die het model al in mm rekent
  (`retained_volume_mm`, `shortfall_mm`).
- **Herhaaltijden via GEV**, per indicator. Ter ijking: een 2018-achtig jaar (~300 mm
  landelijk gemiddeld) komt nu eens per ~20 jaar voor, rond 2050 eens per 4 à 10 jaar, rond
  2100 eens per 2 jaar.
- **Per waterschap**, want de ruimtelijke variatie is groot (noord–zuid meer dan 30 %). Er
  is per waterschap een Excel met per RACMO-jaar het maximaal cumulatief neerslagtekort én
  de bijbehorende herhaaltijd, per klimaatscenario en zichtjaar (Referentie, Hd/Hn 2050 en
  2100, Ld/Ln 2100). Bijvoorbeeld Rijn en IJssel, referentie: het extreemste RACMO-jaar
  `1995_5` = 458 mm neerslagtekort (herhaaltijd ~640), en `2013_1` = 344 mm (herhaaltijd
  ~46) — oostelijk Nederland is droger dan het landelijk gemiddelde.
- **Twee producten:** karakteristieke jaren (per herhaaltijd T2–T100, mét dagelijkse reeks)
  en representatieve 30-jarige reeksen.

### 5.2 Hoe het het model in gaat

De screening-knop wordt daarmee een tripel dat de beleidsmedewerker kiest, analoog aan de
terugkeertijd van de ontwerpbui:

| knop | keuze | bron |
|---|---|---|
| regio | waterschap (of district) | de per-waterschap Excel |
| klimaat | scenario + zichtjaar (Referentie / 2050 / 2100) | het tabblad in die Excel |
| zwaarte | herhaaltijd (T2, T5, T10, T25, T50, T100) | de kolom "Herhaaltijd Neerslagtekort" |

Dat levert één getal: het maximaal cumulatief neerslagtekort `D` [mm]. Twee manieren om het
model ermee te voeden, van grof naar getrouw:

1. **Scalair (eerste stap).** `D` mm over het accumulatievenster (het groeiseizoen tot de
   piekdatum, orde 150–180 dagen) als de droogtebelasting. Dit is de eerlijke versie van de
   placeholder "4 mm/dag over 30 dagen" uit `kaart-is-een-keuze.svg`.
2. **Getrouw (later).** `simulate_deficit` accepteert al een dagelijkse
   `direct_precipitation_m`-reeks; de dagelijkse P−E-reeks van het karakteristieke jaar past
   daar één-op-één in. Dan is de belasting geen constante maar het echte profiel.

### 5.3 De twee grenzen van het product, expliciet

- **Eén karakteristiek jaar dekt de gecombineerde indicatoren maar tot ~T5.** Voor hogere
  herhaaltijden lopen de indicatoren uiteen; het rapport concludeert dat één jaar dan niet
  alles tegelijk representeert. Voor een screening op orde van grootte is dat geen bezwaar,
  maar de tool moet de gekozen herhaaltijd rapporteren en niet doen alsof T50 één net jaar
  is.
- **De RACMO-reeksen zijn synthetisch, niet historisch.** De handreiking bij het rapport
  waarschuwt dat weersvariatie tussen jaren niet als klimaatverandering gelezen moet worden.
  Dat is een gebruiksrandvoorwaarde, geen modelprobleem, maar hij hoort in de uitleg van de
  tool.

Hiermee vervalt de openstaande V7/V8 uit `PLAN_UITWISSELING_EN_NETWERK.md`: de exogene
droogte-as heeft nu een bron, een eenheid en een regionale opdeling.

### 5.4 In de repo opgenomen

De statistiek is als data-asset opgenomen, naar het voorbeeld van `rainfall_patterns.json`:

- **`tools/toolset_rules_of_thumb/drought_statistics.json`** — per waterschap (21) en per
  scenario (Referentie + Hd/Hn 2050·2100 + Ld/Ln 2100) het maximaal cumulatief neerslagtekort
  [mm] bij de herhaaltijden T2, T5, T10, T25, T50, T100, met een `meta`-blok (bron, eenheid,
  seizoen, methode, aannames). `null` waar de herhaaltijd buiten de 240-jarige RACMO-reeks
  valt.
- **`tools/toolset_rules_of_thumb/utils_drought.py`** — de loader (`@lru_cache`, gespiegeld
  op `_load_rainfall_patterns`) met `available_regions()`, `available_scenarios()` en
  `cumulative_deficit_mm(region, scenario, return_period)`.
- **`scripts/build_drought_statistics.py`** — het extractiescript uit de per-waterschap
  Excels, zodat de asset reproduceerbaar is. Per RACMO-jaar ligt het punt `(neerslagtekort,
  GEV-fit-herhaaltijd)` al op de GEV-curve; de waarde bij een doel-herhaaltijd is er langs
  geïnterpoleerd in `log(T)`.

Geverifieerd tegen het rapport: het klimaatsignaal reproduceert Tabel 1. Rijn en IJssel,
neerslagtekort bij T10: Referentie 269 → Hd 2050 361 (+35 %) → Hd 2100 451 (+68 %), gelijk
aan de percentages in het rapport. De regionale spreiding bij T10 loopt van ~237 mm (Hunze
en Aa's) tot ~291 mm (Scheldestromen).

De **dagelijkse reeksen** (de karakteristieke jaren dag-voor-dag, voor de getrouwe variant
uit §5.2) zitten hier **niet** in — de per-waterschap Excels bevatten alleen jaarstatistiek.
Die reeksen staan op de STOWA-site en kunnen later als tweede asset volgen, in hetzelfde
formaat met een `daily_deficit_mm`-veld per (regio, scenario, herhaaltijd).

---

## 6. Toetsen

Alle toetsen hieronder staan er en zijn groen. De naam erachter is de test die hem bewaakt.

| eis | toets |
|---|---|
| De statische eis blijft werken | de bestaande `optimize`-tests op `min_storage_mm`, ongewijzigd |
| Aanvoeren is inert op de peil-as, en dat is de diagnose | `test_supply_does_nothing_on_the_static_storage_requirement` |
| De dynamische eis is een echte waterstand-uitspraak | `test_supply_moves_the_dynamic_shortfall` - monotoon, en nul tekort bij 2 m³/s |
| Opzet vergroot de droge buffer met zijn eigen centimeters | `test_raising_the_target_level_deepens_the_drought_buffer` |
| Statisch en dynamisch meten hetzelfde water | `test_the_two_drought_readings_measure_the_same_water` (op 1e-9) |
| De hele band is de buffer, niet alleen de marge | `test_the_drought_buffer_is_the_whole_level_band` |
| De aanvoertools houden hun antwoord | `test_the_supply_tools_keep_their_answer` - 109,5 mm, het anker uit WP8 |
| Aanvoeren doet nu iets in de zoeker | `test_the_drought_requirement_brings_supply_into_the_package` |
| Een tekort-eis zonder droogte is een fout | `test_the_drought_requirement_needs_a_drought` |
| Geen spookpakket | `test_a_priceless_measure_that_does_nothing_is_not_reported_as_used` |
| De prijsloze maatvoering komt uit de eis | `test_a_priceless_measure_is_reported_at_its_smallest_working_size` |
| en niet uit het startpunt van de zoeker | `test_the_priceless_size_does_not_depend_on_where_the_search_started` |
| Een inerte actie verandert het antwoord niet | `test_an_inert_action_adds_no_distinct_answers` - nog steeds drie |
| De schaduwprijs overleeft de droogte-eis | `test_the_shadow_price_survives_a_drought_requirement` |
| De peilband bereikt de toestand via de toolgrens | `test_the_level_band_reaches_the_state_through_the_tool_boundary` |
| De droogtestatistiek reproduceert het rapport | `test_the_climate_signal_reproduces_the_report` en de rest van `test_droogtestatistiek.py` |
| Peilmarge blijft buiten de zoeker | vastgelegd in de docstring van `DEFAULT_ACTIONS`; de vijf acties staan in de mixtellingen |
| Reproduceerbaar | het gerapporteerde gebied bit-voor-bit gelijk op Linux en macOS (invariant I6), ongewijzigd |

---

## 7. Volgorde, en wat er van elke stap terechtkwam

**Stap 0 — het ontwerp-doel** ✓ bevestigd; zie §0.

**Stap 1 — `Deficit` + `max_shortfall_mm` in `Constraints` en `Outcome`** ✓ (§4.1, §4.2).
De statische eis staat ongewijzigd ernaast; het bestaande `supply.Deficit` is hergebruikt in
plaats van een tweede droogte-object te maken. `Outcome.shortfall_mm` staat als laatste veld
met een default, zodat de bestaande positionele uitpak blijft werken.

**Stap 2 — de bufferdiepte** ✓ (§4.3). `simulate_deficit` klemt nu op
`-(level_margin_m + target_level_rise_m)`. De aanvoertools zetten geen peilopzet, dus hun
ankers uit `BOUW_WP8_WP10.md` Sec. 7.E staan onveranderd - vastgelegd in
`test_the_supply_tools_keep_their_answer`.

**Stap 3 — de peilband als context-invoer** ✓ (§4.4). `WaterSystemInput` heeft nu
`target_level_rise_m` en `level_margin_m`, en `PolderState.from_water_system_input` geeft ze
door. Gemeten aan de toolgrens: 0,20 m opzet met 0,10 m marge geeft netto +0,10 m op
`dh_total`, want de opzet kost marge en de voorbemaling wint een deel terug.

**Stap 4 — aanvoeren in de zoeker** ✓ (§4.5). `DEFAULT_ACTIONS` heeft vijf acties, dus 31
mixen. `_minimise_priceless` verkleint een prijsloze maatregel tot de kleinste maatvoering die
de eisen nog haalt - lexicografisch onder de prijs, en gemeten en niet aangenomen. Nul is
daarvan het bijzondere geval. Daardoor
blijft het antwoord zónder droogte-eis exact wat het was.

**Stap 5 — hier stoppen.** De eindige, gedeelde bron is een eigen issue op de
netwerk-frontier, geen uitbreiding van dit plan. Zie §3.

---

## 8. Wat dit plan niet is

| niet | waarom |
|---|---|
| een RL-opzet | op deze schaal lost `optimize` het exact op; RL komt pas op netwerkschaal (#37) |
| een verzonnen droogte-beloning | drie maatregelen hebben geen prijs; `switch_price_of` doet het beter |
| peilmarge in de zoeker | operationeel; hoort in de context, niet in de investeringsafweging |
| een eindige bron voor aanvoeren | dat is de topologie-frontier, en het maakt de gratis-lunch pas een echte afweging |
| een verzonnen droogtestatistiek | de bron is STOWA 2025-23 (§5): maximaal cumulatief neerslagtekort per waterschap per herhaaltijd |
