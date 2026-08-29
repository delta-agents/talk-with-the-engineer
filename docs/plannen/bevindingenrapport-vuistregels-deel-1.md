# Bevindingenrapport Vuistregels-TEST MCP

**Datum:** 27 augustus 2026
**Scope:** alle 11 tools van de `Vuistregels-TEST` MCP-server
**Aantal aanroepen:** 21 (18 geslaagd, 3 time-outs)
**Methode:** handleiding eerst gelezen via `read_me` (alle vier modules), daarna
getest in rondes: baseline → terugrekening → eenheden → invoervalidatie →
statussen → droogtestatistiek → systeemtools → topologische randgevallen.

Alle JSON-fragmenten in dit rapport zijn de letterlijke inhoud van het
`input`-object. Elk fragment is één-op-één opnieuw aan te roepen.

---

## 1. Samenvatting

| # | Ernst | Tool | Bevinding |
|---|---|---|---|
| B1 | Blocker | `calculate_allocation_given_shortage` | Hangt; 3 van 3 aanroepen time-out na 4 min |
| B2 | Hoog | `calculate_cascade_given_excess` | `binding_node` lijkt stilstand te meten in plaats van blokkade |
| B3 | Hoog | `calculate_retention_given_h` / `_given_area` | `sensitivity`-rij `days_to_retain_discharge` is stale |
| B4 | Middel | `calculate_supply_given_h` / `_given_supply` | `discharge_capacity_*` is verplicht maar inert |
| B5 | Middel | `calculate_supply_*` | `window_days` overschreven door `length_days`, binnen bronblok |
| B6 | Middel | `read_me` / droogtestatistiek | Gedocumenteerde T100-weigering niet reproduceerbaar |
| B7 | Middel | alle maatregeltools | `description` rondt af op 1 significant cijfer (~20% afwijking) |
| B8 | Laag | `calculate_supply_*` | Validatievolgorde: conflictmelding pas na capaciteitscheck |
| B9 | Laag | `calculate_cascade_given_excess` | Geen plausibiliteitsvlag; "Over 1 gebieden"; koude start |

---

## 2. Wat is geverifieerd en werkt

Deze punten zijn actief getest en gaven het verwachte resultaat. Ze zijn de
moeite van het vastleggen waard, omdat een regressie hierop stil zou blijven.

**Terugrekening is exact.** `store_given_h` vraagt 12,71 ha; diezelfde 12,71 ha
terugvoeren in `store_given_area` geeft precies `dh_with_measure_m: 1.0` en een
identiek `measure`-blok. Idem voor het afvoerpaar met 0,7415 m³/s.

**Eenheidsomrekening is byte-identiek.** Deze twee aanroepen geven een volledig
gelijke uitvoer:

```json
{"area_ha": 4000, "delta_h_available": 1, "discharge_capacity_m3_per_sec": 5, "return_period": 100}
{"area_m2": 40000000, "delta_h_available": 1, "discharge_capacity_l_s_ha": 1.25, "return_period": 100}
```

**Massabalans op de droge kant sluit.** Bij `supply_given_h` met Rijn en IJssel /
Referentie / T10: `demand_mm` 268,6 = `supplied_mm` 262,6 + `buffer_mm` 6,0, met
`shortfall_mm` 0. Bij `supply_given_supply` klopt ook de uitputtingsdag:
6 mm / 0,544 mm per dag = 11,04 = `days_until_buffer_empty`.

**IJkgetal uit de handleiding klopt.** De handleiding noemt voor Rijn en IJssel,
Referentie, T10: 269 mm en 1,5 mm/dag. De tool geeft 268,6 mm en 1,468 mm/dag.

**Concentratie-effect van `length_days` gedraagt zich als beschreven.** Van 183
naar 90 dagen blijft `cumulative_deficit_mm` 268,6, loopt het tekort van 1,468
naar 2,984 mm/dag en de inlaat van 0,1661 naar 0,3377 l/s/ha — overeenkomend met
de "1,5 naar 3,0" en "0,16 naar 0,33" uit de handleiding.

**Statusmachine correct in alle vier de takken.** `exact`, `no_measure_needed`
(delta 0, `cost` 0), `action_infeasible` (`cost` leeg, `cost_at_limit` gevuld) en
`limit_reason: past_optimum` met een expliciete uitleg dat een kleinere maatregel
beter en goedkoper is.

**Invoervalidatie op eenheden en conflicten.** Twee eenheden voor dezelfde
grootheid en de combinatie `deficit_mm_per_day` + droogtetripel worden beide
geweigerd, met de foute waarden in de melding en een handelingsperspectief.

**Topologische validatie van de cascade.** Kringloop, `drains_to` naar een
niet-bestaand gebied (inclusief hoofdletterverschil `Boezem` vs `boezem`) en
dubbele knoopnamen worden alle drie geweigerd met een bruikbare melding.

**Conditionele caveats verschijnen gericht.** De caveat over de koppelingswet
verschijnt alleen bij gebruik van `head_max_m`; de caveat over peilopzet alleen
bij `target_level_rise_m`. `assumptions` laat correct de velden weg die de
aanroeper zelf heeft ingevuld.

---

## 3. Bevindingen

### B1 — `calculate_allocation_given_shortage` hangt

**Ernst:** blocker
**Status:** de hele droogteverdelingskant van de MCP is onbruikbaar en is
hierdoor niet gereviewd.

**Waarneming.** Drie aanroepen, alle drie afgebroken na 4 minuten zonder
antwoord. Ook het voorbeeld uit de eigen tooldocumentatie loopt vast. Een
teruggebrachte variant met één afnemer, zonder `draws_from`, hangt eveneens — de
oorzaak zit dus niet in de topologie of het aantal knopen.

**Reproductie (minimaal geval):**

```json
{"available_source_volume_m3": 4000000, "length_days": 30,
 "nodes": [{"area_ha": 4000, "category": 4, "deficit_mm_per_day": 4,
            "intake_capacity_m3_per_sec": 1.5, "name": "landbouwpolder"}]}
```

**Server is aantoonbaar gezond gebleven.** Tussen en na de hangende aanroepen
reageerden `calculate_store_given_h` en `calculate_cascade_given_excess`
normaal en binnen enkele seconden. Het probleem is dus toolspecifiek en niet een
dode of geblokkeerde server.

**Vermoeden.** Een lus in de verdringingsreeks- of `theta_steps`-oplosser die
niet termineert. Aandachtspunt bij het opsporen: dit is de enige tool met een
iteratieve toewijzing zonder expliciete iteratielimiet in de uitvoer — de
cascade rapporteert wel `iterations` en `converged`.

---

### B2 — `binding_node` lijkt stilstand te meten in plaats van blokkade

**Ernst:** hoog
**Waarom dit zwaar weegt:** de tool bestaat blijkens zijn eigen beschrijving om
te vinden "waar de drainage vastloopt — welk gemaal het niet bijhoudt". Als dat
antwoord omgekeerd is, is de kopregel van de tool onjuist terwijl de
onderliggende waterstanden kloppen.

**Waarneming.** In een cascade zonder enige `head_max_m`, met `iterations: 0`
(dus een enkele pass en per definitie geen terugkoppeling), meldt de tool:

> De koppeling knelt bij 'polder A': op het uur van zijn eigen piek was 94 % van
> het geinstalleerde gemaalvermogen niet beschikbaar.

Tegelijk is `lowest_dh_m: 0.0` — polder A stijgt niet. Een gemaal dat voor 94%
onbeschikbaar is in een polder die geen centimeter stijgt, kan niet allebei waar
zijn.

**Reproductie:**

```json
{"return_period": 25,
 "nodes": [{"name": "polder A", "area_ha": 1000, "percentage_open_water": 4,
            "discharge_capacity_m3_per_sec": 2, "drains_to": "boezem"},
           {"name": "boezem", "area_ha": 3000, "percentage_open_water": 5,
            "discharge_capacity_m3_per_sec": 4}]}
```

Uitvoer: `binding_node: "polder A"`, `blocked_capacity_fraction: 0.9429`,
`lowest_dh_m: 0.0`, `iterations: 0`, `converged: true`.

**Waarschijnlijke oorzaak.** Polder A is ruim bemeten (2 m³/s op 1000 ha = 2
l/s/ha bij 4% open water) en heeft op het piekuur weinig te verpompen. De 94% is
dan *ongebruikte* capaciteit, niet *geblokkeerde*. De metriek meet inzet, de
tekst spreekt over beschikbaarheid, en de conclusie ("knelt bij") volgt uit geen
van beide.

**Tweede symptoom: numerieke ruis wordt gepromoveerd tot conclusie.** In een
andere cascade was `blocked_capacity_fraction: 2.109e-15` — een drijvende-komma
nul — en toch verscheen dezelfde zin "de koppeling knelt bij 'polder A'", met
"0 %" in de tekst. Een zin die zichzelf tegenspreekt.

Reproductie daarvan:

```json
{"return_period": 10,
 "nodes": [{"name": "polder A", "area_ha": 4000, "percentage_open_water": 3.5,
            "discharge_capacity_m3_per_sec": 5, "drains_to": "boezem"},
           {"name": "boezem", "area_ha": 8000, "percentage_open_water": 3.5,
            "discharge_capacity_m3_per_sec": 10}]}
```

**Derde symptoom: de metriek is instabiel over terugkeertijden.** Exact dezelfde
topologie geeft bij T10 `binding_node: "polder A"` en bij T100
`binding_node: null` met `blocked_capacity_fraction: null`.

**Ter contrast: bij echte terugkoppeling klopt het wel.** Met `head_max_m` en een
te kleine benedenstroomse boezem komt er `iterations: 2` en
`blocked_capacity_fraction: 1.0`, en dan is de melding terecht:

```json
{"return_period": 100,
 "nodes": [{"name": "polder A", "area_ha": 4000, "percentage_open_water": 3.5,
            "discharge_capacity_m3_per_sec": 5, "head_max_m": 0.5, "drains_to": "boezem"},
           {"name": "boezem", "area_ha": 2000, "percentage_open_water": 1,
            "discharge_capacity_m3_per_sec": 1}]}
```

**Voorstel.** Rapporteer `binding_node` alleen wanneer er daadwerkelijk
terugkoppeling is (`head_max_m` aanwezig én `iterations > 0`), leg een
ondergrens op `blocked_capacity_fraction` (bijvoorbeeld 1e-6) voordat de
conclusiezin wordt gegenereerd, en scheid in de naamgeving "niet ingezet" van
"niet beschikbaar".

---

### B3 — `sensitivity`-rij voor `days_to_retain_discharge` is stale

**Ernst:** hoog
**Waarom dit zwaar weegt:** de handleiding schrijft in de module `terugkoppelen`
expliciet voor dat `assumptions`, `sensitivity` en `caveats` alle drie in de
terugkoppeling aan de gebruiker horen. Deze rij geeft dus verkeerde informatie
door langs een pad dat de handleiding verplicht stelt.

**Waarneming.** Bij `calculate_retention_given_h` meldt de gevoeligheidsrij voor
`days_to_retain_discharge` zowel bij 0 als bij 4 dagen de waarde `1266.0` —
exact het basisantwoord. De werkelijke waarden zijn heel anders:

| `days_to_retain_discharge` | Gerapporteerd in `sensitivity` | Werkelijk (aparte aanroep) | Werkelijke status |
|---|---|---|---|
| 0 | 1266,0 ha | **104,4 ha** | `action_infeasible` |
| 2 (basis) | — | 1266,0 ha | `exact` |
| 4 | 1266,0 ha | **461,3 ha** | `exact` |

Bij 0 dagen is het doel met deze maatregel dus helemaal niet haalbaar, en dat
wordt doorgegeven als een keurige 1266 ha.

**Reproductie.** Basisaanroep, en vervolgens dezelfde aanroep met het veld
expliciet op 0 en op 4:

```json
{"area_ha": 4000, "delta_h_available": 1, "discharge_capacity_m3_per_sec": 5, "return_period": 100}
{"area_ha": 4000, "delta_h_available": 1, "discharge_capacity_m3_per_sec": 5, "return_period": 100, "days_to_retain_discharge": 0}
{"area_ha": 4000, "delta_h_available": 1, "discharge_capacity_m3_per_sec": 5, "return_period": 100, "days_to_retain_discharge": 4}
```

**Reikwijdte.** Ook aanwezig in `calculate_retention_given_area` (daar
0,7454 / 0,7454 m, gelijk aan `dh_with_measure_m`). De rij verschijnt alleen
wanneer het veld is aangenomen — precies het geval waarin de aanroeper er het
meest op leunt. Zodra de aanroeper het veld zelf opgeeft, verdwijnt de rij
correct uit zowel `assumptions` als `sensitivity`.

**Aandachtspunt bij het opsporen.** De overige rijen in dezelfde `sensitivity`
(`days_to_discharge`, `length_event_hrs`, `percentage_open_water`,
`rainfall_regime`, `time_of_year`) zijn wél correct en variëren netjes. Het
probleem is dus geïsoleerd tot deze ene variabele, die als enige uitsluitend bij
de retentietools voorkomt.

---

### B4 — `discharge_capacity_*` is verplicht maar inert op de aanvoertools

**Ernst:** middel

**Waarneming.** Twee losse problemen die elkaar versterken.

*Verplicht, maar niet zo gemarkeerd.* Het schema van `calculate_supply_given_h`
noemt alleen `drawdown_available_m` in `required`. Toch weigert de tool zonder
gemaalcapaciteit:

> Geef de gemaalcapaciteit op in een van deze eenheden: discharge_capacity_l_s_ha,
> discharge_capacity_m3_per_sec, ...

*En de waarde doet niets.* Deze twee aanroepen geven een volledig identieke
uitvoer — alle velden, tot en met `description` en `caveats`:

```json
{"area_ha": 4000, "deficit_mm_per_day": 4, "delta_supply_capacity_l_s_ha": 0.4, "discharge_capacity_l_s_ha": 1.25, "drawdown_available_m": 0.3}
{"area_ha": 4000, "deficit_mm_per_day": 4, "delta_supply_capacity_l_s_ha": 0.4, "discharge_capacity_l_s_ha": 5,    "drawdown_available_m": 0.3}
```

**Waarom dit opvalt.** Het schemacommentaar van deze server verwerpt dit patroon
elders expliciet: "een veld dat wordt geaccepteerd en genegeerd is erger dan geen
veld". Hier is het bovendien een veld dat verplicht is én genegeerd wordt. Een
gebruiker die 1,25 tegen 5 l/s/ha afweegt krijgt tweemaal hetzelfde antwoord
zonder enige aanwijzing dat de vergelijking zinloos is.

**Keuze.** Of het veld laten meerekenen (een gemaal dat in een droge periode
doorloopt beïnvloedt de peilband), of het van de aanvoertools verwijderen. Blijft
het staan, dan hoort het in `required` en zou het bij afwijkende waarden in
`assumptions` of een caveat moeten opduiken.

---

### B5 — `window_days` wordt overschreven door `length_days`

**Ernst:** middel

**Waarneming.** Bij `length_days: 90` bevat het blok `drought_statistic`:

```
"cumulative_deficit_mm": 268.6, "window_days": 90, "source": "STOWA 2025-23"
```

Het venster van die statistiek is 183 dagen (1 april – 1 oktober); de 90 is een
keuze van de aanroeper. Die keuze staat nu binnen een blok dat door `source`
geattribueerd wordt aan STOWA. De begeleidende caveat noemt in dezelfde uitvoer
wél correct "1 april tot 1 oktober", waardoor de uitvoer zichzelf tegenspreekt.

**Reproductie:**

```json
{"area_ha": 4000, "discharge_capacity_l_s_ha": 1.25, "drawdown_available_m": 0.3,
 "drought_region": "Rijn_en_IJssel", "drought_return_period": 10,
 "drought_scenario": "Referentie", "length_days": 90}
```

**Waarom dit meer is dan cosmetiek.** Dit is dezelfde tweedeling waar de
handleiding elders scherp op is: wat je overkomt tegenover wat je afspreekt.
`window_days` hoort de eigenschap van de bron te blijven; de gekozen
concentratie staat al in `length_days`. Voorstel: `window_days` vast op 183
houden en desgewenst een apart veld toevoegen voor het gekozen venster.

---

### B6 — Gedocumenteerde T100-weigering niet reproduceerbaar

**Ernst:** middel

**Waarneming.** De tooldocumentatie bij `drought_return_period` stelt: "niet elke
combinatie bestaat — bij de natste scenario's is T100 niet bereikt binnen de
gebruikte reeks, en dan weigert de tool met uitleg in plaats van te
extrapoleren." Drie pogingen om die weigering uit te lokken leverden alle drie
gewoon een getal op:

| Regio | Scenario | T | `cumulative_deficit_mm` |
|---|---|---|---|
| Rijn en IJssel | `Ln_2100` | 100 | 409,4 |
| Rijn en IJssel | `Hn_2100` | 100 | 498,0 |
| Delfland | `Hn_2100` | 100 | 476,1 |

**Reproductie:**

```json
{"area_ha": 4000, "discharge_capacity_l_s_ha": 1.25, "drawdown_available_m": 0.3,
 "drought_region": "Rijn_en_IJssel", "drought_return_period": 100, "drought_scenario": "Ln_2100"}
```

**Twee mogelijkheden.** Ofwel de dataset is aangevuld en de documentatie is
achterhaald, ofwel de weigering geldt voor regio's die deze drie steekproeven
niet raakten. In beide gevallen is de tekst zoals hij er nu staat niet waar voor
de meest voor de hand liggende testgevallen. Dit is niet uitputtend getest: 21
regio's × 7 scenario's is niet doorlopen.

---

### B7 — `description` rondt af op één significant cijfer

**Ernst:** middel

**Waarneming.** De zin in `description` wijkt structureel af van het
gestructureerde veld `measure.delta`:

| Tool | `measure.delta` | Tekst in `description` | Afwijking |
|---|---|---|---|
| `store_given_h` | 12,71 ha | "ongeveer 10 ha extra open water" | −21% |
| `retention_given_h` | 1266 ha | "ongeveer 1000 ha land" | −21% |
| `retention_given_area` | 3900 ha | "ongeveer 4000 ha land" | +3% |

**Spanning met de handleiding.** De module `terugkoppelen` schrijft voor: "geef
een bereik, geen punt" — en het bereik dat de tool erbij geeft ("Reken op 10 tot
100 ha") is inderdaad goed. Maar het puntgetal in dezelfde zin is dan een
afgeronde ondergrens die als centrale schatting leest. Wie de zin citeert zonder
`measure.delta` erbij te pakken, zit er consequent ruim een vijfde onder.

**Voorstel.** Twee significante cijfers ("ongeveer 13 ha"), of de puntwaarde
weglaten en alleen het bereik noemen.

---

### B8 — Validatievolgorde

**Ernst:** laag

**Waarneming.** Bij een aanroep met zowel de verboden combinatie
(`deficit_mm_per_day` naast een droogtetripel) als een ontbrekende
gemaalcapaciteit, komt eerst de melding over de gemaalcapaciteit. Pas nadat die
is opgelost, verschijnt de inhoudelijk belangrijkere conflictmelding. Dat kost de
aanroeper een extra ronde en leidt de aandacht naar een ander veld.

**Reproductie:**

```json
{"area_ha": 4000, "deficit_mm_per_day": 4, "drawdown_available_m": 0.3,
 "drought_region": "Rijn_en_IJssel", "drought_return_period": 10, "drought_scenario": "Referentie"}
```

Geeft: melding over ontbrekende gemaalcapaciteit. Met
`"discharge_capacity_l_s_ha": 1.25` erbij verschijnt pas de conflictmelding.

**Kanttekening.** Beide meldingen zijn op zichzelf uitstekend. Het gaat alleen om
de volgorde; conflicten tussen opgegeven velden eerst afhandelen, dan pas
ontbrekende velden.

---

### B9 — Kleinere punten

**Geen plausibiliteitsvlag bij extreme uitkomsten.** Een cascade-uitkomst van
`worst_dh_m: 4.876` (4,88 m stijging) wordt zonder enige markering gerapporteerd.
De twee systeemtools hebben blijkens de handleiding bewust geen `status`-veld,
waardoor er ook niets is dat zo'n uitkomst kán markeren; `converged: true` zegt
alleen iets over de numeriek. Overweging: een plausibiliteitsveld toevoegen, of
de bovengrens in de `description` benoemen.

**Grammatica in de cascade-beschrijving.** Bij één knoop: "Over **1 gebieden** in
1 topologische lagen is de hoogste stijging 13 cm". Enkelvoud/meervoud wordt niet
verbogen.

**Afrondingsverschil tussen tools.** Dezelfde 0,7415 m³/s levert
`extra_discharge_capacity_m3_d_required` op als 64060 in
`calculate_discharge_given_h` en 64070 in `calculate_discharge_given_discharge`.
Verwaarloosbaar inhoudelijk, maar zichtbaar wanneer twee antwoorden naast elkaar
worden gezet — wat de handleiding juist aanraadt.

**Koude start.** De allereerste aanroep van `calculate_cascade_given_excess` liep
na 4 minuten dood; daarna reageerde dezelfde tool op identieke invoer binnen
seconden en is het niet meer opgetreden. Dat wijst op het laden van een zware
afhankelijkheid bij eerste gebruik. Met een MCP-client die na 4 minuten opgeeft
is dat een eerste indruk die de gebruiker niet terugkrijgt. Overweging: de
statistiek bij het opstarten van de server inladen in plaats van bij eerste
aanroep.

---

## 4. Testdekking

**Wel getest.** Alle 8 maatregeltools (baseline, terugrekening, eenheden,
statussen), `read_me` (4 modules), `calculate_cascade_given_excess` (1 knoop,
2 knopen, terugkoppeling met `head_max_m`, kringloop, ontbrekende referentie,
dubbele namen, `level_margin_m` en `target_level_rise_m`), droogtestatistiek
(4 regio/scenario-combinaties, 2 vensters), invoervalidatie op beide verboden
combinaties.

**Niet getest.**

- `calculate_allocation_given_shortage` volledig — geblokkeerd door B1. Hiermee
  ontbreken ook de verdringingsreeks-logica, `theta_steps`,
  `coverage_per_category` en `contains_current_theta` uit de handleiding.
- `language: "en"` op geen van de tools; alle uitvoer is in het Nederlands
  beoordeeld.
- Cascades dieper dan 2 lagen en breder dan 2 knopen; de `maxItems: 50`-grens.
- Negatieve en nul-waarden op velden zonder ondergrens in het schema
  (`days_to_retain_discharge` heeft geen `minimum`).
- Kostenvelden zijn op interne consistentie bekeken maar niet tegen de
  bronprojecten uit `bronnen` geijkt.
- De volledige droogtematrix (21 regio's × 7 scenario's × 6 herhaaltijden).

---

## 5. Voorgestelde volgorde van oppakken

1. **B1** — zonder deze fix is een derde van de functionaliteit onbereikbaar en
   blijft een deel van dit rapport onvoltooid.
2. **B2** en **B3** — beide geven een verkeerd antwoord met een zelfverzekerde
   toon, langs paden die de handleiding verplicht stelt door te geven. Dit is
   schadelijker dan een foutmelding.
3. **B4** tot en met **B7** — correctheid van schema, attributie en
   getalweergave.
4. **B8**, **B9** — afwerking.

Na B1 is een herhaling van de verdelingstool-tests nodig; die zijn hier volledig
afwezig.
