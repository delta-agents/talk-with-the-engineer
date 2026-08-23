# Bouwdocument WP13–WP15 — het gebied, de verdeling, en de adjoint

Uitvoeringsplan voor issues [#30](https://github.com/HKV-products-services/talk-with-the-engineer/issues/30),
[#31](https://github.com/HKV-products-services/talk-with-the-engineer/issues/31) en
[#32](https://github.com/HKV-products-services/talk-with-the-engineer/issues/32), in één sweep.

Dit is het werkdocument: bestand voor bestand, met de gemeten ankergetallen, de invarianten en
de faalscenario's. Het ontwerp staat in `PLAN_UITWISSELING_EN_NETWERK.md`; de drie issues zijn
de review van de route. Alle getallen in dit document zijn gemeten op `main` (`dd748fb`) op
23-08-2026, op de referentiecasus uit `tests/src/tools/test_optimize.py`: 4000 ha, 3,5 % open
water, gemaal 5 m³/s, T=1000, winter, p1a, 96 uur, 4 dagen.

---

## 0. Waarom dit één sweep is en geen drie

De drie issues lezen als drie onderwerpen — een plateau, een verdringingsreeks, een gradiënt.
Ze zijn één defect op drie plaatsen:

> **Een vlakke richting plus een puntzoeker geeft een willekeurig antwoord, en niets in de
> uitvoer zegt dat het willekeurig was.**

| # | de vlakke richting | de puntzoeker | het willekeurige antwoord |
|---|---|---|---|
| 30 | peilopzet heeft geen prijs, dus de kostenfunctie is plat in die richting | SLSQP | `peilopzet = 1,00 m` — de zoekgrens — waar 0,571 m de eis haalt |
| 31 | de norm `p = 1` binnen een schil: elke verdeling met dezelfde som is even goed | een LP-solver | een willekeurige verdeling binnen categorie 4 |
| 32 | de klem is niet-glad; op de knijpgrens is de gradiënt één van twee waarden | eindige differenties | een gradiënt die het teken van de stap volgt |

En het is één remedie, ook op drie plaatsen: **meld het gebied, en bouw zo dat er geen zoeker
in het pad van dat gebied zit.** Een interval waarvan de onderkant de eis is, is
zoekeronafhankelijk per constructie. Een waterfall van `sort` en `cumsum` is
solveronafhankelijk per constructie. Een adjoint met de klem strikt actief of strikt inactief
is stapgrootte-onafhankelijk per constructie. Dat is drie keer dezelfde discipline, en die
discipline is goedkoper om één keer af te spreken dan drie keer te heronderhandelen.

Wat de sweep daarmee oplevert dat drie losse bouwen niet opleveren:

1. **Één uitlezing.** `forced` / `optional` / `absent` plus een interval is hetzelfde object
   voor een maatregelpakket (#30) en voor een toewijzing (#31). Twee keer bouwen geeft twee
   vormen die een agent apart moet leren.
2. **Één ε-discipline.** #30 heeft ε op de kosten, #31 heeft ε in de lexicografische relaxatie
   (`obj_i ≤ optimal_i + ε`, precies zoals Ribasim). Dezelfde vraag, en het antwoord hoort
   dezelfde vorm te hebben.
3. **De volgorde valt uit de afhankelijkheden.** WP15 mag niet vóór WP13 (je legt geen
   gradiënt naar een doelfunctie waarvan het optimum nog schuift), en WP14 levert de enige
   niet-triviale toets op de portabiliteit van de kern die WP15 nodig heeft.

---

## 1. Invarianten

I1 t/m I5 uit `BOUW_WP8_WP10.md` blijven onverkort gelden. Drie nieuwe, en ze zijn de
opgeschreven vorm van §0:

| # | invariant | hoe je het ziet |
|---|---|---|
| **I6** | Een gerapporteerd gebied heeft geen zoeker in zijn pad. De grenzen komen uit een eis, een capaciteit of een prijsband — nooit uit een solver-uitkomst. | een test die hetzelfde gebied op Linux en macOS eist, bit voor bit |
| **I7** | "Geen prijs" wordt nooit stil nul. | `grep -n "cost(state) or 0" src/` is leeg; `Package.priceless` is niet-leeg zodra een prijsloze maatregel in het pakket zit |
| **I8** | Geen `description` noemt meer cijfers dan het gemelde interval toestaat. | `test_no_description_outruns_its_interval`, over alle negen tools |

I6 is de belangrijkste van de drie en het is de reden dat dit één sweep is. Hij is ook een
harde reviewvraag bij elke PR: *waar komt deze grens vandaan?* Is het antwoord "daar kwam de
optimizer op uit", dan is het geen grens.

---

## 2. WP13 — het gebied in plaats van het punt (#30)

### 2.0 WP13.0 — de prijs van peilopzet. Eigen PR, en hij gaat voorop

**Waarom dit eerst moet.** `optimize` geeft vandaag bij twee eisen een ánder pakket dan in
`PLAN_UITWISSELING_EN_NETWERK.md` §9 staat, en de suite merkt het niet:

| eisen | plan §9 | gemeten op `main` |
|---|---|---|
| alleen inundatie 100 cm | afvoeren 2,91 m³/s — € 5,59 mln | ✅ gelijk |
| + 20 mm voorraad | bergen 190 ha + peilopzet 24 cm — € 25,67 mln | **afvoeren 5,71 m³/s + peilopzet 57 cm — € 10,97 mln** |

€ 10,97 mln is echt het optimum: om `{bergen, peilopzet}` eronder te krijgen moet bergen onder
81 ha, en bij 81 ha (221 ha open water) is de inundatie-eis niet haalbaar — bergen heeft er
111 ha voor nodig zónder opzet. De € 25,67 mln was het niet-geconvergeerde antwoord van vóór
`COST_SCALE` (8040f8a). Alle 13 tests in `test_optimize.py` blijven groen, omdat
`test_the_second_constraint_changes_the_answer` sinds 84b826c alleen `"peilopzet" in used` en
`set(used) != {"afvoeren"}` toetst — beide houden voor `{afvoeren, peilopzet}`.

De oorzaak is één regel, `optimize.py:117`:

```python
action.at(max(float(quantity), 0.0)).cost(state) or 0.0
```

`cost()` geeft netjes `None`; de `or` maakt er 0,0 van. Daarmee is peilopzet gratis, en dan
koopt hij inundatiemarge die een groter gemaal weer terugverdient.

**En de uitweg is niet een verzonnen prijs.** Sweep over een hypothetische prijs per meter
opzet, elke keer opnieuw geoptimaliseerd — dit is de schaduwprijslezing uit Finke, Weber &
Bertsch (2026):

| prijs peilopzet | pakket | kosten |
|---|---|---|
| geen prijs | afvoeren 5,71 + opzet 0,571 m | € 10,97 mln |
| € 0,10 mln/cm | afvoeren 5,71 + opzet 0,571 m | € 11,54 mln |
| € 0,14 mln/cm | afvoeren 5,71 + opzet 0,571 m | — |
| **€ 0,15 mln/cm** | afvoeren 5,60 + **bergen 2,80 ha** + opzet 0,560 m | — |
| € 0,50 mln/cm | afvoeren 2,78 + bergen 84,4 ha + opzet 0,357 m | € 34,57 mln |
| € 1,20 mln/cm | afvoeren 0,08 + bergen 187 ha + opzet 0,245 m | — |
| **€ 1,50 mln/cm** | **bergen 190,1 ha + opzet 24,2 cm** | — |

Twee dingen die hieruit volgen en die de demo beter maken dan hij was:

1. **Het kantelpunt is € 0,14 mln per cm**, en de substitutie is *continu* — bergen komt er
   met 2,8 ha in en groeit. Er is geen sprong, dus er is ook geen "omslagpunt" te melden maar
   een prijsas.
2. **Bij € 1,50 mln per cm komt exact het gedocumenteerde `{bergen 190 ha, opzet 24 cm}`
   terug.** Het oude antwoord was dus niet onzin — het is het juiste antwoord op een andere
   vraag, namelijk die waarin drooglegging € 1,5 mln per centimeter waard is. Ter
   plausibiliteitscheck: 24,2 cm × € 1,5 mln/cm = € 36 mln over 4000 ha is **€ 9.075 per
   hectare**, ongeveer een tiende van de agrarische grondwaarde die `COST_OPEN_WATER` zelf als
   bron noemt (€ 95.400/ha, Kadaster/NVM 2025). Dat is een bespreekbare orde van grootte, en
   dat is precies het punt: de politieke variabele wordt expliciet in plaats van weggestopt in
   een ontbrekende prijs.

Dat is een betere demo dan "afvoeren verdwijnt uit het pakket". De zin wordt: *afvoeren
verdwijnt uit het pakket zodra een centimeter drooglegging meer dan anderhalve ton per hectare
waard is — en of dat zo is, is aan het waterschap.*

**Taken.**

| # | bestand | wat |
|---|---|---|
| 13.0.a | `tools/.../optimize.py` | `or 0.0` weg. `outcome_of` geeft `(after, dh, storage, cost, priceless)` terug, met `priceless` de namen van de maatregelen met `unit_cost is None` én een maatvoering > 0 |
| 13.0.b | `tools/.../optimize.py` | `Package` krijgt `priceless: tuple[str, ...]` en `cost_range: tuple[float, float] \| None` (som over `action.cost_range(state)`; `None` zodra er een prijsloze maatregel in zit) |
| 13.0.c | `tools/.../optimize.py` | `switch_price_of(state, storm, constraints, measure)` — bisectie op de prijs per eenheid waarbij de *verzameling* gebruikte maatregelen in `best` verandert. Geen nieuwe zoeker: `optimize` in een bisectie, ~20 aanroepen van 0,6 s is te veel, dus bisectie op een vooraf uitgerekende grove sweep van 8 punten en daarna 6 verfijningen |
| 13.0.d | `models/.../actions.py` | docstring van `PeilopzetAction` en `AanvoerenAction`: "geen prijs" verwijst naar `switch_price`, niet naar "gratis". `UnitCost` houdt `gt=0` — een prijs van nul is iets anders dan geen prijs, en dat is goed zo |
| 13.0.e | `PLAN_UITWISSELING_EN_NETWERK.md` §9 | de tabel bijwerken met het gemeten pakket, en de prijsas erbij |

**Tests.**

| test | wat hij vastlegt |
|---|---|
| `test_a_priceless_measure_is_not_free` | `{afvoeren, peilopzet}` heeft `priceless == ("peilopzet",)` en `cost_range is None` |
| `test_the_documented_package_returns_at_its_shadow_price` | bij € 1,5 mln/cm is `best` `{bergen, peilopzet}` met bergen in [185, 195] ha en opzet in [23, 26] cm |
| `test_the_switch_price_is_where_the_package_changes` | `switch_price_of(..., "peilopzet")` ligt tussen € 0,13 en € 0,16 mln/cm, en één cent onder/boven die waarde verschilt de maatregelverzameling |
| `test_the_second_constraint_changes_the_answer` (bestaand, **verscherpen**) | expliciet `set(used) == {"afvoeren", "peilopzet"}` bij geen prijs, mét een comment dat dit aan de prijsas hangt. Zwakke assertie eruit |

**Klaar als.** `grep -n "cost(state) or 0" src/` is leeg (I7) · de gouden regressie en I1–I5 ongemoeid ·
`PLAN_UITWISSELING_EN_NETWERK.md` §9 klopt weer met de code · geen verzonnen prijs voor peilopzet in de repo.

> **✅ Gebouwd** — branch `fix/geen-prijs-is-niet-gratis`, commit `cb74481`. 404 tests groen,
> warnings nog 2, gouden regressie op 1e-12. Gemeten bracket: **€ 0,144–0,145 mln/cm**, en bij
> € 1,5 mln/cm komt `{bergen 190,1 ha, opzet 24,2 cm}` exact terug.
>
> Twee afwijkingen van dit plan, met reden:
> - `outcome_of` levert een `Outcome`-**NamedTuple** in plaats van een langere tuple. Indexeren
>   (`[3]`) blijft werken, uitpakken met vier namen niet — dat was op vier plekken en is
>   omgezet naar attribuutgebruik, wat leesbaarder is dan `_after, dh, _storage, _cost`.
> - `switch_price_of` bisecteert op de **maatregelverzameling** en niet op de kosten, en meldt
>   een **interval** in plaats van een getal. De verzameling is de robuuste grootheid (WP12:
>   0 van 162), en een punt zou meer precisie suggereren dan bisectie op een SLSQP-vergelijking
>   waar kan maken. Kosten: 14 `optimize`-aanroepen, gemeten 4,9 s — geen tool dus, een analyse.

**Faalscenario.** `switch_price_of` blijkt niet monotoon — bij een hogere prijs komt een
maatregel terug die eerder verdween. Dan is er geen enkel kantelpunt maar een verzameling, en
dan meldt de functie het *interval* waarin de verzameling wisselt en niet één getal. Meten,
niet aannemen: de sweep hierboven is monotoon op 13 punten, en dat is geen bewijs.

### 2.1 WP13.1 — het gebied bestaat, intern

**Correctie op de aanname in #30.** `packages` is niet het gebied. Ontdubbeld op de maatvoering
over alle vier de acties:

| eisen | mixen | haalbaar | onderscheiden antwoorden | binnen ε = 30 % |
|---|---|---|---|---|
| alleen inundatie | 15 | 12 | 3 | **1** |
| + 20 mm voorraad | 15 | 6 | 2 | **1** |
| alleen voorraad | 15 | 8 | **1** | 1 |

Zes van de twaalf haalbare mixen geven letterlijk `{afvoeren 2,91}`. Stap 1 punt 1 uit het
issue — *het SLSQP-punt dat we al hebben* — levert dus niets; de 1D-sweep is de hele opbrengst.
Dat is nieuw rekenwerk, geen uitlezing, en het hoort zo in de PR-beschrijving te staan.

**ε komt uit de prijsband, niet uit een afspraak.** `UnitCost.low/high` bestaat al en is al
onderbouwd:

| maatregel | band | relatief |
|---|---|---|
| gemaal | € 1,86 – 2,04 mln per m³/s | −3 % / +6 % |
| bergen | € 120 – 230 k per ha | −11 % / **+70 %** |

Een platte 15 % is dus tegelijk twee keer te ruim voor het gemaal en vier keer te krap voor
bergen. Criterium: **twee pakketten zijn niet te onderscheiden zodra hun kostenintervallen
overlappen** — dat is ε-dominantie (Laumanns, Thiele, Deb & Zitzler 2002), gebouwd uit getallen
die we al hebben.

**En het echte plateau zit in de kostenvórm.** ε op het kostenniveau bereikt bergen nooit: het
tweede onderscheiden antwoord bij de inundatie-eis is `{bergen 111,2 ha}` à € 15,01 mln, dus
+169 %. Maar in de trapkost-lezing die `AfvoerenAction.replacement_quantity` al levert:

| pakket | werkwaarde | band |
|---|---|---|
| afvoeren 2,91 m³/s, lineair | € 5,59 mln | 5,42 – 5,94 |
| afvoeren 2,91 m³/s, **als vervanging** (7,91 m³/s totaal) | € 15,19 mln | 14,72 – 16,14 |
| bergen 111,2 ha | € 15,01 mln | 13,35 – 25,58 |

**1,2 % verschil, ruim overlappende banden.** Dat is het plateau, en het is twee structureel
verschillende antwoorden. Twee gebieden naast elkaar melden — lineair en als vervanging — en
niet één breed gebied; met +172 % als slack slikt de band elk pakket en zegt het plateau niets.

**ε_water is nu twee toleranties in twee eenheden.** `optimize.py:158` doet
`abs(margin) <= 1e-3` over een dict waarin `margins["inundatie"]` in **meter** staat (regel 153)
en `margins["voorraad"]` in **mm** (regel 155). Dus 1 mm op de stand en 1 µm op de voorraad.
Idem `FEASIBILITY_TOLERANCE = 1e-6`. Twee benoemde constanten, met een anker: 1 mm peilopzet
koopt 0,035 mm voorraad, dus "even strak" is een factor 28 — niet 1 en niet 1000.

**Het interval is eenzijdig.** De checkbox "interval ruwweg 2–5 m³/s" kan niet: onder 2,91 mist
de norm (2,00 m³/s geeft 1,225 m tegen een norm van 1,00) en 5,00 kost +72 %. Gemeten:

| ε | interval afvoeren | `dh_total` aan de bovenkant |
|---|---|---|
| 1 % | 2,91 – 2,94 m³/s | 0,993 m |
| 15 % | 2,91 – 3,35 m³/s | 0,892 m |
| 30 % | 2,91 – 3,79 m³/s | 0,786 m |

De onderkant is de **eis** en de bovenkant is **ε**. Dat is I6: geen van beide komt uit SLSQP,
dus Linux en macOS geven per constructie hetzelfde gebied.

**Taken.**

| # | bestand | wat |
|---|---|---|
| 13.1.a | `tools/.../optimize.py` | `EPS_LEVEL_M = 1e-3` en `EPS_STORAGE_MM = 0.035` als benoemde constanten; `binding` en `feasible` gebruiken de juiste per eis |
| 13.1.b | `tools/.../optimize.py` | `sweep_binding(state, storm, mix, constraints)` — 1D-sweep op de bindende maatregel vanaf het eis-snijpunt tot de kosten-ε breekt. Hergebruikt `bisect_decreasing` uit `solve.py` voor de onderkant |
| 13.1.c | `tools/.../optimize.py` | `MeasureRole` enum (`forced` / `optional` / `absent`) en `MeasureRange(name, magnitude_min, magnitude_max, unit, role)` |
| 13.1.d | `tools/.../optimize.py` | `OptimizeResult` krijgt `near_optimal: tuple[Package, ...]` (ontdubbeld op maatvoering) en `ranges: tuple[MeasureRange, ...]` |
| 13.1.e | `tools/.../optimize.py` | `distinct_answers(packages)` — de ontdubbeling, als eigen functie zodat de test hem kan aanroepen |

**Tests.**

| test | anker |
|---|---|
| `test_the_enumeration_collapses_onto_few_answers` | 15 mixen → 12 haalbaar → 3 onderscheiden bij de inundatie-eis |
| `test_the_interval_is_bounded_below_by_the_requirement` | `magnitude_min` ≈ 2,912 m³/s en `dh_total` daar is 1,000 ± 1e-3 |
| `test_the_interval_is_bounded_above_by_the_price_band` | bij ε uit `cost_range` ligt `magnitude_max` in [2,93, 3,40] |
| `test_the_region_is_platform_independent` | het gebied hangt niet van het startpunt af: `optimise_mix` vanaf `zeros` en vanaf `highs` geeft hetzelfde `MeasureRange` (dit is de test die de Mac/Linux-splitsing echt afdekt) |
| `test_forced_and_absent_flip_with_the_second_constraint` | alleen inundatie: `afvoeren` is `forced`. Plus voorraad: `peilopzet` is `forced`, en `afvoeren` is `optional` — **niet** `absent`, zie WP13.0 |
| `test_the_step_cost_reading_puts_storage_on_the_plateau` | de banden van afvoeren-als-vervanging en bergen overlappen; het verschil in werkwaarde is < 5 % |
| `test_two_tolerances_have_two_units` | een voorraadmarge van 0,02 mm is bindend, een van 0,05 mm niet |

**Klaar als.** Alle bovenstaande tests groen · I1–I5 ongemoeid · `optimize` blijft onder 3 s
(nu 0,6 s; de sweep mag dat niet meer dan verdubbelen) · `near_optimal` bevat nooit twee
pakketten met dezelfde maatvoering.

> **✅ Gebouwd** — branch `feat/het-gebied-in-plaats-van-het-punt`, commit `fd78824`. 412 tests
> groen, `optimize` 0,59 s (was 0,53 s, dus de sweep kost ~10 %). Gemeten gebied:
>
> | eisen | rol | interval |
> |---|---|---|
> | alleen inundatie | afvoeren `forced` | **2,912 – 3,185 m³/s** |
> | + 20 mm voorraad | afvoeren `forced`, peilopzet `forced` | 5,713 – 6,249 m³/s / 0,571 m |
> | alleen voorraad | peilopzet `forced` | **0,571 – 1,000 m** — het plateau, niet de zoekgrens |
>
> Vier afwijkingen van dit plan, met reden:
> - **`EPS_STORAGE_MM` is geen constante geworden** maar wordt afgeleid: `eps_of(state)` geeft
>   `EPS_LEVEL_M · open-wateraandeel · 1000`. Een vaste 0,035 zou de referentiepolder
>   hardcoderen; zo schaalt hij mee en is hij dezelfde fysieke uitspraak ("een millimeter peil").
> - **`FEASIBILITY_TOLERANCE` blijft absoluut en strak op beide eisen**, tegen de plantekst in.
>   Het gemelde probleem is dat `binding` 1000× strenger was op de voorraad — dat is een
>   *rapportage*drempel. Een strenge haalbaarheidstoets is niet dezelfde fout: die zit aan de
>   veilige kant, en hem symmetrisch losser maken zou een gedragswijziging zijn zonder baat.
> - **`cost_range` is gesplitst in twee velden.** `cost_range` is `None` zodra er een prijsloze
>   maatregel in zit (geen prijs, geen band); `priced_cost_range` blijft bestaan als maat voor
>   wat we van prijzen weten. Zonder die splitsing is ε nul zodra peilopzet meedoet en klapt het
>   gebied tot een punt — precies het probleem dat we oplossen.
> - **`ranges` is coördinaatgewijs en dus een ondergrens**, niet de projectie van het gebied: één
>   maatregel beweegt, de rest staat vast op het goedkoopste pakket. Zichtbaar in rij 2: peilopzet
>   komt als 0,571–0,571 uit de sweep omdat het gemaal vaststaat. De projectie is minstens zo
>   breed. Dat staat zo in de docstring en hoort zo in de tekst van WP13.2.

**Faalscenario.** De sweep op de bindende maatregel is niet zinvol als er twéé maatregelen
tegelijk bewegen — dan is het gebied tweedimensionaal en is een interval per maatregel een
projectie, niet het gebied. Dat is precies wat MAA de romp noemt, en bij dimensie 4 is die
exact uit te rekenen waar de energiemodellen hem moeten benaderen (Lau e.a. 2024 vindt dat de
expliciete romp bij hogere dimensie vastloopt; Lau e.a. 2025 codeert hem daarom impliciet).
**Besluit voor deze bouw: projecties, en in de tekst zeggen dat het projecties zijn.** De romp
is WP16 als iemand hem wil.

### 2.2 WP13.2 — de zin, en de precisie die er al is

De discipline bestaat al: `supported_digits` → `_rounded`. Maar `_magnitude_nl` en
`_magnitude_en` negeren `digits` voor drie van de vijf eenheden — `descriptions.py:97/99/100`
en `109/111/112` hardcoderen `:.2f` voor m³/s en `:.0f` voor peilmarge. De "2,91" uit de titel
van #30 is letterlijk die regel.

**Taken.** `_magnitude_nl` / `_magnitude_en`: alle vijf de takken via `_rounded` ·
`describe_region(ranges, language)` — de zin uit het gebied, in de stijl van `append_spread` ·
`RegionOutput`-achtige velden op de `optimize`-uitvoer (nog geen tool, zie §7).

**Tests.** `test_no_description_outruns_its_interval` (I8, over alle negen tools) ·
`test_the_sentence_names_the_interval_not_the_point` — de zin bevat "2 tot 3" of "ordegrootte
3", en niet "2,91".

### 2.3 WP13.3 — de claim testen

Geen nieuwe zoeker: `ranges` uitlezen. "Afvoeren is onmisbaar" is waar zodra `role is forced`
in elk near-optimaal pakket. Eén test die de claim laat falen zodra de voorraadeis aanstaat —
en let op WP13.0: met de huidige prijsas is afvoeren daar `optional`, niet `absent`. De claim
die wél omvalt is "afvoeren alleen is genoeg".

Plus: de y-as van de robuustheidscurve krijgt `cost_range` in plaats van `cost`. Dat is de
onbetrouwbaarste as in het systeem en tegelijk de kop van de demo.

---

## 3. WP14 — de droge kant verdeelt (#31)

### 3.0 WP14.0 — papier: de vormen, θ, en één bewijsverplichting

**De droge kant heeft nog geen netwerk.** `SystemState.capacity_in_m3_per_sec` bestaat
(`system.py:51`) en gaat heen en terug door `from_polders` (`:122`) en `to_polders` (`:213`),
maar **geen berekening leest hem**: `grep -rn capacity_in src/talk_with_the_engineer/tools/`
geeft alleen `supply.py`, waar een losse `PolderState` wordt gebouwd. `simulate_network` is
uitsluitend de natte kant. Stap 1 uit het issue is dus niet "de bron krijgt een voorraad" maar
"er is nog geen pass om die voorraad aan te bieden".

**De gedeelde pot valt uiteen, en dat schrapt de LP.** `SystemState` staat één uitgaande
verbinding per knoop toe (`system.py:109` raist anders) en `Connection` draagt beide
capaciteiten naar dezelfde `to`. Op de droge kant heeft elke knoop dus precies **één bron**:
`downstream[i]`. Elke afnemer heeft één pad, en dan is de toewijzing een transportprobleem op
een boom. Numeriek getoetst tegen `scipy.linprog` (HiGHS):

| toets | gevallen | grootste afwijking |
|---|---|---|
| lexicografisch + gelijk tekort vs opeenvolgende LPs, één bron | 300 netten | 3·10⁻¹² |
| maximin vs LP op de dekkingsfractie | 300 netten | 2·10⁻¹⁶ |
| **twee lagen** (bron → boezems met eigen kantcapaciteit → polders), categorietotalen | 400 netten, 1303 totalen | 3·10⁻⁹ (= de LP-slack, dus exact) |

Het waarom is scherper dan "greedy werkt": **fan-out 1 neemt de routeringskeuze weg.** Een
afnemer heeft één pad, dus er is niets te routeren; alleen de hoeveelheid per knoop is vrij, en
die is alleen vrij wanneer de bron bindt — en dan krijgen lagere categorieën toch niets. De
scheidslijn is dus fan-out en niet diepte, en dat staat zo in de literatuur: Danna e.a.
(INFOCOM 2012) stellen dat bij één pad per afnemer water-filling de max-min fair oplossing
geeft, en dat er bij meerdere paden **geen combinatorisch algoritme bekend is**. Le Boudec
(EPFL 2021) Theorem 1.2.2–1.2.4 geeft uniciteit plus water-filling bij vaste routing.

**Handmatig tegenvoorbeeld voor fan-out 2**, om de grens vast te leggen: twee bronnen met elk
1 eenheid; knoop X (cat. 1, vraag 1) kan uit beide, knoop Y (cat. 2, vraag 1) alleen uit de
eerste. Kiest greedy voor de eerste, dan krijgt Y niets waar de LP hem 1 geeft. Dat hoort als
`xfail`-test in de suite: hij documenteert waar de gesloten vorm ophoudt.

**De wet noemt binnen een schil wél een criterium, en het is de gewogen vorm.** Uit het
Landelijk draaiboek waterverdeling en droogte (29-01-2026), tabel 3.1, op grond van
**art. 3.14 Bkl**:

> "Binnen de categorieën 1 en 2 is sprake van een prioriteitsvolgorde. Binnen de categorieën 3
> en 4 vindt onderlinge prioritering plaats op basis van **minimalisatie van de economische
> maatschappelijke schade**."

En uit de Handleiding verdringingsreeks (versie 2, 26-03-2020): *"Nadere prioritering tussen
categorie 3 en categorie 4 is niet mogelijk."*

Drie gevolgen: binnen cat. 1 en 2 is het lexicografisch tot op de post; binnen cat. 3 en 4 is
het criterium `min Σ wᵢ·tekortᵢ` — de **gewogen** vorm, niet gelijk tekort en niet maximin; en
de schillen zijn ondoordringbaar, wat "één LP met grote gewichten" uitsluit.

**Dus de vier vormen zijn geen menu maar twee lagen plus een band:**

| vorm | status | gesloten vorm | anker |
|---|---|---|---|
| lexicografisch tussen schillen | **wettelijk** | greedy per categorie, twee passes | Danna e.a.; Handleiding |
| gewogen binnen cat. 3/4 | **wettelijk criterium** | Edmonds greedy op aflopend gewicht | Schrijver Thm 44.3 / Cor. 44.3b |
| gelijk tekort in een schil | proxy | proportioneel + iteratief vrijgeven | WEAP Equity Groups |
| maximin | proxy / band | capped water-filling, oplossing **uniek** | Le Boudec Thm 1.2.2–1.2.4 |

**De normkeuze ís de vormkeuze**, en dat is de brug naar #30. Uit de Deltares Quick Scan Tool
(Gijsbers, Baayen & ter Maat): *"The order p ≥ 1 denotes the norm under consideration. One
would select p = 1 for linear penalization, or p = 2 to penalize large violations
disproportionately more."* Met p = 1 is de doelfunctie plat over elke verdeling met dezelfde
som, en kiest de solver willekeurig — **exact het plateau-probleem uit #30, één laag lager.**
Daarom dezelfde uitlezing en niet een tweede.

**Eén bewijsverplichting.** De stap "boom → laminaire familie → polymatroid", waar de
gewogen-greedy op rust, is niet als citeerbare stelling te vinden. Schrijf de rangfunctie voor
onze boom uit en bewijs submodulariteit zelf — korte inductie over de boomdiepte — en hang
Theorem 44.3 daaraan op. **Dit is een taak in WP14.0, geen aanname.** Faalt het bewijs, dan
vervalt alleen de gewogen vorm naar een LP; de andere drie staan op Danna/Le Boudec.

**θ.** `θ` = beschikbaar volume aan de bron als fractie van de som van de vragen. Blijft de
interne as; V7 (KNMI-reeks) voedt hem later, niet andersom.

### 3.1 WP14.1 — de omgekeerde pass

| # | bestand | wat |
|---|---|---|
| 14.1.a | `models/.../system.py` | `topological_levels()` cachen (`functools.cached_property` op een frozen dataclass: via `object.__setattr__` of een `_levels`-veld). Gemeten 3,7 ms bij 8500 knopen, per aanroep, en `simulate_network` roept hem elke keer opnieuw aan |
| 14.1.b | `tools/.../network.py` | `_backward_pass(system, demand, available, levels)` — de spiegel van `_forward_pass`, over `reversed(levels)`. Zelfde vorm: geen lus over de knoop-as, `np.add.at` voor de aggregatie omhoog, indexering voor de verdeling omlaag |
| 14.1.c | `models/.../connection.py` | `head_max_in_m: float \| None`. **Eigen veld en niet `head_max_m` hergebruiken:** de opvoerhoogte van een gemaal en het verval over een zwaartekrachtinlaat zijn niet hetzelfde getal. Zelfde argument als waarom `Connection` twee capaciteiten draagt |
| 14.1.d | `tools/.../network.py` | derating van `capacity_in` op het *negatieve* deel van het bronpeil: `clip(1 - maximum(-source_level, 0)/head_max_in, 0, 1)`. De droge klem is `hi=0`, dus standen zijn ≤ 0 |

**Tests.** `test_the_backward_pass_mirrors_the_forward_pass` — op een ketting zonder
beperkingen is de som van wat er wordt onttrokken gelijk aan wat de bron levert, tot 1e-12 ·
`test_topological_levels_are_computed_once` — teller op de aanroep ·
`test_a_falling_source_throttles_the_intake` — met `head_max_in_m` gezet zakt `capacity_in` mee.

### 3.2 WP14.2 — de eindige bron

`OUTSIDE` blijft oneindig aan de **natte** kant (de zee neemt je water aan). Aan de droge kant
krijgt een bron `available_m3`; default `inf`, zodat bestaande aanroepen niet verschuiven.

**Ankers.** `available_m3 = inf` is bitgelijk aan de huidige aanvoertools · Twente-anker: 4000
ha, 1 % open water, 4 mm/dag, 30 dagen vraagt 4,68 mln m³; met `available_m3 = 0` is de status
tekort en niet "gedekt", en het volume blijft in de uitvoer · twee afnemers op één bron: de som
van wat ze krijgen ≤ wat er is, tot machineprecisie.

**En één ding dat gaat rotten.** `_supply_availability_caveat`
(`base_rule_of_thumb.py:628`) zegt nu *"het zit niet in dit model"*. Zodra WP14.2 landt is dat
onwaar. Die caveat moet **in dezelfde PR** van "dit zit er niet in" naar "dit zit erin, en dit
gaf het", met als resterende aanname het regionale systeem buiten de selectie. In de
definition-of-done, anders blijft hij staan.

### 3.3 WP14.3 — de vier vormen

Eén constraint-set: massa, inlaatcapaciteit, bronvoorraad, vraag per knoop. Vier doelen, geen
droogtelus, **geen solver**.

| # | wat |
|---|---|
| 14.3.a | `AllocationShape` enum: `LEXICOGRAPHIC`, `WEIGHTED`, `EQUAL_DEFICIT`, `MAXIMIN` |
| 14.3.b | `allocate(system, demand, categories, available, shape, weights=None)` — greedy per categorie (twee passes), met de binnen-de-schil-regel als parameter |
| 14.3.c | `AllocationResult` met per knoop de toegekende fractie, de bindende categorie, en `role` (`forced` als elke vorm hem geeft, `optional` als sommige) — **hetzelfde `MeasureRole` als WP13.1c** |
| 14.3.d | speelgoednet in `tests/`: één bron, drie afnemers in drie categorieën, ankergetallen eerst op papier |

**Tests.** `test_lexicographic_starves_the_lowest_category_first` — cat. 4 krijgt 0 zolang
1–3 niet vol zijn · `test_equal_deficit_within_a_shell` · `test_maximin_is_unique` — twee
verschillende startordeningen geven dezelfde toewijzing (Le Boudec Thm 1.2.2) ·
`test_the_closed_form_matches_a_reference_lp` — de LP-vergelijking uit WP14.0 als test in de
suite, met een vaste seed, 50 netten, tolerantie 1e-9 · `test_fan_out_two_breaks_the_closed_form`
(`xfail`, strict) — het handmatige tegenvoorbeeld · `test_the_four_shapes_share_one_matrix` —
geen tweede netwerkcode.

### 3.4 WP14.4 — het θ-plaatje, analytisch

Niet sweepen en geen mpLP: de knikpunten van capped water-filling zijn de gesorteerde caps en
vragen, dus de critical regions van Gal & Nedoma (1972) volgen exact en direct. De survey van
Nemesch e.a. (arXiv:2501.11544, 2025) noemt parametrische min-cost flow expliciet als geval met
exponentieel veel regio's — en mpLP is voor zover te vinden **nooit** op waterverdeling
toegepast. Als de boom een gesloten vorm heeft, ís die gesloten vorm de expliciete
parametrische oplossing.

**Taken.** `theta_breakpoints(...)` — de gesorteerde knikpunten plus de toewijzing per regio ·
uitvoer als tabel categorie × θ per vorm.

**Tests.** `test_the_breakpoints_are_analytic` — een dichte sweep over θ ∈ [0,1] met 1000
punten wijkt nergens meer dan 1e-9 van de stuksgewijs-lineaire reconstructie af (**de sweep is
de test, niet het antwoord**) · `test_the_theta_table_is_platform_independent` (I6) ·
`test_no_description_sells_one_allocation_as_the_verdringingsreeks`.

**Wat hier níet in gaat.** JAX door de LP (er is geen LP), V8 (doorspoeling/chloride), V7 als
vervanging van θ, en de graaf als toolargument. En één idee voor ná stap 3, niet nu: Zuid-Afrika's
*assurance levels* (Rudberg 2026) verdelen in de **kansdimensie** — een betrouwbaarheid per
afnemer in plaats van een volume. Dat is precies wat een gesloten vorm goedkoop kan en een
LP-per-tijdstap niet, en het is de natuurlijke plek waar V7 binnenkomt.

---

## 4. WP15 — de adjoint (#32)

### 4.0 WP15.0 — papier: `J`, en de vaste-puntvraag die stap 3 blokkeert

**`J` bestaat nog niet op het netwerkpad.** `simulate_network` leest `area_ha`,
`pct_open_water`, `retention_fraction`, `days_to_retain`, `level_margin_m`,
`capacity_out_m3_per_sec` en `head_max_m`. Hij leest **niet** `target_level_rise_m`. Peilopzet
is dus een no-op in `simulate_network`, en `NetworkResult` heeft geen veld om hem terug te
brengen. Gevolg voor de checkbox "alle vier de acties": peilopzet heeft daar een adjoint van
identiek 0 omdat het veld ongebruikt is, en op het één-polderpad is zijn afgeleide naar
`dh_total` analytisch exact 1. In beide gevallen slaagt een eindige-differentie-vergelijking
triviaal en bewijst niets.

De gradiënten die iets toetsen zijn **bergen** (via
`metres_per_m3_per_sec = 3600/(area_open_water·1e4)`, een 1/A-nonlineariteit in de recursie) en
**afvoeren** (door de klem heen). `J` = som van `dh_max_m` over de selectie, plus
`target_level_rise_m` zodra dat in de uitlezing zit. Som en geen softe-max: de `max` zit al in
de tijdas (`water_level.max(axis=1)`), dus de keuze gaat alleen over de knoop-as, en een som
heeft geen temperatuur die we moeten verzinnen.

**Terzijde, en het scheelt werk:** "de bindende knoop" heeft de adjoint niet nodig —
`_binding_node` (`region.py:69`) rekent hem exact uit. De adjoint voegt een andere en betere
vraag toe: niet *waar knelt het* maar *waar doet een euro het meeste*. Dat onderscheid hoort in
de PR-beschrijving, anders lijkt de adjoint een duurdere versie van iets dat er al is.

**En dit blokkeert stap 3.** De derating is een `while`-lus (`network.py:173`) met een
uitgangstest die een tak op een arraywaarde is (`:204`). In JAX is dat `lax.while_loop`, en die
is **niet reverse-mode differentieerbaar** — de docs zeggen letterlijk *"while_loop is not
reverse-mode differentiable because XLA computations require static bounds on memory
requirements"*, en de fout komt uit de transpose-regel, niet uit de JVP. Forward-mode (`jvp`)
werkt dus wél, en dat is een goedkope tussenstap.

Drie opties, en de keuze hoort in WP15.0:

| optie | wat | prijs |
|---|---|---|
| **`lax.scan` met vast budget** | de iteratie uitrollen; gemeten **2 iteraties** op de ketting, en de monotone-`minimum`-constructie begrenst hem per constructie | goedkoopst, en genoeg zolang het budget klopt |
| `jax.custom_vjp` | de vaste-punt-adjoint uit de JAX-docs; de backward is zelf een goedkope vaste-puntiteratie | nul dependencies, meer eigen code |
| `optimistix.fixed_point(..., adjoint=ImplicitAdjoint())` | solverlogica uitbesteed | een dependency |

**`jaxopt` valt af**: *"JAXopt is no longer maintained nor developed."* Dat staat nog in de
bronnenlijst van #31 en #32 en moet daar weg.

**Voorstel: `lax.scan` met vast budget**, met een test die faalt zodra de iteratie het budget
raakt. Dat houdt de kern dependency-vrij en het is eerlijk over wat er gebeurt. Impliciete
differentiatie is de escalatie als het budget in de praktijk niet houdt.

**Mag dat, met een niet-gladde klem?** Ja, bijna overal, en dat is uitgezocht: Bolte, Le,
Pauwels & Silveti-Falls (NeurIPS 2021) geven een niet-gladde impliciete-functiestelling waarin
*"replacing derivatives by Clarke Jacobians in the usual differentiation formulas is fully
justified"* voor **definable** problemen — een geklemde translatie is stuksgewijs affien en dus
definable. Bolte, Pauwels & Vaiter (NeurIPS 2022) bewijzen convergentie van de afgeleiden
bijna overal voor *nonexpansive* niet-gladde iteraties, en `np.minimum(capacity, derated)` is
per constructie monotoon dalend en begrensd. Grazzi, Pontil & Salzo (ICML 2024) geven de
lineaire snelheden.

**Het praktische risico zit niet in de theorie.** `∂F/∂x` van de derating is een **diagonaal
0/1-masker** — knijpt deze knoop wel of niet — dus de lineaire solve is spotgoedkoop. Maar bij
8500 knopen ligt er altijd een handvol gemalen precies op de knijpgrens, en daar is de
gradiënt willekeurig één van twee waarden. Dat is een discontinuïteit, geen fout, en het maakt
eindige-differentie-verificatie onbetrouwbaar — precies waar stap 3 op leunt. Dus: doe de
FD-controle met de klem **strikt actief of strikt inactief**, en rapporteer apart hoeveel
knopen binnen tolerantie van de grens liggen.

### 4.1 WP15.1 — de kern is echt portabel

**De AST-test dekt 2 van de 5 regels uit §7, en het netwerk gebruikt de niet-bewaakte tak.**

| §7-regel | in de test? |
|---|---|
| geen lus over de tijd- of knoop-as | ja (`ast.For`, comprehension) |
| geen `.item()` / `float()` | ja |
| geen `if` op een arraywaarde | **nee** — `simulate.py:72, 87, 89` |
| in-place mutatie niet in de recursie | **nee** — `simulate.py:110, 111, 114` |
| geen pydantic in de kern | dekt WP3 |

`guarded = {"clamped_scan", "slack_of"}` (`test_kern_properties.py:883`) mist `_reflected_scan`
— en dat is de functie die het netwerk aanroept, want `clamped_scan(delta, -margin, inf)` neemt
het snelpad. Gemeten op 8500 × 240:

| pad | wat | tijd |
|---|---|---|
| snelpad `_reflected_scan` | `cumsum` + `np.minimum.accumulate` | **26 ms** |
| algemene tak | log-diepte scan, in-place | **206 ms** |

**En `jnp.minimum.accumulate` is geen snelpad.** Hij bestaat, maar valt terug op
`_accumulate_via_scan`, een sequentiële `lax.scan`; alleen `jnp.add` en `jnp.multiply` hebben
een eigen pad. De juiste API is **`jax.lax.cummin`**, en die lost het onderliggende probleem
zelf op — zijn JVP-regel schrijft hem bij differentiëren om naar een associatieve scan, met dit
commentaar in de broncode:

> `# Irrespective of backend, we always use the parallel prefix scan`
> `# implementation when differentiating because reduce_window is not`
> `# arbitrarily differentiable.`

Dus onder JAX convergeren snelpad en algemene tak op hetzelfde algoritme zodra er een gradiënt
aan hangt. Dat maakt de bit-gelijkheidstest van WP15.2 een echte kruiscontrole van twee
implementaties van dezelfde monoïde.

**Eén ontwerpeis die niet in het issue staat.** `lax.associative_scan` is reverse-mode
differentieerbaar per constructie (het is geen primitive, alleen slice/concat/rev), en
asymptotisch is forward:backward 1:1. Maar JAX-issue #19498 (onopgelost) rapporteert een ~10×
steilere helling voor afgeleiden naar een parameter die *in* de binaire operator zit. Dus:
**de te differentiëren grootheden horen in de elementen van de scan, niet als grenzen die in
`combine` worden gebroadcast.** `clamped_scan` doet nu het laatste, en `level_margin_m`
(voorbemalen) is een van de vier acties waarnaar we willen differentiëren. Dat is een
signatuurwijziging en hij hoort hier, niet in WP15.3 als verrassing.

**Taken.** `xp` op moduleniveau, `xp = numpy` als default · `pixi.toml`: `jax` als **optionele
feature**, niet in `default` · backend-gekozen implementatie van het snelpad (`np.minimum.accumulate`
tegenover `lax.cummin`) · `clamped_scan` herparametriseren zodat grenzen per tijdstap
meegaan als elementen · AST-test uitbreiden met `if`-op-arraywaarde, `ast.Subscript` als
assign-target, en `_reflected_scan` + `_forward_pass` in `guarded`; plus een check dat de
bewaakte functies `xp.` gebruiken en niet `np.`.

**Klaar als.** `xp is numpy` is default · geen import van `jax` op het kritieke pad van de
negen tools · `pixi run pytest` zonder de jax-feature blijft groen · de AST-test dekt 4 van de
5 regels · `grep -n "minimum.accumulate" src/` geeft alleen de backend-schakelaar (het
B9-vinkje in `BOUW_WP8_WP10.md` §3.7 is nu onwaar en wordt bijgewerkt).

### 4.2 WP15.2 — twee backends, één eenknoopcasus

**Gemeten uitgangspunt**, ketting van *n* polders op één boezem, 240 uur:

| knopen | zonder derating | met derating |
|---|---|---|
| 101 | 0,6 ms | 1,6 ms (2 iteraties) |
| 1.001 | 7,8 ms | 16,6 ms |
| 8.501 | **55 ms** | **140 ms** |

De WP10-eis "8500 × 240 uur onder 100 ms" houdt dus **zonder** derating en niet ermee — en
derating is het enige geval waarin de cascade bestaat. Het budget van WP15.2 moet zeggen welke
van de twee het meet.

**Tests.** `test_one_node_is_bit_equal_across_backends` — één knoop plus `OUTSIDE`, float64,
1e-12, JAX == numpy == `simulate` · `test_eight_thousand_nodes_within_budget` — met en zonder
derating apart gerapporteerd, geen stille skip · `test_i1_to_i5_hold_without_jax`.

### 4.3 WP15.3 — de enkele adjoint

`jax.vjp` van `J` naar de actievector per knoop. Controle: centrale differentie op een keten
van 5, op **bergen en afvoeren** (zie WP15.0), met de klem strikt actief of strikt inactief.
Peilopzet en voorbemalen als unit-checks tegen hun gesloten vorm.

De uitlezing die een mens ziet is niet 8500 gradiënten maar bindende knoop, teken en
ordegrootte — dezelfde les als `RegionOutput`.

**Klaar als.** keten van 5: adjoint en eindige differentie zelfde teken en zelfde
ordegrootte, op de twee niet-triviale acties · 8500 knopen: één `J` naar alle knopen onder
100 ms, met en zonder derating gerapporteerd · vasthouden-benedenstrooms is een bijna-nul in de
adjoint en gemaalcapaciteit niet, als regressie en niet als slide (V10) · het aantal knopen op
de knijpgrens staat in de testuitvoer.

**Faalscenario.** Het vaste-puntbudget van WP15.0 blijkt op een echte topologie niet te
houden. Dan is de adjoint niet fout maar onvolledig, en de uitweg is `custom_vjp` — niet het
budget stilletjes verhogen.

---

## 5. De gedeelde uitlezing

Eén object, drie gebruikers. Dit is de reden dat de sweep één sweep is en het hoort in de
eerste PR die het nodig heeft (WP13.1c), niet twee keer gebouwd.

```
MeasureRole = forced | optional | absent
MeasureRange(name, magnitude_min, magnitude_max, unit, role)
```

| gebruiker | wat een "maatregel" is | waar het interval vandaan komt |
|---|---|---|
| WP13 | een maatregel in een pakket | onderkant = de eis, bovenkant = de prijsband |
| WP14 | een afnemer in een toewijzing | onder- en bovengrens over de vier vormen |
| WP15 | een knoop in de adjoint | teken en ordegrootte, geen millimeter |

En één ε-discipline: **strak op het water, ruim op de euro's, en nooit een getal dat we niet
kunnen onderbouwen.** ε_water uit het model (WP13.1a), ε_kosten uit `UnitCost.low/high`
(WP13.1), ε in de lexicografische relaxatie van WP14.3 uit dezelfde bron als Ribasim's
`obj_i ≤ optimal_i + ε`.

Wat ε **niet** is: een uitspraak over hoe ver een echt besluit van het optimum eindigt. Fossas
Tenas e.a. meten via hindcasting dat dat 44–59 % is, tegen de ≤ 10 % die de literatuur
gebruikt. Dat hoort in de tekst of in een caveat, niet in het criterium — anders slikt de band
elk pakket. (Die percentages komen uit zoekresultaten en niet uit de bron; nakijken voordat ze
ergens in komen.)

---

## 6. Volgorde en afhankelijkheden

```
WP13.0  de prijs van peilopzet  ─┬─►  WP13.1  het gebied  ──►  WP13.2  de zin  ──►  WP13.3  de claim
        (blocker, eigen PR)      │              │
                                 │              └── MeasureRole/MeasureRange ──┐
                                 │                                             │
WP14.0  papier + bewijs  ──►  WP14.1  omgekeerde pass  ──►  WP14.2  eindige bron  ──►  WP14.3  vier vormen  ──►  WP14.4  θ
                                        │                                                        ▲
                                        │                                                        │
                                        └── topological_levels gecacht ──┐              ◄────────┘
                                                                         │
WP15.0  J + vaste-puntbesluit  ──►  WP15.1  xp + AST  ──►  WP15.2  twee backends  ──►  WP15.3  de adjoint
                                             ▲
                                             └── de knoop-as van 14.1b is de eerste echte portabiliteitstoets
```

Drie harde regels in die graaf:

1. **WP13.0 gaat voorop, absoluut.** Zolang `best` schuift is elk gebied eromheen decoratie en
   is elke gradiënt naar `J` een gradiënt naar een bewegend doel.
2. **WP15.3 komt na WP13.1.** Anders optimaliseren we het punt dat we juist tot een gebied
   willen uitbreiden.
3. **WP14.1 vóór WP15.1 is de goedkope volgorde**, niet de verplichte. De omgekeerde pass is
   de eerste code die de knoop-as opnieuw gebruikt, en dus de eerste eerlijke toets of de kern
   echt in de portabele deelverzameling zit. Doe je WP15.1 eerst, dan schrijf je de AST-regels
   op één gebruiker.

Stoppen is op zes plaatsen een geldige uitkomst: na WP13.0, WP13.1, WP14.2, WP14.3, WP15.1 of
WP15.2. Elk laat de suite groen en I1–I8 heel.

---

## 7. Wat we niet doen

- **`optimize` als tiende MCP-tool.** Het gebied maakt de *uitvoer* groter, niet de invoer; een
  graaf hoort niet in een toolargument. Zelfde regel voor de LP-vorm en θ uit WP14: de agent
  krijgt een selectie, een vorm en een θ — nooit het net.
- **De MAA-romp.** Bij dimensie 4 kan hij exact, en dat is een echt voordeel op de
  energieliteratuur, maar WP13.1 levert projecties en zegt dat het projecties zijn. Romp is
  WP16 als iemand hem wil.
- **Een LP in WP14.** Niet omdat een LP verkeerd is, maar omdat hij op deze topologie
  overbodig is — en een solver in het pad breekt I6.
- **cvxpylayers / jaxopt / FFOLayer.** Er is geen LP om door heen te differentiëren. Het haakje
  blijft gedocumenteerd voor als fan-out > 1 wordt; `jaxopt` daarbij vervangen door Optimistix.
- **`slsqp-jax`.** Bestaat, rust op Optimistix, claimt 5k–50k variabelen — maar 6 sterren, één
  auteur, en midden in een rename naar `sqpdax`. Pas relevant als de beslissingsvector per
  knoop is, en dan met gepinde versie en een scipy-referentiecase.
- **Gradiënten door discrete investeringskeuzes.** Zie de kritiek in arXiv:2601.17800 (één
  auteur, preprint, weeg als zodanig): een surrogate loss die continu is *in verwachting* maar
  discontinu in bijna elke realisatie. Enumeratie buiten, continu binnen blijft de vorm.
- **JAX in de default-omgeving**, float32 door de gouden test, en de adjoint als
  8500-getallen-tool aan een agent.
- **V7 als vervanging van θ**, V8 (doorspoeling/chloride), en echte waterschapstopologie.

---

## 8. Openstaande vragen die de bouw niet blokkeren

| # | vraag | interim |
|---|---|---|
| V12 | Is `switch_price_of` monotoon, of wisselt de maatregelverzameling meer dan één keer over de prijsas? | monotoon op 13 gemeten punten; de functie meldt een interval zodra hij het niet is |
| V13 | Is een centimeter drooglegging op de referentiepolder werkelijk in de orde van € 0,14 mln (kantelpunt) of € 1,5 mln (waar het oude antwoord terugkomt)? Dit is een vraag aan Ton en aan een waterschap, niet aan het model. | de prijsas melden, geen punt kiezen |
| V14 | Is "boom → laminaire familie → polymatroid" te bewijzen zoals verwacht? | korte inductie over de boomdiepte; faalt hij, dan vervalt alleen de gewogen vorm naar een LP |
| V15 | Houdt het vaste-puntbudget van 2 iteraties op een echte topologie met lussen? | harde limiet plus een test die faalt bij het raken van het budget |
| V16 | Wat zijn de gewichten voor de gewogen vorm (art. 3.14 Bkl: marginale schade per m³)? | niet verzinnen; gelijk tekort en maximin als expliciet gelabelde proxies, en de band ertussen melden |

---

## 9. Bronnen

Alleen wat in dit document dragend is. Per bron staat of hij is ingezien; de volledige sweep met
markeringen staat in de tweede comment onder issues #30, #31 en #32.

**Bijna-optimale ruimten**

- Laumanns, Thiele, Deb & Zitzler (2002), *Combining convergence and diversity in evolutionary
  multiobjective optimization*, Evolutionary Computation 10(3):263–282 — de herkomst van
  ε-dominantie, en het criterium onder "overlappende kostenintervallen". **Let op:** de eerder
  gebruikte referentie `Gold e.a. (2024), Nature Communications` bestaat niet.
- Chang, Brill & Hopkins (1982), *Use of mathematical models to generate alternative solutions
  to water resources planning problems*, WRR 18(1):58–64 — het waterzusje van Brill e.a. (1982),
  Management Science 28(3):221–235.
- Rosenberg (2015), *Blended near-optimal alternative generation…*, WRR 51(4):2047–2063 — en de
  formulering die het beste zegt waarvoor het gebied dient: het lokt een grotere set
  **ongemodelleerde** kwesties uit. Sinds 2023 drie citaties, alle drie energie; de
  wateropvolging is elf jaar later niet geschreven.
- Lau, Patankar & Jenkins (2024), Environmental Research: Energy 1(4):045004 — de expliciete
  romp loopt vast bij hogere dimensie. Lau e.a. (2025), 2(3):035001 — daarom impliciet.
- Neumann & Brown (2023), iScience 26(5):106702 — ε en kostenonzekerheid gelijktijdig; het
  precedent voor ε uit de prijsband.
- Finke, Weber & Bertsch (2026), *EJOR*, DOI 10.1016/j.ejor.2026.03.032 — de schaduwprijslezing
  onder WP13.0. Finke e.a. (2024), Applied Energy 376:124126 — MGPA: AUGMECON plus MGA, de brug
  naar de ε-constraint-methode (Haimes, IEEE T-SMC SMC-1(3):296–297, 1971).
- Lombardi e.a. (2025), *Joule* 9(11):102144 — vijf treden. **Achter een paywall; de ladder pas
  overnemen na lezen.**

**Verdeling**

- Danna e.a. (2012), *Upward Max Min Fairness*, IEEE INFOCOM — één pad per afnemer geeft
  water-filling; bij meerdere paden is geen combinatorisch algoritme bekend. De scheidslijn.
- Le Boudec (2021), *Rate adaptation, Congestion Control and Fairness: A Tutorial*, EPFL —
  Theorem 1.2.2 (uniciteit), 1.2.3 (bottleneck), 1.2.4 (water-filling bij vaste routing).
- Bertsekas & Gallager, *Data Networks*, 2e ed. 1992, **hoofdstuk 6 "Flow Control", §6.5.2
  "Max-Min Flow Control", p. 524–530** — niet het routing-hoofdstuk.
- Megiddo (1977), *A good algorithm for lexicographically optimal flows in multi-terminal
  networks*, Bull. AMS 83(3) — het lexicografische paper; Megiddo (1974) is een ander paper.
  Fujishige (1980), Math. of OR 5:186–196 (niet ingezien).
- Schrijver, *Combinatorial Optimization*, hoofdstuk 44, §44.2, p. 771–773, Thm 44.3 /
  Cor. 44.3b — Edmonds' greedy op polymatroïden, de basis onder de gewogen vorm.
- Ogryczak & Śliwiński (2007), INOC — de sequentiële aanpak is veilig op een continue
  verzameling en niet op een discrete.
- Landelijk draaiboek waterverdeling en droogte, 29-01-2026, tabel 3.1 (art. 3.14 Bkl); en
  Handleiding verdringingsreeks v2, 26-03-2020. **De reeks staat in het Bkl, niet meer in het
  Waterbesluit.**
- Yates e.a. (2005), Water International 30(4):487–500 — WEAP: Equity Groups, en een binnenlus
  die via schaduwprijzen precies progressive filling doet.
- Baayen e.a. (2016), RTC-Tools 2 — lexicografisch goal programming ís een reeks
  optimalisaties. En Ribasim (Deltares) — een reeks LP's per prioriteit met een fairness-term,
  de directe tegenhanger van WP14.
- Gijsbers, Baayen & ter Maat, *Quick Scan Tool for water allocation in the Netherlands* — de
  norm p ∈ {1, 2, ∞} als vormkeuze.
- Gal & Nedoma (1972), Management Science 18(7):406–422; Nemesch e.a. (2025), arXiv:2501.11544 —
  parametrische min-cost flow kan exponentieel veel regio's hebben; mpLP is voor zover te
  vinden nooit op waterverdeling toegepast.
- Rudberg (2026), Frontiers in Water 8:1803379 — assurance levels; en de bevestiging dat
  verdeling *binnen* een prioriteitsniveau een open vraagstuk is.

**Adjoint**

- JAX-documentatie, `jax.lax.while_loop` (niet reverse-mode differentieerbaar),
  `jax.lax.cummin` (JVP via `associative_scan`), en *Custom derivative rules* (het
  `fixed_point`-voorbeeld). JAX-issue #19498 — parameters in de operator zijn duur.
- `google/jaxopt` — *"no longer maintained nor developed."* Optimistix: `ImplicitAdjoint`,
  `fixed_point`.
- Bolte, Le, Pauwels & Silveti-Falls (NeurIPS 2021), arXiv:2106.04350; Bolte, Pauwels & Vaiter
  (NeurIPS 2022), arXiv:2206.00457; Grazzi, Pontil & Salzo (ICML 2024), arXiv:2403.11687 — de
  niet-gladde impliciete differentiatie waar de klem onder valt.
- Hascoët e.a. (2026), JGR-MLC 3(1), DOI 10.1029/2025JH000760 — 6,8 mln kanalen; **PyTorch**, en
  het werkt doordat LTI geen vast punt nodig heeft. Dat is precies de aanname die onze klem
  breekt, en zo hoort de vergelijking in §7 van het ontwerpdocument te staan.
- Song e.a. (2025), WRR, DOI 10.1029/2024WR038928 — 2.807 train / 4.997 eval, mediane NSE 0,68
  tegen 0,48. Het dichtstbijzijnde precedent voor één adjoint naar duizenden knopen.
- Cardoso-Bihlo & Bihlo (2026), arXiv:2604.07129 (AegirJAX) — sigmoid-masking in plaats van
  booleaanse vlaggen, ghost-cell-padding om niet-differentieerbare control flow te vermijden.
- arXiv:2506.14186 (2025) — de harde klem in de forward, een verzachte in de backward. Achtervang
  als het 0/1-masker de zoektocht laat stotteren.

**Niet gevonden, en dat is zelf een resultaat:** geen literatuur over differentieerbare modellen
of adjoints voor polderpeilbeheer of gemaalregeling (2025–2026); geen toepassing van
bijna-optimale ruimten op water sinds Rosenberg 2015; geen mpLP op waterverdeling; en geen
citeerbare stelling voor "laminaire familie → polymatroid".
