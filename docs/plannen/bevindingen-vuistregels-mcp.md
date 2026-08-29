# Bevindingenrapport — Vuistregels-TEST MCP

**Datum:** 26 augustus 2026
**Scope:** alle 11 tools van de `Vuistregels-TEST` MCP server
**Methode:** 28 aanroepen — round-trips, eenheidskruisproeven, randstatussen, topologiefouten, conflicterende invoer
**Reviewer:** Claude (Opus 5), in opdracht van Mattijn van Hoek

---

## Samenvatting

De rekenkern is solide. Round-trips sluiten exact, eenheidsconversies kloppen over alle
zeven invoereenheden, en de `sensitivity`-tabel blijkt een echte herberekening in plaats
van een linearisatie. Op meerdere niet-triviale punten is het fysische gedrag correct:
volumebehoud, het binnenoptimum bij vasthouden, en de wettelijke ordening van de
verdringingsreeks.

De bevindingen zitten vrijwel allemaal in de **laag tussen de kern en de caller**: velden
die iets anders betekenen dan ze suggereren, invoer die stil wordt genegeerd, en beloftes
uit de handleiding die de uitvoer niet nakomt. Dat is precies de laag die ertoe doet bij
een MCP die door een taalmodel wordt aangeroepen, omdat een caller geen mogelijkheid heeft
die stilte op te merken.

| ID | Bevinding | Ernst |
|---|---|---|
| V-01 | `theta_steps` spreekt het hoofdantwoord tegen | **Hoog** |
| V-02 | Conflicterende eenheden worden stil genegeerd | **Hoog** |
| V-03 | `language: "en"` vertaalt alleen `description` | Midden-hoog |
| V-04 | Schema en validatie spreken elkaar tegen bij `delta_area` | Midden |
| V-05 | `priceless` uit de handleiding ontbreekt in de uitvoer | Midden |
| V-06 | Voorbij het binnenoptimum blijft `status: exact` | Midden |
| V-07 | `measure.delta` betekent iets anders in de twee supply-tools | Midden |
| V-08 | `sensitivity.note` is ambigu bij twee `null`-kolommen | Midden |
| V-09 | Cascade lekt volle float-precisie | Laag |
| V-10 | `binding_node` kiest stil uit gelijkwaardige kandidaten | Laag |
| V-11 | Cascade mist `status` en `sensitivity` | Laag |
| V-12 | Numerieke ruis in `shortfall_mm` en `days_until_buffer_empty` | Laag |
| V-13 | Foutmeldingen inconsistent; Pydantic-internals lekken | Laag |
| V-14 | Supply-uitvoer dupliceert zes velden | Laag |
| V-15 | `cost` blijft gevuld bij `action_infeasible` | Laag |
| V-16 | Afronding in `description` botst met `measure.delta` | Laag |
| V-17 | `language` lekt in elk `theta_steps`-object | Cosmetisch |

---

## V-01 — `theta_steps` spreekt het hoofdantwoord tegen

**Ernst:** Hoog · **Tool:** `calculate_allocation_given_shortage`

### Reproductie

```json
{"input": {
  "available_source_volume_m3": 2000000,
  "length_days": 30,
  "nodes": [
    {"name": "veenkade",         "area_ha": 300,  "deficit_mm_per_day": 4, "category": 1, "intake_capacity_m3_per_sec": 0.5, "draws_from": "boezem"},
    {"name": "drinkwaterinname", "area_ha": 500,  "deficit_mm_per_day": 4, "category": 2, "intake_capacity_m3_per_sec": 1.0, "draws_from": "boezem"},
    {"name": "landbouwpolder",   "area_ha": 4000, "deficit_mm_per_day": 4, "category": 4, "intake_capacity_m3_per_sec": 1.5, "draws_from": "boezem"},
    {"name": "boezem",           "area_ha": 8000, "deficit_mm_per_day": 0, "category": 4, "intake_capacity_m3_per_sec": 10.0}
  ]
}}
```

### Waargenomen

`theta` = 0,347 en `coverage_per_category["4"]` = **0,2167**.

Diezelfde theta valt in `theta_steps[2]`, interval `[0,167 – 0,842]`, en dat object meldt
`coverage: {"4": 0.81}`. Een tweede run met `available_source_volume_m3: 3000000`
(theta = 0,521, werkelijke coverage 0,425) valt in exact dezelfde stap, die opnieuw 0,81
meldt. De `theta_steps` zijn identiek in beide runs.

### Analyse

De `coverage` in een stap is kennelijk de waarde op de **bovengrens** van het interval, niet
de waarde *binnen* het interval. Dat is nergens gedocumenteerd. De 0,81 is verklaarbaar en
op zichzelf correct: bij θ ≈ 0,84 wordt de inlaat van de landbouwpolder bindend
(1,5 m³/s × 30 d = 3,89 Mm³ = 81 % van een vraag van 4,8 Mm³).

Twee dingen maken dit ernstig:

1. De caveat moedigt actief aan het veld te gebruiken: *"De trap in `theta_steps` is daarom
   bruikbaarder dan het ene getal."* Een caller die die instructie opvolgt, rapporteert
   81 % waar 22 % het antwoord is — een factor bijna vier, in een verdelingsvraag met
   juridische lading.
2. `theta_steps[2]` en `theta_steps[3]` zijn identiek in `coverage` én in
   `binding_category` (beide 4). Juist tussen die twee slaat de aard van de binding om van
   *beschikbaarheid* naar *capaciteit* — van een rantsoeneringsvraag naar een
   kunstwerkvraag. Dat onderscheid is de kern van wat deze tool te vertellen heeft, en het
   is uit de trap niet af te lezen.

### Suggestie

- Documenteer expliciet dat `coverage` de waarde op `theta_high` is, of geef per stap
  `coverage_at_low` en `coverage_at_high`.
- Voeg `binding_is_capacity_not_availability` per stap toe.
- Voeg een `contains_current_theta: true` vlag toe op de stap waarin de casus valt, zodat
  een caller niet zelf hoeft te matchen.
- Overweeg aangrenzende stappen met identieke coverage én binding samen te voegen, tenzij
  de aard van de binding verschilt — dan is dát juist het verschil dat de stap rechtvaardigt.

---

## V-02 — Conflicterende eenheden worden stil genegeerd

**Ernst:** Hoog · **Tool:** alle acht maatregeltools

### Reproductie

```json
{"input": {
  "area_ha": 4000, "area_m2": 99000000,
  "discharge_capacity_m3_per_sec": 5, "discharge_capacity_l_s_ha": 99,
  "delta_h_available": 1.0, "return_period": 100,
  "percentage_open_water": 3.5, "time_of_year": "winter",
  "days_to_discharge": 3, "length_event_hrs": 96,
  "name_rainfall_pattern": "p1c", "rainfall_regime": "R"
}}
```

### Waargenomen

Uitvoer **exact identiek** aan de baseline zonder de conflicterende velden: 68,18 ha,
`dh_reference_m` 1,49. Geen melding, geen `assumptions`-regel, geen waarschuwing. De
genegeerde waarden zijn niet subtiel — 99 000 000 m² is 9900 ha, en 99 l/s/ha is twintig
keer de bovenkant van de gangbare band.

### Analyse

Er bestaat een prioriteitsvolgorde (`_ha` wint van `_m2`; `_m3_per_sec` wint van
`_l_s_ha`), maar die is voor de caller onzichtbaar. Dit is het gevaarlijkste faaltype dat
een tool kan hebben: een plausibel, intern consistent, volledig fout antwoord zonder enig
signaal. Een taalmodel dat twijfelt tussen twee eenheden en er "voor de zekerheid" twee
invult, krijgt geen correctie.

Het staat bovendien haaks op de toon van de rest van het systeem, dat elders juist
uitzonderlijk expliciet is over wat het heeft aangenomen.

### Suggestie

Weiger de aanroep met een melding in de stijl van de bestaande foutteksten, bijvoorbeeld:
*"Geef de gemaalcapaciteit in één eenheid op; er zijn er twee ingevuld
(`discharge_capacity_m3_per_sec`=5 en `discharge_capacity_l_s_ha`=99)."*

Een lichter alternatief dat ook de rest van de invoer transparant maakt: een
`input_echo`-blok met de daadwerkelijk gebruikte waarden, genormaliseerd naar één eenheid.

---

## V-03 — `language: "en"` vertaalt alleen `description`

**Ernst:** Midden-hoog · **Tool:** alle tools met een `language`-veld

### Reproductie

```json
{"input": {"area_ha": 4000, "area_available_ha": 0, "discharge_capacity_m3_per_sec": 5,
           "return_period": 100, "percentage_open_water": 3.5,
           "time_of_year": "winter", "language": "en"}}
```

### Waargenomen

`description` komt in het Engels: *"With 0.00 ha of additional open water…"*. Maar
`assumptions[].why_it_matters` en **alle** `caveats` blijven Nederlands.

### Analyse

De handleiding stelt alle drie verplicht in de terugkoppeling: *"`assumptions` … `sensitivity`
… `caveats`. Alle drie horen in je terugkoppeling."* Een Engelstalige gebruiker krijgt dus
één Engelse zin met een Nederlandse motivering eronder, of de caller laat de caveats weg —
en dan valt precies de relativering weg die het model eerlijk houdt.

Dit botst met het ontwerpprincipe dat `read_me` zelf expliciet uitspreekt bij het
*ontbreken* van een `language`-veld: *"een veld dat wordt geaccepteerd maar genegeerd is
erger dan geen veld."* Half toepassen is een derde categorie, en waarschijnlijk de
vervelendste van de drie, omdat de gedeeltelijke vertaling suggereert dat de rest ook
gedekt is.

### Suggestie

Vertaal `why_it_matters` en `caveats` mee, of documenteer in het schema van `language` dat
het alleen `description` betreft.

---

## V-04 — Schema en validatie spreken elkaar tegen bij `delta_area`

**Ernst:** Midden · **Tool:** `calculate_retention_given_area`

### Reproductie

```json
{"input": {"area_ha": 4000, "delta_area_ha": -5000, "discharge_capacity_m3_per_sec": 5,
           "return_period": 100, "percentage_open_water": 3.5, "time_of_year": "winter"}}
```

### Waargenomen

Foutmelding: *"delta_area_ha is het areaal dat voor retentie wordt ingericht en kan niet
negatief zijn."*

Het schema van datzelfde veld zegt echter: *"Change in area in hectares for retaining water
on land (positive for increase, **negative for decrease**)."* Idem voor `delta_area_m2`.

### Analyse

Het schema nodigt uit tot een aanroep die per definitie faalt. Een caller die het
tooldescription serieus neemt, doet vroeg of laat precies dit.

Ter contrast: bij `delta_discharge_capacity_m3_per_sec` is de beschrijving wél correct
("Extra gemaalcapaciteit"), en de foutmelding bij een negatieve waarde is voorbeeldig —
zie het kopje "Wat goed werkt" hieronder.

### Suggestie

Pas de veldbeschrijving aan naar de werkelijkheid, en zet `minimum: 0` in het schema zodat
de validatie al bij het opstellen van de aanroep bijt in plaats van erna.

---

## V-05 — `priceless` uit de handleiding ontbreekt in de uitvoer

**Ernst:** Midden · **Tool:** alle maatregeltools

### Reproductie

```json
{"input": {"area_ha": 4000, "delta_h_available": 1.0, "discharge_capacity_m3_per_sec": 5,
           "return_period": 100, "percentage_open_water": 3.5, "time_of_year": "winter",
           "level_margin_m": 0.3, "target_level_rise_m": 0.2}}
```

### Waargenomen

De peilmarge werkt inhoudelijk: `dh_reference_m` daalt van 1,49 naar 1,267 m en de
benodigde berging van 68,18 naar 37,52 ha. Maar er is **geen `priceless`-veld** in de
respons. `cost` (€5,07 mln) dekt alleen het bergen.

### Analyse

De handleiding belooft: *"peilopzet, peilmarge en aanvoeren hebben geen prijs. Ze staan in
`priceless` en niet op nul. Wat ze kosten is drooglegging, bedrijfsvoering en water — noem
dat, en niet een bedrag."*

Dat is een goed ontworpen mechanisme, en precies de reden waarom het gemis opvalt: zonder
`priceless` blijft er niets in de uitvoer staan dat de caller eraan herinnert dat die
30 cm peilmarge wél iets kost — namelijk marge tot inundatie en bedrijfsvoering. Het risico
is dat een peilmarge als gratis winst wordt gepresenteerd, want ze verlaagt de kosten
zichtbaar en verhoogt niets zichtbaars.

### Suggestie

Voeg `priceless` toe zodra `level_margin_m` of `target_level_rise_m` niet-nul is, of zodra
de maatregel aanvoeren is, met per post de niet-monetaire prijs.

---

## V-06 — Voorbij het binnenoptimum blijft `status: exact`

**Ernst:** Midden · **Tool:** `calculate_retention_given_area`

### Reproductie

Twee aanroepen, verder identiek (4000 ha, 5 m³/s, T=100, winter, 3,5 % open water,
`days_to_discharge` 3, `days_to_retain_discharge` 2, `length_event_hrs` 96, p1c, R):

| `delta_area_ha` | `dh_with_measure_m` | `cost` | `status` | `limit_reason` |
|---|---|---|---|---|
| 2645 (= optimum) | 1,163 | €6,35 mln | `action_infeasible` | `measure_optimum` |
| 3800 | **1,212** | **€9,12 mln** | `exact` | `none` |

### Analyse

Bij 3800 ha betaalt de gebruiker 44 % meer voor een 5 cm **slechter** resultaat, en niets
in `status` of `limit_reason` wijst daarop. Het is uitsluitend af te leiden uit de
combinatie `magnitude_optimum_kind: "interior"` en `magnitude_at_optimum_ha` (2645) <
`measure.after` (3800) — twee velden vergelijken die de handleiding niet als paar
introduceert.

Het gedrag is verdedigbaar: de vraag was "wat doet deze maatvoering", en dat antwoord ís
exact. Maar het binnenoptimum bij vasthouden is nu juist het meest contra-intuïtieve
resultaat dat dit model produceert, en dus het punt waar een expliciete vlag de meeste
waarde heeft.

### Suggestie

`limit_reason: "past_optimum"` bij `magnitude_optimum_kind: "interior"` en een maatvoering
voorbij het optimum, met in `description` de betere maatvoering erbij genoemd.

---

## V-07 — `measure.delta` betekent iets anders in de twee supply-tools

**Ernst:** Midden · **Tools:** `calculate_supply_given_h` / `calculate_supply_given_supply`

### Waargenomen

| Tool | `measure.before` | `measure.after` | `measure.delta` |
|---|---|---|---|
| `supply_given_h` | 0,0 | 1,69 | **1,69** |
| `supply_given_supply` | 1,2 | 1,2 | **0,0** |

In de eerste is de inlaat een nieuw aan te leggen maatregel; in de tweede een bestaande
waarvan wordt doorgerekend wat ze doet.

### Analyse

Een caller die `measure.delta` uitleest als "wat moet er gebeuren" — een redelijke lezing,
en bij de zeven andere maatregeltools de juiste — leest bij `supply_given_supply` een 0 en
concludeert dat er niets hoeft te gebeuren. Terwijl er een inlaat van 1,2 m³/s in het spel
is die 50 van de 120 mm levert en waarbij 60 mm vraag onvervuld blijft.

Bij de wateroverlast-paren speelt dit niet: `discharge_given_discharge` rapporteert netjes
`before` 5,0 → `after` 7,312 → `delta` 2,312, want de opgegeven maatvoering is daar een
*toevoeging* aan een bestaande capaciteit. Bij aanvoeren is de opgegeven maatvoering de
totale inlaat, en dat verschil is niet uit het veld af te lezen.

### Suggestie

Maak de semantiek gelijk (`before` = bestaande situatie, `delta` = wat erbij komt), of
splits het inlaatveld in een bestaande en een extra capaciteit zoals bij het gemaal.

---

## V-08 — `sensitivity.note` is ambigu bij twee `null`-kolommen

**Ernst:** Midden · **Tool:** alle tools met `sensitivity`

### Waargenomen

```json
{"field": "days_to_discharge", "low_value": "2", "high_value": "4",
 "low_answer": 38.49, "high_answer": null,
 "note": "bij deze waarde is er geen maatregel nodig"}
```

Hier is "deze waarde" afleidbaar: de kolom die `null` is, dus 4. Maar bij
`status: no_measure_needed` en bij `action_infeasible` komen beide kolommen op `null`:

```json
{"field": "rainfall_regime", "low_value": "LL", "high_value": "H",
 "low_answer": null, "high_answer": null,
 "note": "bij deze waarde is het doel met deze maatregel niet haalbaar"}
```

Nu verwijst één enkelvoudig "deze waarde" naar twee waarden tegelijk.

### Suggestie

Splits naar `low_note` en `high_note`, elk gekoppeld aan zijn eigen kolom.

---

## Kleinere bevindingen

**V-09 — Cascade lekt volle float-precisie.** `worst_dh_m: 4.315204656087141`,
`median_dh_m: 2.3822801600622503`, `coupling_effect_m: 1.2712328160871347`. De rest van het
systeem rondt consequent op vier significante cijfers af (1,49 / 68,18 / 2,312). Vijftien
decimalen bij een vuistregelmodel is schijnprecisie, en een caller kan die letterlijk
doorgeven.

**V-10 — `binding_node` kiest stil uit gelijkwaardige kandidaten.** In een cascade met twee
polders (beide `head_max_m: 1.5`) die op een boezem lozen die 1,77 m stijgt, zijn beide
gemalen volledig geblokkeerd. De uitvoer noemt alleen `polder A`, terwijl `polder B` de
hoogste stijging heeft (4,32 m) en de `description` het formuleert als *"De koppeling knelt
bij 'polder A'"*. Het tie-break-criterium is onbekend. Overweeg een lijst, of vermelding
van het criterium.

**V-11 — Cascade mist `status` en `sensitivity`.** De acht maatregeltools hebben beide;
`calculate_cascade_given_excess` heeft wel `assumptions` en `caveats`, maar geen
`sensitivity`. Juist bij een cascade waar vier waarden zijn aangenomen zou de bandbreedte
waardevol zijn. Het ontbreken van `status` is verdedigbaar (er is geen maatregel), maar
verdient dan vermelding in `read_me`, dat nu stelt dat je `measure.after` nooit zonder
`status` moet lezen.

**V-12 — Numerieke ruis.** `shortfall_mm: 9.994e-7` waar 0 hoort te staan;
`days_until_buffer_empty: 29.96` bij een periode van 30 dagen. Afronden op de
rapportageprecisie lost beide op.

**V-13 — Foutmeldingen inconsistent.** Drie stijlen naast elkaar:
1. Engels en kaal: *"One of area_m2 or area_ha must be provided."*
2. Nederlands en uitleggend: *"Geef de gemaalcapaciteit op in een van deze eenheden: …"*
3. Rauwe Pydantic-uitvoer bij dubbele gebiedsnamen, inclusief
   `[type=value_error, input_value=…]` en een link naar `errors.pydantic.dev`.

De tweede stijl is de goede; de derde lekt implementatiedetails die voor een caller ruis
zijn.

**V-14 — Supply-uitvoer dupliceert zes velden.** `demand_mm`, `supplied_mm`, `buffer_mm`,
`shortfall_mm`, `drawdown` en `days_until_buffer_empty` staan zowel in `data` als op
topniveau. Onschadelijk, maar het roept bij een caller de vraag op of er verschil is.

**V-15 — `cost` blijft gevuld bij `action_infeasible`.** Bij `delta_h_available: 0.02` staat
er `cost: 521100000` naast `after: 4000 ha` (100 % open water). De handleiding waarschuwt
hier expliciet voor, en dat werkt zolang de caller de handleiding leest — maar het veld
nullen is robuuster dan erop vertrouwen. Eventueel `cost: null` met de bestaande waarde in
een apart `cost_at_physical_bound`.

**V-16 — Afronding in `description` botst met `measure.delta`.** 12,71 ha wordt "10 ha";
37,52 ha wordt "40 ha". De gedachte is duidelijk en goed — de handleiding vraagt om een
bereik in plaats van een punt. Maar als een caller zowel de `description` als
`measure.delta` doorgeeft, spreekt het antwoord zichzelf tegen. Overweeg de afronding
expliciet als bereik te presenteren (`"10 tot 40 ha"`) in plaats van als afgerond punt.

**V-17 — `language` lekt in de uitvoer.** Elk object in `theta_steps` bevat
`"language": "nl"`, een invoerveld dat in een resultaatobject niets te zoeken heeft.

---

## Wat goed werkt

Deze punten zijn getest en bevestigd, en verdienen vermelding omdat ze niet vanzelf spreken.

**Round-trips sluiten exact.** `store_given_h` geeft 68,18 ha bij een doel van 1,00 m;
diezelfde 68,18 ha in `store_given_area` geeft 1,00 m terug. Idem voor het afvoerpaar
(2,312 m³/s heen en terug).

**Eenheidsconversies kloppen over de hele breedte.** Dezelfde som ingevoerd als 5 m³/s,
1,25 l/s/ha en 10,8 mm/d, en als 4000 ha en 40 000 000 m², levert identieke uitvoer tot op
het laatste cijfer. Ook binnen één respons is de conversie sluitend: 2,312 m³/s ↔
138,7 m³/min ↔ 199 800 m³/d ↔ 4,994 mm/d.

**`sensitivity` is een echte herberekening.** De tabel voorspelde 128,2 ha bij
`time_of_year: winter`; een directe aanroep met dat veld gaf 128,2 ha. Geen linearisatie.

**Volumebehoud.** Het benodigde *totale* open water (208,2 ha) is onafhankelijk van het
startpercentage — bij 2 % en bij 3,5 % komt hetzelfde eindareaal uit. Fysisch correct en
een goede sanity check dat de bergingsbalans klopt.

**Het binnenoptimum bij vasthouden.** `magnitude_optimum_kind: "interior"` met een optimum
bij 2645 ha: meer land vasthouden maakt het resultaat slechter, omdat het uitgestelde water
op de piek terugkomt. Dit is het soort gedrag dat een simpel model juist mist, en het is
hier correct gemodelleerd.

**De noemers kloppen met de documentatie.** `share_of_nl` bij vasthouden is "het
landoppervlak", en 2645 / 3860 = 68,52 % — precies het gerapporteerde percentage. Bij
bergen is de noemer het hele gebied. Dat is consistent met wat `read_me` belooft.

**De verdringingsreeks rekent exact.** Nagerekend bij een bron van 2 Mm³ op een vraag van
5,76 Mm³: categorie 1 krijgt 0,36 Mm³ volledig, categorie 2 krijgt 0,6 Mm³ volledig,
categorie 4 houdt 1,04 van 4,8 Mm³ over = 21,67 %. Exact wat de tool rapporteert.

**Een eindige bron bindt correct.** Met `available_source_volume_m3: 2000000` levert een
inlaat van 0,3 l/s/ha (capaciteit 77,8 mm) slechts 50 mm, want de bron is de beperking en
niet het kunstwerk. Correct doorgerekend.

**Caveats zijn contextgevoelig.** Zodra `available_source_volume_m3` wordt ingevuld, wisselt
de caveat van *"dit veronderstelt dat het water bij die inlaat beschikbaar is"* naar
*"de beschikbaarheid zit nu IN dit antwoord"*. Dat is doordacht gebouwd en zeldzaam.

**Topologiefouten zijn uitstekend afgevangen.** De cyclusmelding legt uit *waarom* het niet
kan: *"water dat rondgaat vraagt een gekoppeld stelsel en niet een pass per diepte."* Een
onbekende `drains_to` levert een melding met een concrete handeling erbij: *"Voeg het toe,
of laat `drains_to` weg als het buiten het systeem loost."*

**De beste foutmelding van het systeem** staat bij een negatieve
`delta_discharge_capacity`, en verdient navolging als sjabloon:

> *"delta_discharge_capacity is de uitbreiding van de capaciteit en kan niet negatief zijn.
> Bedoel je een kleiner gemaal, geef dan de kleinere discharge_capacity op. Bedoel je water
> dat de andere kant op gaat, dan is dat aanvoer: gebruik calculate_supply_given_supply."*

Hij weigert, legt uit, en wijst twee kanten op — inclusief de juiste andere tool.

**`individual_coverage_range_per_category` is intellectueel eerlijk.** De tool rapporteert
`[0,217 – 1,0]` voor categorie 4 en zegt er in de caveat bij dat de wet tussen die uitersten
niet kiest, omdat de schadefuncties ontbreken. Dat is precies de juiste omgang met een
grens van het model.

---

## Testdekking

| Tool | Aanroepen | Getest op |
|---|---|---|
| `read_me` | 1 | alle vier modules |
| `calculate_store_given_h` | 9 | baseline, 3 eenheidsvarianten, conflict, minimale invoer, 3 statussen, peilmarge |
| `calculate_store_given_area` | 3 | round-trip, nul-maatregel, `language: en` |
| `calculate_discharge_given_h` | 1 | baseline |
| `calculate_discharge_given_discharge` | 2 | round-trip, negatieve delta |
| `calculate_retention_given_h` | 1 | binnenoptimum |
| `calculate_retention_given_area` | 2 | voorbij optimum, negatieve delta |
| `calculate_supply_given_h` | 1 | volledige eenheidscontrole |
| `calculate_supply_given_supply` | 1 | eindige bron |
| `calculate_cascade_given_excess` | 4 | 3 knopen met terugkoppeling, cyclus, dubbele namen, onbekende `drains_to` |
| `calculate_allocation_given_shortage` | 2 | vier categorieën, twee bronvolumes |
| **Totaal** | **28** | |

### Niet getest

De volgende zaken vielen buiten deze ronde en zijn kandidaat voor een vervolg:

- Alle zeven `name_rainfall_pattern`-waarden (alleen `p1c` en de standaard zijn geraakt).
- De volledige `return_period`-enum; alleen T=100 is gebruikt.
- Cascades dieper dan twee lagen, en het gedrag bij `converged: false`.
- De `maxItems: 50` grens op `nodes` in beide systeemtools.
- Gedrag bij `discharge_capacity` = 0 (een polder zonder gemaal).
- `percentage_open_water` = 100.
- `retention_fraction` op cascade-knopen.
- Kostenbandbreedtes tegen de onderliggende bronnen uit 2024/25.
