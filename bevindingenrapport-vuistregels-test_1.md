# Bevindingenrapport Vuistregels-TEST MCP

**Versie 2 — 27 augustus 2026**
**Scope:** alle 11 tools van de `Vuistregels-TEST` MCP-server
**Aantal aanroepen:** 29 (26 geslaagd, 3 time-outs in ronde 1)
**Methode:** handleiding eerst gelezen via `read_me` (alle vier modules), daarna
getest in rondes: baseline → terugrekening → eenheden → invoervalidatie →
statussen → droogtestatistiek → systeemtools → topologische randgevallen →
hertest van de geblokkeerde tool → oorzaakanalyse van de stale gevoeligheid.

**Wijzigingen ten opzichte van versie 1**

- **B1 is opgelost** en de verdelingstool is alsnog volledig getest. Zie §3.1.
- **B2 is aangescherpt** met een sluitend tegenvoorbeeld: de melding verschijnt
  precies wanneer de knoop stilstaat en verdwijnt zodra hij daadwerkelijk volloopt.
- **B3 heeft een aanwijsbare oorzaak** — een naamverschil tussen invoerveld en
  intern model, hard aangetoond via een lekkende validatiefout. Zie §3.3.
- **Drie nieuwe bevindingen** uit de hertest: B10, B11, B12.

Alle JSON-fragmenten zijn de letterlijke inhoud van het `input`-object en
één-op-één opnieuw aan te roepen.

---

## 1. Samenvatting

| # | Ernst | Tool | Bevinding |
|---|---|---|---|
| B1 | ~~Blocker~~ **Opgelost** | `calculate_allocation_given_shortage` | Hing bij eerste test; werkt nu, rekenkern geverifieerd correct |
| B2 | Hoog | `calculate_cascade_given_excess` | `binding_node` vuurt op stilstand in plaats van blokkade — sluitend aangetoond |
| B3 | Hoog | `calculate_retention_given_h` / `_given_area` | Stale gevoeligheidsrij; oorzaak: naamverschil `days_to_retain_discharge` → `days_to_retain` |
| B10 | Middel/hoog | `calculate_allocation_given_shortage` | Nulvrager blaast dekkingsband op tot 100% — treedt op in het eigen voorbeeld |
| B4 | Middel | `calculate_supply_given_h` / `_given_supply` | `discharge_capacity_*` is verplicht maar inert |
| B5 | Middel | `calculate_supply_*` | `window_days` overschreven door `length_days`, binnen bronblok |
| B6 | Middel | `read_me` / droogtestatistiek | Gedocumenteerde T100-weigering niet reproduceerbaar |
| B7 | Middel | alle maatregeltools | `description` rondt af op 1 significant cijfer (~20% afwijking) |
| B11 | Middel | aanvoer- en verdelingstools | `sensitivity` structureel leeg of afwezig |
| B12 | Laag/middel | alle tools | Ruwe pydantic-fout lekt interne modelnaam en framework-URL |
| B8 | Laag | `calculate_supply_*` | Validatievolgorde: conflictmelding pas na capaciteitscheck |
| B9 | Laag | systeemtools | Geen plausibiliteitsvlag; "Over 1 gebieden"; koude start |

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
Referentie / T10: `demand_mm` 268,6 = `supplied_mm` 262,6 + `buffer_mm` 6,0. Bij
`supply_given_supply` klopt ook de uitputtingsdag: 6 mm / 0,544 mm per dag =
11,04 = `days_until_buffer_empty`.

**IJkgetal uit de handleiding klopt.** Rijn en IJssel, Referentie, T10: de
handleiding noemt 269 mm en 1,5 mm/dag; de tool geeft 268,6 en 1,468.

**Concentratie-effect van `length_days` gedraagt zich als beschreven.** Van 183
naar 90 dagen blijft het cumulatieve tekort 268,6 mm, loopt het tekort van 1,468
naar 2,984 mm/dag en de inlaat van 0,1661 naar 0,3377 l/s/ha.

**Verdringingsreeks rekent correct** — nieuw geverifieerd in ronde 2, zie §3.1.

**Gevoeligheidsrijen zijn correct, op één na** — nieuw geverifieerd, zie §3.3.

**Statusmachine correct in alle vier de takken.** `exact`, `no_measure_needed`,
`action_infeasible` (`cost` leeg, `cost_at_limit` gevuld) en `past_optimum`.

**Invoervalidatie op eenheden en conflicten**, en **topologische validatie van de
cascade** (kringloop, ontbrekende referentie inclusief hoofdletterverschil,
dubbele namen) werken alle met bruikbare meldingen.

**Conditionele caveats verschijnen gericht.** De koppelingswet-caveat alleen bij
`head_max_m`, de peilopzet-caveat alleen bij `target_level_rise_m`. `assumptions`
laat correct de velden weg die de aanroeper zelf invulde.

---

## 3. Bevindingen

### 3.1 B1 — `calculate_allocation_given_shortage` — OPGELOST

**Status:** in ronde 1 liepen drie van drie aanroepen na 4 minuten dood, ook een
minimaal geval met één knoop. In ronde 2 reageert dezelfde tool op exact dezelfde
invoer binnen seconden. De oorzaak van de oorspronkelijke hang is daarmee niet
vastgesteld; de tool is ondertussen niet gewijzigd voor zover zichtbaar. Houd er
rekening mee dat dit dus een intermitterend probleem kán zijn en geen opgeloste
bug. Als de server tussentijds is herstart, is dat de meest waarschijnlijke
verklaring, en dan blijft de vraag staan wat hem in ronde 1 heeft laten hangen.

**De rekenkern is nu geverifieerd en klopt.** Twee controles.

*Enkelvoudig geval, inlaat is de klem:*

```json
{"available_source_volume_m3": 4000000, "length_days": 30,
 "nodes": [{"name": "landbouwpolder", "area_ha": 4000, "category": 4,
            "deficit_mm_per_day": 4, "intake_capacity_m3_per_sec": 1.5}]}
```

Vraag = 4000 ha × 4 mm × 30 d = 4,8 mln m³ ✓ `total_demand_m3`. Inlaat = 1,5 m³/s
× 30 d = 3,888 mln m³ ✓ `total_granted_m3`. Dekking 3,888/4,8 = 0,81 ✓. Omdat de
inlaat (3,888) onder het bronaanbod (4,0) ligt, staat
`binding_is_capacity_not_availability: true` — correct, en de tekst zegt terecht
"meer water aanvoeren helpt hier niet, een grotere inlaat wel".

*Meervoudig geval, verdringingsreeks:* met een drinkwaterinname (categorie 2,
vraag 0,6 mln m³) erbij krijgt categorie 2 volledige dekking en categorie 4
(4,0 − 0,6) / 4,8 = 0,7083 ✓. `binding_is_capacity_not_availability` slaat correct
om naar `false`: nu is de bron de klem.

*`theta_steps` interpoleert exact lineair,* zoals de handleiding belooft. De
huidige θ = 0,7407 valt in trede 2 (0,1111–0,8311); lineair geeft dat
(0,7407−0,1111)/0,7200 × 0,81 = 0,7083, precies gelijk aan
`coverage_per_category`. De tredegrenzen zijn ook inhoudelijk juist: 0,1111 is
het punt waarop categorie 2 vol zit, 0,8311 het punt waarop de inlaat van
categorie 4 bindend wordt.

**Nog niet getest op deze tool:** categorieën 1 en 3, meer dan twee schillen,
`draws_from`-ketens dieper dan één laag, de `maxItems: 50`-grens, en het geval
zonder `available_source_volume_m3` (onbeperkte bron).

---

### 3.2 B2 — `binding_node` vuurt op stilstand in plaats van blokkade

**Ernst:** hoog
**Waarom dit zwaar weegt:** deze tool bestaat blijkens zijn eigen beschrijving om
te vinden "waar de drainage vastloopt — welk gemaal het niet bijhoudt". De
onderliggende waterstanden kloppen, maar juist de conclusiezin kan omgekeerd zijn.

**Het sluitende tegenvoorbeeld.** Twee aanroepen die alleen verschillen in
`days_to_discharge`, op dezelfde topologie zonder enige `head_max_m`:

| `days_to_discharge` | `lowest_dh_m` (polder A) | `binding_node` | `blocked_capacity_fraction` |
|---|---|---|---|
| 3 (aangenomen) | **0,0 m** | "polder A" | 0,9429 |
| 2 (expliciet) | **0,064 m** | `null` | `null` |

De melding verschijnt dus precies wanneer polder A *niet* stijgt, en verdwijnt
zodra hij daadwerkelijk volloopt. Dat is het omgekeerde van knellen. De 94% is
*ongebruikte* capaciteit — polder A is met 2 l/s/ha bij 4% open water ruim
bemeten en heeft op het piekuur weinig te verpompen — terwijl de tekst spreekt
van "niet beschikbaar" en daaruit "de koppeling knelt bij polder A" concludeert.

**Reproductie:**

```json
{"return_period": 25,
 "nodes": [{"name": "polder A", "area_ha": 1000, "percentage_open_water": 4,
            "discharge_capacity_m3_per_sec": 2, "drains_to": "boezem"},
           {"name": "boezem", "area_ha": 3000, "percentage_open_water": 5,
            "discharge_capacity_m3_per_sec": 4}]}
```

en dezelfde invoer met `"days_to_discharge": 2` erbij.

**Tweede symptoom: numerieke ruis wordt conclusie.** Bij een andere cascade was
`blocked_capacity_fraction: 2.109e-15` — een drijvende-komma nul — en verscheen
toch "de koppeling knelt bij 'polder A'", met "0 %" in dezelfde zin:

```json
{"return_period": 10,
 "nodes": [{"name": "polder A", "area_ha": 4000, "percentage_open_water": 3.5,
            "discharge_capacity_m3_per_sec": 5, "drains_to": "boezem"},
           {"name": "boezem", "area_ha": 8000, "percentage_open_water": 3.5,
            "discharge_capacity_m3_per_sec": 10}]}
```

**Derde symptoom: instabiel over terugkeertijden.** Exact dezelfde topologie geeft
bij T10 `binding_node: "polder A"` en bij T100 `binding_node: null`.

**Ter contrast: bij echte terugkoppeling klopt het wel.** Met `head_max_m` en een
te kleine benedenstroomse boezem: `iterations: 2`, `blocked_capacity_fraction: 1.0`,
en dan is de melding terecht.

```json
{"return_period": 100,
 "nodes": [{"name": "polder A", "area_ha": 4000, "percentage_open_water": 3.5,
            "discharge_capacity_m3_per_sec": 5, "head_max_m": 0.5, "drains_to": "boezem"},
           {"name": "boezem", "area_ha": 2000, "percentage_open_water": 1,
            "discharge_capacity_m3_per_sec": 1}]}
```

**Voorstel voor afvangen.** Drie voorwaarden voordat de conclusiezin wordt
gegenereerd: (1) er is terugkoppeling, dus `head_max_m` aanwezig én
`iterations > 0`; (2) `blocked_capacity_fraction` boven een ondergrens van
bijvoorbeeld 1e-6; (3) de knoop stijgt daadwerkelijk, dus `dh > 0`. Voorwaarde 3
is de goedkoopste vangst en had alle drie de symptomen hierboven onderschept.
Scheid daarnaast in de naamgeving "niet ingezet" van "niet beschikbaar".

---

### 3.3 B3 — Stale gevoeligheidsrij, met aanwijsbare oorzaak

**Ernst:** hoog
**Waarom dit zwaar weegt:** de module `terugkoppelen` schrijft voor dat
`assumptions`, `sensitivity` en `caveats` alle drie in de terugkoppeling aan de
gebruiker horen. Deze rij geeft dus onjuiste informatie door langs een pad dat de
handleiding verplicht stelt.

**Waarneming.** De gevoeligheidsrij voor `days_to_retain_discharge` echoot altijd
exact het basisantwoord, ongeacht wat dat basisantwoord is:

| Basisgeval | Rij meldt bij 0 én 4 | Werkelijk bij 0 | Werkelijk bij 4 |
|---|---|---|---|
| 1266 ha (T100, dtd=3) | 1266 / 1266 | **104,4 ha**, status `action_infeasible` | **461,3 ha** |
| 2016 ha (T100, dtd=2) | 2016 / 2016 | — | — |
| 0,7454 m (`_given_area`) | 0,7454 / 0,7454 | — | — |

Bij 0 dagen is het doel met deze maatregel helemaal niet haalbaar; dat wordt
doorgegeven als een keurige 1266 ha.

**Aanwijsbare oorzaak.** Een negatieve waarde lokt een ruwe validatiefout uit die
de interne naam prijsgeeft:

```json
{"area_ha": 4000, "days_to_retain_discharge": -5, "delta_h_available": 1,
 "discharge_capacity_m3_per_sec": 5, "return_period": 100}
```

geeft:

```
1 validation error for PolderState
days_to_retain
  Input should be greater than or equal to 0
```

Het invoerveld heet `days_to_retain_discharge`, het veld op `PolderState` heet
`days_to_retain`. Dat is het enige veld in de hele toolset met zo'n naamverschil,
en het is exact het enige veld met een stale rij. De meest waarschijnlijke
verklaring: de gevoeligheidsroutine zet de override onder de invoernaam, die op
het interne model niet bestaat en stil wordt genegeerd — waarna de "gevarieerde"
doorrekening het ongewijzigde basisgeval is.

**Alle overige rijen zijn geverifieerd correct.** Twee steekproeven waarbij de
voorspelde waarde exact is nagerekend:

| Tool | Rij | Voorspeld | Nagerekend |
|---|---|---|---|
| `retention_given_h` | `days_to_discharge` = 2 | 2016 ha | **2016 ha** ✓ |
| `cascade_given_excess` | `rainfall_regime` = LL | 0,5185 m | **0,5185 m** ✓ |

Het defect is dus geïsoleerd tot dit ene veld, en niet een systeemfout in de
gevoeligheidsroutine.

**Voorstel voor afvangen.** Drie maatregelen, oplopend in grondigheid:

1. **Direct:** de override op de interne naam zetten, of de twee namen
   gelijktrekken.
2. **Structureel:** de gevoeligheidsroutine laten falen op een onbekende
   veldnaam in plaats van stil door te rekenen. Een override die nergens
   terechtkomt is nu niet te onderscheiden van een variabele zonder effect.
3. **Als vangnet:** een assertie dat `low_answer` en `high_answer` niet beide
   exact gelijk zijn aan het basisantwoord. Dat had alle drie de gevallen in de
   tabel hierboven gevangen, en is goedkoop genoeg voor CI. Let op dat een echte
   nul-gevoeligheid dan als vals alarm kan langskomen; die zou expliciet
   gemarkeerd moeten worden in plaats van stilzwijgend te lijken op deze bug.

---

### 3.4 B10 — Nulvrager blaast de dekkingsband op tot 100% (nieuw)

**Ernst:** middel/hoog
**Waar het optreedt:** in het voorbeeld dat de tool zelf in zijn documentatie
meegeeft.

**Waarneming.** Een boezem die alleen als doorvoer in de selectie zit, heeft
`deficit_mm_per_day: 0` maar wél een categorie. Die nulvraag telt mee in
`individual_coverage_range_per_category` als volledige dekking, en trekt de
bovengrens naar 100%.

| Selectie | `individual_coverage_range_per_category` cat. 4 | Zin in `description` |
|---|---|---|
| Mét boezem (nulvraag) | [0,708, **1,0**] | "loopt de dekking van 71% **tot 100%**" |
| Zonder boezem | [0,708, **0,708**] | "loopt de dekking van 71% **tot 71%**" |

De uitkomsten die ertoe doen — `theta`, `coverage_per_category`,
`total_granted_m3`, `theta_steps` — zijn in beide gevallen identiek. Alleen de
band en de zin die de gebruiker leest verschillen, en die suggereert nu dat een
landbouwafnemer bij een andere verdeling volledig bediend zou kunnen worden.

**Reproductie:** de twee selecties naast elkaar.

```json
{"available_source_volume_m3": 4000000, "length_days": 30,
 "nodes": [{"name": "drinkwaterinname", "area_ha": 500, "category": 2, "deficit_mm_per_day": 4,
            "intake_capacity_m3_per_sec": 1, "draws_from": "boezem"},
           {"name": "landbouwpolder", "area_ha": 4000, "category": 4, "deficit_mm_per_day": 4,
            "intake_capacity_m3_per_sec": 1.5, "draws_from": "boezem"},
           {"name": "boezem", "area_ha": 8000, "category": 4, "deficit_mm_per_day": 0,
            "intake_capacity_m3_per_sec": 10}]}
```

en dezelfde zonder de boezem, met `draws_from` weggelaten bij de twee afnemers.

**Voorstel voor afvangen.** Knopen met een vraag van nul uitsluiten van de
dekkingsband; hun dekking is 0/0 en niet 100%. Een doorvoerknoop is bovendien
structureel nodig in de selectie zodra `draws_from` wordt gebruikt, dus dit is
geen exotisch geval maar het normale gebruik.

---

### 3.5 B11 — `sensitivity` structureel leeg of afwezig (nieuw)

**Ernst:** middel

**Waarneming.** De handleiding stelt `sensitivity` verplicht in de
terugkoppeling, maar twee toolfamilies leveren hem niet:

| Tool | `assumptions` | `sensitivity` |
|---|---|---|
| `calculate_supply_given_h` | gevuld | **altijd `[]`** |
| `calculate_supply_given_supply` | gevuld | **altijd `[]`** |
| `calculate_allocation_given_shortage` | gevuld | **veld ontbreekt volledig** |
| `calculate_cascade_given_excess` | gevuld | gevuld ✓ |

Bij de aanvoertools is dit opvallend omdat `percentage_open_water` daar wél als
aanname wordt gemeld, mét de tekst dat het "van alle invoervelden de uitkomst het
sterkst stuurt" — maar zonder enig getal over hoeveel het scheelt. De aanname
wordt dus gemeld en de gevoeligheid verzwegen.

Bij de verdelingstool is de afwezigheid inhoudelijk beter te verdedigen:
`theta_steps` vervult daar een vergelijkbare rol, en de caveat wijst daar
expliciet naar. Het verschil met de cascade — die géén `theta_steps` heeft maar
wél `sensitivity` — is dan wel onverklaard.

---

### 3.6 B12 — Ruwe validatiefout lekt interne modelnaam (nieuw)

**Ernst:** laag/middel

**Waarneming.** Waar alle andere foutmeldingen zorgvuldig in het Nederlands zijn
opgesteld met handelingsperspectief, valt deze terug op de ruwe framework-uitvoer:

```
1 validation error for PolderState
days_to_retain
  Input should be greater than or equal to 0 [type=greater_than_equal, input_value=-5, input_type=int]
    For further information visit https://errors.pydantic.dev/2.13/v/greater_than_equal
```

Drie problemen: de interne klassenaam `PolderState` en veldnaam `days_to_retain`
komen naar buiten en corresponderen niet met het invoerveld dat de gebruiker
opgaf; de melding is Engelstalig terwijl de rest Nederlands is; en er wordt naar
pydantic-documentatie verwezen, wat voor een waterbeheerder geen bruikbaar
handelingsperspectief is.

**Kanttekening.** Voor deze review was het lek juist nuttig — het leverde de
oorzaak van B3. Voor productie hoort het afgevangen te worden, en verdient
`days_to_retain_discharge` een ondergrens in het MCP-schema zelf, zoals de
meeste andere numerieke velden die al hebben.

---

### 3.7 B4 — `discharge_capacity_*` is verplicht maar inert

**Ernst:** middel

*Verplicht, maar niet zo gemarkeerd.* Het schema van `calculate_supply_given_h`
noemt alleen `drawdown_available_m` in `required`, maar de tool weigert zonder
gemaalcapaciteit.

*En de waarde doet niets.* Deze twee aanroepen geven een volledig identieke
uitvoer, tot en met `description` en `caveats`:

```json
{"area_ha": 4000, "deficit_mm_per_day": 4, "delta_supply_capacity_l_s_ha": 0.4, "discharge_capacity_l_s_ha": 1.25, "drawdown_available_m": 0.3}
{"area_ha": 4000, "deficit_mm_per_day": 4, "delta_supply_capacity_l_s_ha": 0.4, "discharge_capacity_l_s_ha": 5,    "drawdown_available_m": 0.3}
```

Het schemacommentaar van deze server verwerpt dit patroon elders expliciet: "een
veld dat wordt geaccepteerd en genegeerd is erger dan geen veld". Hier is het
bovendien verplicht én genegeerd. Keuze: laten meerekenen, of van de
aanvoertools verwijderen. Blijft het staan, dan hoort het in `required`.

---

### 3.8 B5 — `window_days` wordt overschreven door `length_days`

**Ernst:** middel

Bij `length_days: 90` bevat het blok `drought_statistic`:
`"window_days": 90` naast `"source": "STOWA 2025-23"`. Het venster van die
statistiek is 183 dagen; de 90 is een keuze van de aanroeper, die nu wordt
geattribueerd aan de bron. De caveat in dezelfde uitvoer noemt wél correct
"1 april tot 1 oktober", waardoor de uitvoer zichzelf tegenspreekt.

```json
{"area_ha": 4000, "discharge_capacity_l_s_ha": 1.25, "drawdown_available_m": 0.3,
 "drought_region": "Rijn_en_IJssel", "drought_return_period": 10,
 "drought_scenario": "Referentie", "length_days": 90}
```

Dit is dezelfde tweedeling waar de handleiding elders scherp op is: wat je
overkomt tegenover wat je afspreekt. Voorstel: `window_days` vast op 183 houden
en desgewenst een apart veld voor het gekozen venster.

---

### 3.9 B6 — Gedocumenteerde T100-weigering niet reproduceerbaar

**Ernst:** middel

De tooldocumentatie stelt dat bij de natste scenario's T100 niet bereikt is en de
tool weigert. Drie pogingen leverden gewoon een getal:

| Regio | Scenario | T | `cumulative_deficit_mm` |
|---|---|---|---|
| Rijn en IJssel | `Ln_2100` | 100 | 409,4 |
| Rijn en IJssel | `Hn_2100` | 100 | 498,0 |
| Delfland | `Hn_2100` | 100 | 476,1 |

Ofwel de dataset is aangevuld en de documentatie is achterhaald, ofwel de
weigering geldt voor regio's buiten deze steekproef. Niet uitputtend getest:
21 regio's × 7 scenario's is niet doorlopen.

---

### 3.10 B7 — `description` rondt af op één significant cijfer

**Ernst:** middel

| Tool | `measure.delta` | Tekst in `description` | Afwijking |
|---|---|---|---|
| `store_given_h` | 12,71 ha | "ongeveer 10 ha extra open water" | −21% |
| `retention_given_h` | 1266 ha | "ongeveer 1000 ha land" | −21% |
| `retention_given_area` | 3900 ha | "ongeveer 4000 ha land" | +3% |

Het bereik dat de tool erbij geeft is goed, maar het puntgetal in dezelfde zin is
een afgeronde ondergrens die als centrale schatting leest. Opvallend: bij een
expliciet opgegeven `days_to_discharge` verscheen wél "2016 ha" onafgerond, dus
de afronding is niet overal consistent. Voorstel: twee significante cijfers, of
de puntwaarde weglaten en alleen het bereik noemen.

---

### 3.11 B8 — Validatievolgorde

**Ernst:** laag

Bij een aanroep met zowel de verboden combinatie (`deficit_mm_per_day` naast een
droogtetripel) als een ontbrekende gemaalcapaciteit, komt eerst de melding over
de gemaalcapaciteit. Pas na het oplossen daarvan verschijnt de inhoudelijk
belangrijkere conflictmelding.

```json
{"area_ha": 4000, "deficit_mm_per_day": 4, "drawdown_available_m": 0.3,
 "drought_region": "Rijn_en_IJssel", "drought_return_period": 10, "drought_scenario": "Referentie"}
```

Beide meldingen zijn op zichzelf uitstekend; het gaat om de volgorde. Conflicten
tussen opgegeven velden eerst, dan pas ontbrekende velden.

---

### 3.12 B9 — Kleinere punten

**Geen plausibiliteitsvlag bij extreme uitkomsten.** Een cascade-uitkomst van
`worst_dh_m: 4.876` wordt zonder markering gerapporteerd. De systeemtools hebben
bewust geen `status`-veld, dus er is ook niets dat zo'n uitkomst kán markeren;
`converged: true` zegt alleen iets over de numeriek.

**Grammatica.** "Over **1 gebieden** in 1 topologische lagen" — treedt op in
zowel de cascade- als de verdelingstool.

**Drijvende-komma ruis in de uitvoer.** `total_granted_m3: 3888000.0000000005`
en `total_shortfall_m3: 911999.9999999995`. Elders wordt netjes afgerond op vier
significante cijfers; deze twee velden ontsnappen daaraan.

**Afrondingsverschil tussen tools.** Dezelfde 0,7415 m³/s levert
`extra_discharge_capacity_m3_d_required` op als 64060 in `discharge_given_h` en
64070 in `discharge_given_discharge` — zichtbaar juist wanneer twee antwoorden
naast elkaar worden gezet, wat de handleiding aanraadt.

**Koude start.** De allereerste cascade-aanroep liep na 4 minuten dood; daarna
reageerde dezelfde tool op identieke invoer binnen seconden. Zie ook §3.1: de
verdelingstool vertoonde in ronde 1 hetzelfde gedrag maar dan drie keer
achtereen. Overweging: de statistiek bij het opstarten van de server inladen in
plaats van bij eerste aanroep, en een gezondheidscheck toevoegen die dat afdwingt.

---

## 4. Testdekking

**Wel getest.** Alle 8 maatregeltools (baseline, terugrekening, eenheden, alle
vier statussen), `read_me` (4 modules), `calculate_cascade_given_excess`
(1 en 2 knopen, terugkoppeling met `head_max_m`, kringloop, ontbrekende
referentie, dubbele namen, `level_margin_m`, `target_level_rise_m`, expliciete
`days_to_discharge`), `calculate_allocation_given_shortage` (1, 2 en 3 knopen,
categorieën 2 en 4, inlaat- én bronbeperking, `theta_steps` narekenen, met en
zonder `length_days`), droogtestatistiek (4 regio/scenario-combinaties, 2
vensters), invoervalidatie op beide verboden combinaties, ondergrenscontrole op
`days_to_retain_discharge`.

**Niet getest.**

- Categorieën 1 en 3 van de verdringingsreeks; `draws_from`-ketens dieper dan één
  laag; de verdelingstool zonder `available_source_volume_m3` (onbeperkte bron).
- `language: "en"` op geen van de tools; alle uitvoer is in het Nederlands
  beoordeeld.
- Cascades dieper dan 2 lagen en breder dan 2 knopen; de `maxItems: 50`-grens op
  beide systeemtools.
- Kostenvelden zijn op interne consistentie bekeken maar niet tegen de
  bronprojecten uit de module `bronnen` geijkt.
- De volledige droogtematrix (21 regio's × 7 scenario's × 6 herhaaltijden).
- `retention_fraction` op cascadeknopen.

---

## 5. Voorgestelde volgorde van oppakken

1. **B2** en **B3** — beide geven een verkeerd antwoord met een zelfverzekerde
   toon, langs paden die de handleiding verplicht stelt door te geven. Dat is
   schadelijker dan een foutmelding. Voor beide staat een concreet vangnet
   beschreven in §3.2 en §3.3.
2. **B10** — treedt op in het eigen documentatievoorbeeld en raakt een zin die
   over waterverdeling gaat.
3. **B1** — vaststellen wat de hang in ronde 1 veroorzaakte, ook nu de tool weer
   werkt. Zolang dat onbekend is, is dit een latent probleem en geen opgeloste bug.
4. **B4** tot en met **B7**, **B11**, **B12** — correctheid van schema,
   attributie, getalweergave en foutafhandeling.
5. **B8**, **B9** — afwerking.
