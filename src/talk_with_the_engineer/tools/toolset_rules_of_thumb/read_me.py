"""De handleiding bij deze toolset, opvraagbaar in plaats van meegeleverd.

**Waarom een tool en geen langere beschrijvingen.** De tien tooldefinities kosten samen al
ongeveer 35.000 tokens, geladen voordat er iets gevraagd is. Alles wat hier staat erbij
zetten zou dat verdubbelen, terwijl het bij de meeste gesprekken niet nodig is. Achter een
tool betaal je het alleen wanneer je het opvraagt, en dan alleen de module die je nodig hebt.
Hetzelfde patroon als de `visualize`-server met zijn `modules`-enum.

Vier modules, en ze beantwoorden vier verschillende vragen:

* `bronnen`      - waar komen de getallen vandaan
* `vuistregels`  - wat doet het model ermee, en welke aannames sturen de uitkomst
* `gebruik`      - welke tool hoort bij welke vraag
* `terugkoppelen`- hoe praat je over het antwoord zonder er iets anders van te maken

Zie issue #9.
"""

from talk_with_the_engineer.models.modelset_rules_of_thumb.read_me import (
    MODULES,
    Module,
    ReadMeInput,
    ReadMeOutput,
)

INDEX = """\
Vier modules, op te vragen met `modules`:

- `bronnen`       waar de getallen vandaan komen: STOWA-neerslagstatistiek,
                  neerslag-afvoerrelatie, droogtestatistiek, kostenbronnen, validatie
- `vuistregels`   wat het model met die getallen doet, en welke aannames de uitkomst sturen
- `gebruik`       welke tool bij welke vraag, en wanneer je een veld beter weglaat
- `terugkoppelen` hoe je over het antwoord praat: wat je niet zonder `status` mag lezen,
                  het verschil tussen procentpunten en relatief, en het onderscheid tussen
                  waterstand en peil

Vraag `bronnen` en `vuistregels` op als iemand wil weten waarop een antwoord rust.
Vraag `terugkoppelen` op voordat je een antwoord in eigen woorden doorgeeft.\
"""

BRONNEN = """\
# Waar de getallen vandaan komen

## Neerslagstatistiek
STOWA 2019, deelrapport 3 (regionale statistiek voor extreme neerslag), tabel 6 en 7.
Gebaseerd op de KNMI'14-scenario's. De patronen staan in `rainfall_patterns.json`.

STOWA 2024-37 (Neerslagstatistiek KNMI'23) is de opvolger en BEVESTIGT deze bron: de
nieuwe statistiek blijft binnen de bandbreedte van STOWA 2019, en herbevestigt daarmee de
conclusies ervan. Twee dingen uit dat rapport die ertoe doen:

- de nieuwe statistiek kent geen boven- en ondergrenzen per scenario meer; gebruik het lage
  en het hoge scenario om de bandbreedte van klimaateffecten in beeld te brengen;
- de verschillen tussen KNMI'14 en KNMI'23 zijn het grootst voor duren tot 24 uur. Deze
  tools rekenen met 48, 96 en 192 uur, dus daar is het verschil klein.

## Neerslag-afvoerrelatie
Tabel 39 van HKV PR4991.10: over hoeveel dagen de dagneerslag tot regionale afvoer komt.
Twee tot vier dagen; minder dagen concentreert de afvoer en geeft een hogere piek.

## Droogtestatistiek
STOWA 2025-23 (Droogtestatistiek KNMI'23-klimaatscenario's), het maximaal cumulatief
neerslagtekort over het groeiseizoen, per waterschap en per klimaatscenario. Staat in
`drought_statistics.json`, met een eigen meta-blok voor eenheid, methode en voorbehouden.
De ruimtelijke variatie is meer dan 30 % tussen noord en zuid, dus de regiokeuze is niet
optioneel.

## Kosten
Gemaalcapaciteit: twee vervangingsprojecten uit 2024/25. Open water en retentie: grondprijs
met een regionale spreiding van ongeveer een factor drie. Peilgestuurde drainage: STOWA en
Waterschap Rivierenland. De bandbreedte per eenheidsprijs staat in `cost_range`.

## Validatie
De waterbalans reproduceert de referentieberekening in `scripts_Ton/TttE_v03.xlsx` tot op
machineprecisie, voor bergen, afvoeren en vasthouden.\
"""

VUISTREGELS = """\
# Wat het model met die getallen doet

De aannames hieronder sturen de uitkomst en zijn niet uit het antwoord af te lezen.

## De waterbalans is een geklemde recursie
`h[t] = clamp(h[t-1] + delta[t], onder, boven)`. De klem IS het peilbeheer: de ondergrens is
het niveau waar het gemaal stopt, de bovengrens waar de inlaat stopt. Wateroverlast en
watertekort zijn dezelfde functie met de klem gespiegeld.

## Neerslagverlies
Er gaat 20 mm neerslagverlies van de eerste twee dagen af. Of dat verlies al in de gebruikte
statistiek zit is een OPEN VRAAG. Zit het er al in, dan wordt het dubbel geteld en valt de
benodigde maatregel tot een derde lager uit; alle zomeruitkomsten zijn dan systematisch aan
de veilige kant.

## Kosten zijn lineair gerekend, en een gemaal is dat niet
Je koopt een gemaal, geen m3/min. Lineair rekenen onderschat een kleine uitbreiding sterk,
en het verandert de RANGORDE: met een trapkost ontstaat een omslagpunt rond 100 cm waaronder
bergen goedkoper is. De conclusie "altijd pompen" volgt dus uit deze aanname en niet uit de
hydrologie.

## Drie maatregelen hebben geen prijs, en dat is geen omissie
Peilopzet kost drooglegging, peilmarge kost bedrijfsvoering, aanvoeren kost water. Dat zijn
verdringingsvragen en geen investeringsposten. Ze staan in `priceless` en niet als nul - een
verzonnen prijs zou het ANTWOORD veranderen en niet alleen de rapportage.

## De droge kant is een ANDERE som, op een andere tijdschaal
Wateroverlast en watertekort delen de rekenkern maar niet de vraag. Dit verschil is de
meestgestelde vraag over deze tools, dus hier staat het uitgeschreven.

| | wateroverlast | watertekort |
|---|---|---|
| aandrijving | een BUI van 48 tot 192 uur | een TEKORT van weken tot een groeiseizoen |
| exogene invoer | STOWA-neerslagstatistiek, per terugkeertijd | `deficit_mm_per_day` maal `length_days` |
| wat er gebeurt | neerslag wordt via de neerslag-afvoerrelatie afvoer | de vraag komt ONVERTRAAGD uit het oppervlaktewater |
| doel | de stijging onder een grens houden | de waterstand boven een ondergrens houden |
| kunstwerk | gemaal, 1 tot 5 l/s/ha | inlaat, 0,3 tot 0,4 l/s/ha - een orde kleiner |
| prijs | investering per m3/s | geen; wat aanvoer kost is het water |

**Een tekort is geen negatieve afvoer.** Tabel 39 beschrijft hoe neerslag tot afvoer komt,
met een vertraging van twee tot vier dagen. Een tekort is een VRAAG - capillaire opstijging,
gewasverdamping, wegzijging - en die komt direct uit het oppervlaktewater. Daarom doen
`days_to_discharge` en `retention_fraction` op de droge kant NIETS.

**De forcering is twee getallen en geen reeks.** Je geeft een tekort in mm/dag en een aantal
dagen. Het cumulatief neerslagtekort uit STOWA 2025-23 is waar je die twee uit kiest: een
tekort van 250 mm over een groeiseizoen is bijvoorbeeld 4 mm/dag over ruim 60 dagen. De tool
rekent geen seizoensverloop door en kent geen datum.

## De voorraad is de sloot, niet de bodem
Wat de droogte kan opeten is de peilband van het OPEN WATER: `level_margin_m` naar beneden
plus `target_level_rise_m` naar boven. Peilopzet is dus de maatregel die voorraad koopt.

Wat er NIET in zit: bodemvocht, grondwater, en overdracht van winter naar zomer. Er is geen
beginvoorraad aan het eind van de winter en geen grondwaterstand die uitzakt. Wie dat
verwacht, verwacht een ander model dan dit.

Gevolg: water vasthouden in de BODEM - sponswerking - is met deze tools niet te waarderen,
terwijl dat voor gebieden met weinig open water juist de belangrijkste maatregel is. Voor die
gebieden is het antwoord een ondergrens op wat mogelijk is.

## Wat er niet in zit
Geen klimaatdrift op de statistiek, geen tijdas, geen opstuwing binnen een gebied, en geen
terugkerende kosten zoals energie of onderhoud.\
"""

GEBRUIK = """\
# Welke tool bij welke vraag

## De acht maatregeltools komen in paren
- `..._given_h`: je hebt een DOELSTIJGING en wilt weten hoe groot de maatregel moet zijn;
- `..._given_area` / `..._given_discharge` / `..._given_supply`: je hebt een MAATVOERING en
  wilt weten wat die doet.

Vier maatregelen: bergen (open water), afvoeren (gemaal), vasthouden (retentie op land),
aanvoeren (inlaat, tegen droogte).

## Twee tools gaan over meer dan een gebied
- `calculate_cascade_given_excess` zodra gebieden OP ELKAAR lozen. Per gebied rekenen mist
  dan precies het effect dat ertoe doet: een bovenstroomse polder die eerder afmaalt maakt
  het benedenstrooms drukker;
- `calculate_allocation_given_shortage` zodra meerdere gebieden EEN BRON delen. Dit volgt de
  wettelijke verdringingsreeks.

## Laat weg wat je niet weet
Vul geen veld in dat je niet kent. De tool rekent dan met een vaste waarde en meldt die in
`assumptions`, met per veld wat de keuze doet. Een waarde die je zelf verzint verschijnt daar
NIET in, en is dan onzichtbaar voor de gebruiker.

## Volgorde
Er is geen verplichte volgorde en geen tool die de uitvoer van een andere als invoer neemt.
Wil je maatregelen vergelijken, roep dan dezelfde vraag met verschillende tools aan en zet de
antwoorden naast elkaar.\
"""

TERUGKOPPELEN = """\
# Hoe je over het antwoord praat

## Lees `measure.after` nooit zonder `status`
- `exact`: `after` is het getal dat gerealiseerd moet worden;
- `action_infeasible`: `after` is de GRENS waarop de maatregel vastloopt - bij bergen kan dat
  100 % open water zijn. Dat is geen advies. Wie dit getal zonder de status doorgeeft, geeft
  een absurd advies;
- `no_measure_needed`: `after` is gelijk aan `before`; er hoeft niets te gebeuren.

## Geef de aannames door
`assumptions` staat er niet voor de sier: die waarden verschuiven het antwoord aanzienlijk,
en `sensitivity` zegt met hoeveel. Noem ook de `caveats` die van toepassing zijn.

## Geef een bereik, geen punt
Het model is sterk over haalbaarheid en rangorde en zwak over maatvoering. "Reken op 40 tot
300 ha" is een eerlijker antwoord dan "40 ha".

## Procentpunten zijn niet hetzelfde als relatief
Bij bergen is 1,1 PROCENTPUNT hetzelfde als 31 % RELATIEF. `share_of_nl` zegt waarvan het
percentage is, en die noemer verschilt per maatregel: bergen rekent op het hele gebied, want
open water is een deel van het gebied; vasthouden op het landoppervlak, want op open water
kun je niets vasthouden.

## Waterstand tegenover peil, scenario tegenover strategie
In alledaags Nederlands zijn "peil" en "waterstand" synoniemen. Hier niet, en het onderscheid
is bindend.

| | wat het is | wat je ermee doet | Engels |
|---|---|---|---|
| waterstand | ontstaat door neerslag en kwel - krachten die je niet in de hand hebt | meten | water level |
| peil | het doel dat je nastreeft; de hoogte waarop je de waterstand probeert te houden | afspreken | setpoint, rule |

Dezelfde tweedeling een niveau hoger: een SCENARIO overkomt je (een klimaatscenario, een bui,
een droge zomer), een STRATEGIE is wat je actief onderneemt. Een peil verhoudt zich tot een
waterstand als een strategie tot een scenario.

Per veld:

- SCENARIO, dit overkomt het gebied: `return_period`, `time_of_year`, `length_event_hrs`,
  `rainfall_regime`, `name_rainfall_pattern`, `days_to_discharge`, `deficit_mm_per_day`,
  `length_days`, en de waterstandstijgingen die daaruit ontstaan - `dh_reference_m`,
  `dh_with_measure_m`, `feasible_dh_min_m`;
- STRATEGIE, dit spreek je af: `target_level_rise_m` (peilopzet), `level_margin_m`
  (peilmarge), en `measure` - de maatregel zelf.

Fout, want het behandelt een afspraak als een gebeurtenis en andersom:
  "Het peil stijgt bij deze bui 66 cm, dus je moet de waterstand 20 cm opzetten."

Goed:
  "De WATERSTAND stijgt bij deze bui 66 cm. Door het STREEFPEIL 20 cm op te zetten koop je
   7 mm zomervoorraad, en die 20 cm gaat af van je marge tot inundatie."

Let op dat `target_level_rise_m` en `dh_reference_m` allebei in meters staan en allebei "een
verhoging" heten. De eerste kies je, de tweede overkomt je. Wie ze verwart, vertelt een
waterbeheerder dat hij iets moet DOEN wat hem in werkelijkheid overkomt.\
"""

CONTENT = {
    "bronnen": BRONNEN,
    "vuistregels": VUISTREGELS,
    "gebruik": GEBRUIK,
    "terugkoppelen": TERUGKOPPELEN,
}


def read_me_text(modules: list[Module] | None = None) -> str:
    """De gevraagde modules, of de index als er niets is gevraagd.

    Geen module opgeven is een geldige aanroep en geeft een korte index terug, zodat een
    beller met een aanroep weet wat er te halen valt.
    """
    if not modules:
        return INDEX
    chosen = [module for module in MODULES if module in set(modules)]
    return "\n\n---\n\n".join(CONTENT[module] for module in chosen)


async def read_me(ctx, input: ReadMeInput) -> ReadMeOutput:
    """De handleiding bij deze toolset: bronnen, aannames, gebruik en terugkoppeling."""
    return ReadMeOutput(text=read_me_text(input.modules))
