# Bevindingenrapport pakketzoeker — `find_package_given_protection`

**Datum:** 1 september 2026
**Scope:** de pakketzoeker op branch `feat/pakketzoeker-als-tool` (commit 51fbe46): het
invoermodel, de toolfunctie, de uitlegzinnen én de rekenkern (`optimize.py`) waar de tool
op leunt.
**Methode:** adversarieel. Elke claim die de tool in een veldtekst of uitlegzin doet, is
onafhankelijk nagerekend — met roosterzoektochten, tegenproeven op de kern en aanroepen
over HTTP — in plaats van op het antwoord van de tool zelf te vertrouwen. Schemagrenzen
zijn bewust overtreden om te zien wat de runtime dan doet.

Alle JSON-fragmenten zijn de letterlijke `input`; alle Python-fragmenten draaien vanuit de
repowortel met `.pixi/envs/default/bin/python`. De referentiepolder is overal 4000 ha,
3,5 % open water, gemaal 5 m³/s, en de referentiebui T=1000 winter p1a 96 u met
`days_to_discharge=4`, regime R (afgekort: BASE).

---

## 1. Samenvatting

| # | Ernst | Waar | Bevinding |
|---|---|---|---|
| P1 | Blocker | invoermodel | `length_days: 0` crasht met een kale `ValueError` → HTTP 500 |
| P2 | Hoog | invoermodel | Schemagrenzen worden niet afgedwongen: negatieve eisen, negatief tekort en negatieve `max_mix_size` geven HTTP 200 met stil onzinnige antwoorden |
| P3 | Hoog | kern + tool | `max_mix_size: 0` doorzoekt stil álles en meldt tegelijk alle 31 mixen als niet-onderzocht; `-1` onderzoekt níets en meldt `action_infeasible` |
| P4 | Hoog | tool | Peilmarge en bestaande peilopzet als invoer maken het antwoord tot 28 % goedkoper zonder één melding — geen post, geen caveat, niets in de zin |
| P5 | Hoog | uitvoermodel | `missed_by` belooft "minder dan dit is niet te halen", maar is alleen het beste van 31 kosten-geoptimaliseerde punten; een rooster haalt aantoonbaar meer |
| P6 | Hoog | kern + zin | De bovengrens in `ranges` is voor prijsloze maatregelen de zoekgrens, terwijl de zin beweert dat het de prijsband is |
| P7 | Middel | kern + zin | "absent — niet omdat ze te duur zijn maar omdat ze niet bijdragen" is aantoonbaar onwaar zodra het beste pakket prijsloos is |
| P8 | Middel | tool | Engelse uitvoer bevat Nederlandse fragmenten bij een onhaalbare vraag |
| P9 | Middel | tool | `no_measure_needed` levert toch een pakket-object plus vijf `absent`-rollen — "draagt niet bij" voor maatregelen waar niets van gevraagd is |
| P10 | Laag | uitvoermodel | `cost_epsilon` en de vervangingslezing rusten op prijsbanden die nergens in de uitvoer staan; het criterium is niet na te rekenen uit het antwoord |
| P11 | Hoog | tool + descriptions | De `description` breekt met de huisstijl: 2 van de 6 zinnen dragen een getal (losse tools: 2 van 2), en 30 % is lesstof die letterlijk in elke uitvoer herhaald wordt en al in twee andere kanalen staat |
| P12 | Hoog | toegankelijkheid | Het uitvoerschema staat op de draad (137.502 tekens over de toolset) en de budgettoets telt het niet; de pakketzoeker alleen al draagt 21.305 tekens uitvoerschema naast 11.082 invoer |
| P13 | Middel | invoermodel | Drie knoppen bestaan alleen op deze tool (`max_mix_size`, `switch_prices`, `detail`); twee ervan beantwoorden geen waterschapsvraag en één overschrijdt zijn eigen tijdslimiet in precies het geval waarvoor hij bedoeld is |

De rode draad: **de kern rekent goed, maar de laag eromheen belooft meer dan hij waarmaakt
- en zegt het in te veel woorden.**
Drie structurele oorzaken komen terug: (a) `hide_null_branch_and_bound` zet grenzen alleen
in het schema en het bijbehorende validatordeel ontbreekt voor alle zes nieuwe velden;
(b) uitlegzinnen doen universele claims ("de bovenkant is de prijsband", "absent is niet te
duur") die alleen voor geprijsde maatregelen gelden; (c) de tool roept de bestaande
invoer-kant van de prijsloze rapportage (`priceless_posts(input, ...)`) niet aan.

---

## 2. Wat is geverifieerd en werkt

Actief getest en in orde; een regressie hierop zou stil blijven, dus vastgelegd.

**Het anker klopt exact.** Met alleen de inundatie-eis (BASE, `max_dh_total_m: 1.0`) kiest
de zoeker `{afvoeren 2,912 m³/s}` à € 5,590 mln; de losse inverse
`calculate_discharge_given_h` met `delta_h_available: 1.0` geeft 2,9115 m³/s à € 5,590 mln.
De deur verandert het antwoord niet.

**Kosten zijn monotoon in de eis.** Over `max_dh_total_m` van 1,6 naar 0,2 m (met 20 mm
voorraadeis) stijgen de kosten strikt: 5,4 → 6,9 → 8,9 → 11,0 → 13,3 → 17,8 → 26,7 → 53,1
mln, met een navolgbare pakketwissel bij 0,6 m (bergen komt erbij). Geen zaagtand, geen
niet-convergentie.

**Deterministisch.** Twee identieke aanroepen geven byte-gelijke `model_dump()`s.

**Bestaand en extra tellen niet dubbel.** Met `target_level_rise_m: 0.2` adviseert de
zoeker 37,1 cm extra opzet waar hij vanaf nul 57,1 cm adviseert — zelfde eindstand, zelfde
kosten, zelfde `dh_total_m`.

**De tekort-eis werkt op zijn rand.** `max_shortfall_mm: 0` is een geldige vraag en geeft
`{aanvoeren 1,852 m³/s}` met `shortfall_mm: 0.0` en `binding: ["tekort"]`; het
binding-etiket bestaat dus ook voor de derde eis.

**De validators die er wél zijn, zijn idempotent en volledig.** Geen eis → geweigerd met
uitleg; tekort-eis zonder droogte → geweigerd; tekort én tripel → geweigerd als dubbelop;
half tripel → geweigerd met de ontbrekende velden; en de droogte-resolutie overleeft een
tweede validatiegang zonder opnieuw op te zoeken.

---

## 3. Bevindingen

### P1 — `length_days: 0` crasht met een kale ValueError (HTTP 500) — Blocker

```json
{"area_ha": 4000, "discharge_capacity_m3_per_sec": 5, "return_period": 100,
 "max_shortfall_mm": 50, "deficit_mm_per_day": 4, "length_days": 0}
```

Het schema adverteert `minimum: 1`, maar de runtime accepteert 0. `simulate_deficit` krijgt
dan een lege dagenreeks en `numpy` gooit *"zero-size array to reduction operation minimum
which has no identity"* — geen `ModelRetry`, geen `ToolError`, dus over REST een kale 500
en over MCP een onleesbare fout. Gemeten met `TestClient`: HTTP 500.

De patroonafspraak in `hide_null_branch_and_bound` (base_rule_of_thumb.py) is expliciet:
de grens staat in het schema, *de handhaving hoort in een validator met een nette zin*.
Die validator is er voor geen van de zes nieuwe velden met een ondergrens. Nagetoetst: dit
gat is van de pakketzoeker alleen - `RetentionInputGivenH` weigert
`days_to_retain_discharge: -2` met een uitlegzin en `SupplyInputGivenH` weigert
`length_days: 0` en een negatief tekort via `gt`-constraints. Elke bestaande tool handhaaft
zijn grenzen; alleen het nieuwe model niet.

**Status: verholpen (K2).** `enforce_the_advertised_bounds` handhaaft alle zes grenzen
met de betekenis erbij; `length_days: 0` is over HTTP een 422 met de reden in de body, en
de nul-randen (`max_dh_total_m: 0`, `min_storage_mm: 0`, `max_shortfall_mm: 0`) blijven
geldig. P1 en P2 zijn hiermee dicht.

### P2 — schemagrenzen zonder handhaving: stil onzinnige antwoorden — Hoog

Alle negen onderstaande waarden worden geaccepteerd (schema zegt telkens `minimum`):

| invoer | wat er gebeurt | HTTP |
|---|---|---|
| `max_dh_total_m: -0.5` | `problem_infeasible`, met `missed.required: -0.5` als serieus getal | 200 |
| `min_storage_mm: -20` | `no_measure_needed` — een negatieve voorraadeis is "al gehaald" | 200 |
| `deficit_mm_per_day: -4` | een natte "droogte": `shortfall: 0.0`, `no_measure_needed` | 200 |
| `max_shortfall_mm: -5` | geaccepteerd | 200 |
| `days_to_retain_discharge: -2` | geaccepteerd | 200 |
| `max_mix_size: 0 / -1 / 99` | zie P3 | 200 |

Elk van deze is een vraag die geen betekenis heeft, en elk krijgt een antwoord dat er
betekenisvol uitziet. Dat is het gevaarlijkste faaltype van deze toolset — het staat met
zoveel woorden in `one_unit_only` — en het zit hier op zes velden tegelijk.

### P3 — `max_mix_size: 0` zoekt stil alles en rapporteert het tegendeel — Hoog

```json
{"area_ha": 4000, "discharge_capacity_m3_per_sec": 5, "return_period": 100,
 "max_dh_total_m": 1.0, "min_storage_mm": 20, "max_mix_size": 0}
```

Uitkomst: `status: "exact"`, `data.mixes_examined: 31` én `unexplored_mixes` met álle 31
combinaties. De oorzaak is dubbel. In de kern staat `largest = max_mix_size or
len(actions)` (optimize.py, in `optimize`), en `0 or 5` is 5 — nul betekent stilzwijgend
"alles". In de toollaag rekent `_unexplored_mixes` onafhankelijk daarvan
`range(0 + 1, 6)` en meldt alles als niet-onderzocht. Twee lezingen van hetzelfde veld die
elkaar in één antwoord tegenspreken.

Met `max_mix_size: -1` is het erger: `-1 or 5` is −1, de zoeklus draait nul keer,
`mixes_examined: 0`, en het antwoord is `action_infeasible` met 32 "niet-onderzochte"
combinaties — waaronder één lege (`[]`, de combinatie van nul maatregelen). Er is dan
niets onderzocht en de status suggereert dat er iets is geprobeerd.

### P4 — peilmarge en bestaande opzet zijn gratis, en niets meldt het — Hoog

Zelfde eisen, één veld erbij:

```json
{"area_ha": 4000, "percentage_open_water": 3.5, "discharge_capacity_m3_per_sec": 5,
 "return_period": 1000, "time_of_year": "winter", "length_event_hrs": 96,
 "name_rainfall_pattern": "p1a", "days_to_discharge": 4, "rainfall_regime": "R",
 "max_dh_total_m": 1.0, "min_storage_mm": 20, "level_margin_m": 0.30}
```

| | kosten | priceless-posten | caveat of zin over de marge |
|---|---|---|---|
| zonder marge | € 10,97 mln | `peilopzet` | — |
| met 30 cm marge | **€ 7,86 mln** | `peilopzet` | **geen** |

Achtentwintig procent goedkoper, en het woord peilmarge komt in het hele antwoord niet
voor. Dit is letterlijk de faalmodus die voor de losse maatregeltools is gedicht met
`_level_margin_post` in `base_rule_of_thumb.py` — het commentaarblok daar noemt als
voorbeeld "van 9,2 naar 5,1 miljoen zonder dat er iets in het antwoord staat". De
pakketzoeker roept `priceless_posts(input, ...)` echter nergens aan; zijn eigen
`PRICELESS_COST` dekt alleen de maatregelen die de zóeker kiest.

Zelfde gat voor de bestaande opzet: met `target_level_rise_m: 0.2` meldt de post alleen de
extra 37,1 cm; de staande 20 cm — die evengoed drooglegging kost en in `dh_total_m`
meetelt — staat nergens.

### P5 — `missed_by` belooft een ondergrens die het niet is — Hoog

De veldtekst zegt: *"Dit is de kleinste overschrijding over alle onderzochte combinaties:
minder dan dit is met deze maatregelen niet te halen."* De tweede helft is onwaar.

De 31 pakketten waaruit `reached` wordt gelezen zijn door SLSQP geoptimaliseerd op
**kosten onder de eisen** — niet op het minimaliseren van de overtreding wanneer de eisen
onhaalbaar zijn. Tegenproef op de kern (BASE, alleen `max_dh_total_m: 0.1`):

```python
r = optimize(state, storm, Constraints(max_dh_total_m=0.1))
min(p.dh_total_m for p in r.packages)   # -> 0.1000 (de eis wordt hier nog nét gehaald)
# ruw rooster over dezelfde zoekruimte, 216 punten:
# afvoeren op 19 m3/s geeft dh_total_m = 0.0000
```

Een kaal rooster haalt 0,000 m waar de pakketverzameling 0,100 m als laagste draagt. Bij
een echt onhaalbare vraag (`max_dh: 0.05` + `min_storage: 500`) meldt `missed` dus een
"kleinste overschrijding" (0,042 m) waarvan niet vaststaat dat hij de kleinste is — de
zin "minder is niet te halen" maakt van een steekproef een bewijs. De eerste helft van de
veldtekst is correct; de belofte erachter moet weg, of de kern moet bij onhaalbaarheid
een aparte overtreding-minimaliserende doorrekening doen.

### P6 — de bovengrens in `ranges` is voor prijsloze maatregelen de zoekgrens — Hoog

De uitlegzin (en de veldtekst van `magnitude_max`) beweert: *"De bovenkant is wat er
binnen de prijsband nog past; daarboven koopt het niets meer."* Voor prijsloze maatregelen
is de bovenkant in werkelijkheid de **zoekgrens** van de kern:

| aanroep | gemelde range | wat de bovengrens werkelijk is |
|---|---|---|
| BASE + `min_storage_mm: 20` | peilopzet 0,571 – **1,0 m** | `MAX_TARGET_LEVEL_RISE_M = 1.0` (actions.py) |
| BASE + `max_shortfall_mm: 50` (+droogte) | aanvoeren 1,08 – **20 m³/s** | `AanvoerenAction.upper_bound(state) = 20.0` |

Een inlaat van 20 m³/s op 4000 ha is 5 l/s/ha — het tienvoudige van wat de eis vraagt —
en wordt gepresenteerd als "past binnen de prijsband". Het mechanisme: `sweep_measure`
laat een maatvoering toe zolang de eisen gehaald worden én de kosten binnen het budget
blijven; een prijsloze maatregel kost niets, dus alleen de zoekgrens stopt hem. De zin
generaliseert een eigenschap van geprijsde maatregelen naar alles.

### P7 — "absent is niet te duur" is onwaar zodra het beste pakket prijsloos is — Middel

BASE + `min_storage_mm: 20`. Het antwoord: peilopzet forced; vasthouden, bergen, afvoeren
en aanvoeren absent, met de zin *"niet omdat ze te duur zijn maar omdat ze niet
bijdragen"*. Tegenproef op de kern, met de opzet vast op zijn gekozen 0,571 m:

| bergen erbij | voorraad | kosten |
|---|---|---|
| 0 ha | 20,0 mm | € 0 |
| 500 ha | **91,4 mm** | € 67,5 mln |
| 1000 ha | 162,8 mm | € 135,0 mln |

Bergen draagt hier dus fors bij aan precies de gestelde eis. Hij is absent omdat het
budget voor het bijna-optimale gebied `best.cost × (1+ε) = 0` is — elk bedrag groter dan
nul valt erbuiten. Dat is de definitie van "te duur", en de zin beweert het omgekeerde.
De rolsemantiek zelf (lidmaatschap van het gebied) is verdedigbaar; de universele
duiding *"absent = draagt niet bij"* in `MeasureRole`, `describe_region` en de veldtekst
is het niet.

### P8 — Engelse uitvoer met Nederlandse fragmenten — Middel

`language: "en"` + onhaalbare eisen geeft:

> *"No combination of these five measures meets the requirements at the same time.
> Closest miss: **inundatie komt 0.04215 tekort, voorraad komt 1.531 tekort**."*

In `_describe_no_package` wordt de opsomming (`listed`) vóór de taalkeuze opgebouwd, in
het Nederlands, en daarna in beide taaltakken gebruikt. De `missed`-veldwaarden zelf
(`requirement: "inundatie"`) zijn ook Nederlandstalig in een Engels antwoord; dat is
consistent met `measure_nl` elders, maar de zin hoort één taal te zijn.

### P9 — `no_measure_needed` draagt een pakket en vijf `absent`-rollen — Middel

BASE + `max_dh_total_m: 5.0` geeft naast de juiste status en zin ook: een gevuld
`best`-object (lege maatregelenlijst, `feasible: true`, kosten € 0) en vijf ranges met
rol `absent`. Een agent die — zoals de handleiding vraagt — `ranges` naast `best` leest,
ziet vijf keer "draagt niet bij" voor maatregelen waarvan niets gevraagd is. Er viel hier
niets bij te dragen; de velden horen leeg te zijn of de rol hoort een eigen waarde te
hebben voor "niet van toepassing".

### P10 — het epsilon-criterium is niet na te rekenen uit het antwoord — Laag

`cost_epsilon: 0.094` wordt gemeld als afgeleid getal ("de relatieve breedte van de
prijsband over het geprijsde deel"), maar die band — `priced_cost_range`, hier
€ 10,63–11,65 mln — staat nergens in de uitvoer: `best.cost_range` is bij een prijsloze
maatregel bewust `null`, en een veld voor het geprijsde deel ontbreekt. Hetzelfde geldt
voor `indistinguishable_as_replacement`, dat rust op overlap van
`replacement_cost_range`-banden die evenmin worden meegegeven. Voor een toolset die
narekenbaarheid als bestaansreden heeft, is "dit getal komt uit een band die u niet mag
zien" een gat: de agent kan het criterium citeren maar niet controleren.

---

## 4. Eerder op deze branch gevonden en al verholpen

Voor de volledigheid — deze zaten in dezelfde review-cyclus en zijn al gecommit:
een volledig prijsloos pakket werd als "kost 0,0 miljoen euro" beschreven (804c00f);
`target_level_rise_m` ontbrak als bestaande stand, waardoor een al opgezette polder een
normoverschrijdend advies kreeg (d125d82); twee handleidingsecties stonden in de
verkeerde module (51fbe46); `near_optimal` begon met een kopie van het antwoord;
`switch_prices` was ongetest; en de route-toets miste twee tools (5345224, 7cfd3ec).

## 5. Prioritering

P1 en P2 zijn één fix: de ontbrekende validatorhelft van het bestaande
grenzen-in-schema-patroon, voor alle zes velden tegelijk, met de nette zinnen die de rest
van het systeem al heeft. P3 vraagt daarnaast één regel in de kern (`max_mix_size`
expliciet op `None` toetsen in plaats van op waarheid). P4 is het aanroepen van de
bestaande `priceless_posts(input, ...)` plus een post voor de staande opzet. P5–P7 zijn
teksten die minder moeten beweren óf uitvoer die meer moet dragen — daar hoort een keuze,
geen pleister. P9 en P10 zijn kleine modelwijzigingen. P13 vóór P12 oppakken: twee knoppen schrappen
verkleint het uitvoerschema vanzelf, en daarna pas is het zinvol de budgettoets het hele
draadformaat te laten tellen.

### P11 — de description is proza geworden waar de huisstijl feiten-met-getallen is — Hoog

De tien maatregeltools bouwen hun `description` uit één sjabloon per vraagsoort
(`describe_inverse` / `describe_forward` in descriptions.py), en in dat sjabloon draagt
**elke zin een getal**: *"Om de stijging op 100 cm te houden is 2,9 m³/s nodig. Zonder
maatregel is de stijging 170 cm, dus dat is een verlaging van 70 cm."* Ook de
statusvarianten zijn getaldragend — bij `no_measure_needed` staat er *"de stijging is
66 cm en dat blijft al onder de 100 cm"*.

Gemeten op dezelfde casus (BASE, twee eisen):

| | tekens | zinnen | zinnen met een getal |
|---|---|---|---|
| losse tool (`discharge_given_h`) | 227 | 2 | **2 van 2** |
| pakketzoeker | 630 | 6 | **2 van 6** |

Van de pakketzoeker-description is bovendien 30 % (192 tekens, drie zinnen) letterlijk
identiek tussen twee verschillende vragen — het is lesstof, geen antwoord: *"De onderkant
is wat de eis vraagt - daaronder wordt de eis niet gehaald. De bovenkant is wat er binnen
de prijsband nog past; daarboven koopt het niets meer."* Diezelfde les staat al in twee
andere kanalen: in de veldbeschrijvingen van `MeasureRangeReading` (het schema) en in de
`read_me`-module `pakketzoeker`. Drie kanalen met dezelfde uitleg is precies wat het
progressive-disclosure-ontwerp van deze toolset wil voorkomen: de description hoort de
clou te dragen en de uitleg hoort opvraagbaar te zijn.

Twee verzwarende details. Ten eerste is een van de vaste leszinnen de zin die P6 en P7
onwaar bewijzen — de les die elke keer wordt herhaald, klopt niet eens altijd. Ten tweede
is de statuszin van de pakketzoeker bij `no_measure_needed` getalloos ("Het gebied haalt
de eisen al zoals het er nu voor staat"), terwijl het huissjabloon voor dezelfde status
twee getallen draagt en `data.dh_without_measure_m` gewoon beschikbaar is — de lezer
krijgt advies ("ga na of de eis is wat je bedoelde") in plaats van de twee getallen
waarmee hij dat zelf kan nagaan.

Herkomst, voor de eerlijkheid: `describe_region` en `describe_step_cost_plateau` zijn
gedeelde machinerie die al op main stond — maar geen enkele tool gebruikte ze; ze
bestonden alleen in tests. De pakketzoeker maakt ze voor het eerst gebruikerszichtbaar,
en de leszinnen erin zijn dus nooit als antwoordtekst beoordeeld. De drie takken die de
pakketzoeker daarnaast zelf schrijft (`_describe_no_package`, de lege-pakketzin, de
volledig-prijsloze zin) zijn handgeschreven NL/EN-paren buiten elk sjabloon om - de enige
plek in de toolset waar dat zo is.

De richting is daarmee ook duidelijk: één getaldragend sjabloon per status, in
descriptions.py naast de bestaande twee; de vaste lessen eruit (ze staan al in schema en
handleiding); en het epsilon-voorbehoud als kort zinsdeel mét het getal in plaats van als
alinea. Het plan (§5.3) vroeg om "het criterium benoemd houden in de uitvoer" - dat kan
in een veld, het hoeft geen proza per antwoord te zijn.

**Status: verholpen (K3), samen met de tekstdelen van P5, P6, P7, P8 en P9.** Drie
statussjablonen naast `describe_inverse`; twee structurele bewakers (geen gedeelde zin
langer dan 40 tekens tussen twee antwoorden, geen zin zonder getal in een
`exact`-antwoord) plus een taalbewaker; `magnitude_max_source` zegt per interval of de
bovengrens prijsband, eis of zoekgrens is; `absent` claimt geen reden meer; de
vervangingslezing is stilte tenzij de rangorde verandert; en `no_measure_needed` draagt
zijn twee getallen en een lege `ranges`. De dure paden van P5 en P7 blijven open (§6, S1).

### P12 — de budgettoets bewaakt de helft van wat er op de draad staat — Hoog

`test_toegankelijkheid` telt per tool naam + description + **invoer**schema. FastMCP zet
echter ook het **uitvoer**schema in elke tooldefinitie, en dat is over de toolset gemeten
groter dan alles wat de toets bewaakt:

| | invoerschema's | uitvoerschema's |
|---|---|---|
| toolset totaal | 94.766 tekens | **137.502 tekens** |
| pakketzoeker | 11.082 | **21.305** |

Wat een agent hiervan werkelijk betaalt hangt van de client af — niet elke client geeft
het uitvoerschema aan het model door — maar de toets beweert een contextbudget te bewaken
en ziet minder dan de helft van de definitie. Per tool gerekend is de pakketzoeker met
invoer + uitvoer + description ≈ 33.800 tekens ruim twee keer het per-tool-budget van
16.000; de zes maatregeltools zitten elk rond 18.500 in plaats van de getelde ~7.000.
Het uitvoerschema van de pakketzoeker is het grootste van de toolset, en het mechanisme is
gemeten: FastMCP levert het schema **gederefereerd** af - geen `$ref`, elk hergebruik van
een genest model dupliceert zijn volledige tekst. `PackageReading` (11 beschrijvingen)
staat er zo vier keer volledig in (`best`, `near_optimal`,
`indistinguishable_as_replacement`, `packages`): 108 veldbeschrijvingen op de draad, samen
13.218 tekens, 62 % van het schema.

Het antwoord zelf is overigens níet het probleem: de gewone payload is 3.446 tekens tegen
2.137 voor een losse tool — factor 1,6 voor een veel grotere vraag — met 7 van de 15
topvelden leeg. Het gewicht zit in het schema en in het proza (P11), niet in de data.

### P13 — drie knoppen die alleen deze tool heeft, en twee horen er niet — Middel

De dertig invoervelden vallen uiteen in: 19 gedeelde routine (oppervlak in 2 eenheden,
gemaal in 5, de bui-vorm in 7, de droogte in 5), 4 gebiedstoestand, 3 eisen — de
eigenlijke vraag — 1 taal, en **3 knoppen die nergens anders bestaan**: `max_mix_size`,
`switch_prices` en `detail`.

* **`max_mix_size`** beantwoordt geen vraag die een waterschap stelt. "Wat als ik maar
  één maatregel mag nemen" is een echte vraag, maar het antwoord daarop staat al in
  `detail=true` (alle 31 combinaties, inclusief de losse). De knop veroorzaakte P3, kost
  een uitvoerveld (`unexplored_mixes`), een statussubtiliteit
  (`action_infeasible`-bij-afkap) en een handleidingsalinea. Kandidaat om te schrappen.
* **`switch_prices`** overschrijft het ontwerp van de kern: de docstring van
  `switch_price_of` zegt letterlijk *"Dat is geen tool maar een analyse, en hij hoort dus
  niet in een toolaanroep."* De vlag zet hem tóch in een toolaanroep, en hij loopt met
  een droogte-eis over de 120 s — precies het geval waarin aanvoeren prijsloos is en de
  omslagprijs interessant wordt. Een knop die stuk gaat op het moment dat je hem nodig
  hebt. Kandidaat om te schrappen (en de analyse als notebook of losse vraag te laten).
* **`detail`** is verdedigbaar (de sweep-informatie zonder tweede tool, plan §5.3), maar
  is met 11.853 tekens payload het duurste antwoord van de toolset.

Schrappen van de eerste twee haalt ook `unexplored_mixes` en `switch_prices` (met het
hele `SwitchPriceReading`-model, 8 velden) uit het uitvoerschema — P3 verdwijnt dan als
klasse, en P12 wordt kleiner.

Wat dit rapport niet herhaalt: de vraag of peilmarge een maatregel in de zoekruimte hoort
te zijn. Die staat, met metingen, in issue #68.

---

## 6. Convergentie en spanningen - het voorwerk voor het plan

De dertien bevindingen zijn geen dertien fixes. Vier ingrepen dekken er elf, en de
overige twee vragen eerst een besluit. Daarnaast zitten er vijf plekken waar bevindingen
elkaar tégenwerken; wie die niet eerst uit elkaar trekt, bouwt het volgende rapport.

### Vier convergentiepunten

**K1 - eerst het mes: de knoppen (P13 → P3, deel van P12).** `max_mix_size` en
`switch_prices` schrappen laat P3 als klasse verdwijnen (er valt niets meer af te kappen
en dus niets verkeerd te rapporteren), haalt `unexplored_mixes` en het hele
`SwitchPriceReading`-model uit het uitvoerschema, en schrapt een handleidingsalinea plus
de `action_infeasible`-subtiliteit. Dit moet éérst, omdat elke andere volgorde werk
oplevert dat daarna wordt weggegooid: validators voor een veld dat verdwijnt, sjablonen
voor een status die niet meer bestaat, budgetten voor een schema dat nog krimpt.

**K2 - de validatorhelft (P1 + P2).** Eén validatorblok in `OptimizeInput`, naar het
bestaande huispatroon. Het gat is aantoonbaar lokaal - elke andere tool handhaaft al -
dus dit raakt geen gedeelde code. Let op dat het huis twee patronen kent: de uitlegzin in
een validator (retention) en het kale `gt=0` (supply, geeft de ruwe pydantic-dump die
`test_invalid_input_gives_422` vastlegt). Kies er een en noem de keuze; de
`hide_null_branch_and_bound`-docstring pleit voor de eerste.

**K3 - één sjabloonherbouw (P5-tekstdeel, P6-tekstdeel, P7-tekstdeel, P8, P9, P11).**
Zes bevindingen zijn samen één ontwerpbeslissing: de description wordt een getaldragend
sjabloon per status in `descriptions.py`, naast `describe_inverse` en `describe_forward`,
per taal opgebouwd zoals die twee dat al doen (dat lost de taalmix vanzelf op). De
universele leszinnen vervallen - ze staan al in het schema en in de handleiding - en
daarmee vervallen ook de zinnen die P6 en P7 onwaar bewijzen. `no_measure_needed` krijgt
zijn twee getallen (de stijging, en de grens waar die al onder blijft), naar het
voorbeeld dat het huissjabloon voor die status al geeft.

**K4 - het antwoord draagt wat er speelt (P4 + P10).** De bestaande
`priceless_posts(input, ...)` aanroepen (peilmarge, staande opzet), een post voor wat de
zoeker aan bestaande context meekreeg, en het geprijsde-deel-interval als veld naast
`cost_epsilon`. Dit is de volledigheidskant: geen tekst, maar velden.

### Vijf spanningen, bewust uit elkaar te trekken

**S1 - tekst verzwakken of kern versterken (P5, P7).** Beide bevindingen hebben een
goedkoop pad (de claim schrappen: "kleinste overschrijding over de onderzochte
combinaties", punt) en een duur pad (de claim waarmaken: een
overtreding-minimaliserende doorrekening per eis bij onhaalbaarheid; een echte
draagt-niet-bij-diagnose door de sweep ook met oneindig budget te draaien). Het goedkope
pad hoort in de sjabloonherbouw (K3), het dure pad is kernwerk met eigen tests en een
eigen afweging. Niet mengen: eerst waar worden, dan pas sterker worden.

**S2 - narekenbaarheid tegen contextkosten (P10 ↔ P12).** K4 voegt velden toe aan
precies het schema dat P12 te groot noemt. De volgorde lost dit op: eerst K1 (schema
krimpt met een heel model), dan K4 (er komen één a twee velden bij), dán pas meten en
het budget vastzetten. Wie het budget eerst vastzet, maakt van elke
volledigheidsverbetering een budgetgevecht.

**S3 - analyse tegen tool (`switch_prices`).** De kern zegt zelf dat de omslagprijs geen
toolaanroep hoort te zijn; het plan (§5.3) beloofde hem juist "ingevouwen" in de uitvoer.
Die twee kunnen niet allebei waar zijn. Het voorstel van dit rapport - schrappen, de
analyse naar het notebook - is een plánwijziging en hoort als zodanig besloten te worden,
niet stil in een fix-commit. Het verhaal zelf (geen prijs is niet gratis, en bij welke
prijs het antwoord kantelt) blijft; alleen het kanaal verandert.

**S4 - pakketzoeker-scope tegen toolsetbreed.** Twee dingen uit dit rapport zijn groter
dan de pakketzoeker: de budgettoets die het uitvoerschema van álle tools niet ziet
(P12: 137.502 tekens onbewaakt), en de sjabloonmachinerie in `descriptions.py` die
gedeelde code is. De branch die de pakketzoeker fixt moet niet stil een toolsetbrede
bewakingswijziging meenemen; P12 verdient een eigen issue met zijn eigen meting per tool,
nádat K1 de grootste post heeft verkleind.

**S5 - het uitvoerschema is een kanaal én een kostenpost.** De veldbeschrijvingen in het
uitvoerschema zijn hoe een agent het antwoord leert lezen; strippen is dus geen fix maar
het opheffen van een kanaal. Wat wél kan: de duplicatie te lijf (FastMCP inline-t elk
hergebruikt model volledig, dus een slanker leesmodel voor de drie lijstvelden scheelt
drie keer elf beschrijvingen), en accepteren dat een pakketvraag een groter schema draagt
dan een maatregelvraag - mits de budgettoets dat dan ook eerlijk telt. Dit besluit hoort
bij S4, niet bij deze branch.

### De volgorde die hieruit volgt

K1 (het mes) → K2 (de validators) → K3 (de sjablonen) → K4 (de volledigheid), elk apart
te toetsen; daarna S3 als planbesluit vastleggen en S4 als eigen issue openen. S1-duur
(kern versterken) alleen bij gebleken behoefte, als eigen werkpakket.
