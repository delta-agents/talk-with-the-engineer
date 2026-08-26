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

- `bronnen`       waarop de antwoorden rusten, als je moet zeggen waar een getal vandaan komt
- `vuistregels`   welke aannames de uitkomst sturen, en wat er NIET in zit
- `gebruik`       welke tool bij welke vraag
- `terugkoppelen` hoe je het antwoord doorgeeft zonder er iets anders van te maken

Lees `terugkoppelen` voordat je een uitkomst in eigen woorden doorgeeft.\
"""

BRONNEN = """\
# Waarop de antwoorden rusten

**Neerslagstatistiek** - STOWA 2019, deelrapport 3, tabel 6 en 7 (KNMI'14).
STOWA 2024-37 (KNMI'23) bevestigt die: de nieuwe statistiek blijft binnen de bandbreedte van
2019. Je rekent dus niet op een achterhaalde bron, en dat kun je zo zeggen.

**Neerslag-afvoerrelatie** - Tabel 39 van HKV PR4991.10. Twee tot vier dagen; minder dagen
concentreert de afvoer en geeft een hogere piek.

**Droogtestatistiek** - STOWA 2025-23: het maximaal cumulatief neerslagtekort over het
groeiseizoen, per waterschap (21) en per klimaatscenario, bij herhaaltijden T2 tot T100. De
aanvoertools lezen hem: geef `drought_region`, `drought_scenario` en `drought_return_period`
samen op en je hoeft `deficit_mm_per_day` niet te weten. De variatie tussen noord en zuid is
meer dan 30 %, dus een landelijk gemiddelde is voor de meeste gebieden het verkeerde getal -
en dat is precies waarom de regio geen standaardwaarde heeft.

**Kosten** - gemaal: twee vervangingsprojecten uit 2024/25. Open water en retentie:
grondprijs, regionaal een factor drie verschil. Die spreiding staat in `cost_range`; geef hem
door in plaats van alleen `cost`.\
"""

VUISTREGELS = """\
# Welke aannames de uitkomst sturen

Deze zijn niet uit een antwoord af te lezen, en ze verschuiven het.

## Nat en droog zijn twee verschillende sommen

| | wateroverlast | watertekort |
|---|---|---|
| aandrijving | een BUI van 48 tot 192 uur | een TEKORT van weken tot een groeiseizoen |
| invoer | `return_period`, en de tool zoekt de neerslagsom erbij | `deficit_mm_per_day` maal `length_days`; dat tekort per dag geef je zelf op, of laat je opzoeken met waterschap + scenario + herhaaltijd |
| mechanisme | neerslag wordt afvoer, met vertraging | de vraag komt ONVERTRAAGD uit het oppervlaktewater |
| doel | de stijging onder een grens houden | de waterstand boven een ondergrens houden |
| kunstwerk | gemaal, 1 tot 5 l/s/ha | inlaat, 0,3 tot 0,4 l/s/ha - een orde kleiner |

**De droogte kies je zoals de bui.** Op de natte kant geef je een `return_period` en haalt
de tool de neerslagsom op; op de droge kant doet het tripel `drought_region` +
`drought_scenario` + `drought_return_period` hetzelfde. Rijn en IJssel, referentieklimaat,
T10 geeft 269 mm over het groeiseizoen, oftewel 1,5 mm/dag over 183 dagen. Wat er is
opgezocht staat in `data.drought_statistic`; **noem het waterschap, het scenario en de
herhaaltijd in je antwoord**, want zonder die drie is niet te zien welke droogte er is
doorgerekend.

**Het opgezochte getal is niet de invoer, het vult er een van twee in.** De som blijft
`deficit_mm_per_day` maal `length_days`, ook als je de statistiek gebruikt: die levert een
cumulatief tekort en dat wordt over het venster verdeeld. `length_days` is daar dus geen
duur maar een CONCENTRATIE - de totale vraag blijft 269 mm of je nu 183, 120 of 90 dagen
opgeeft, alleen het tekort per dag loopt op van 1,5 naar 3,0 mm/dag en de benodigde inlaat
van 0,16 naar 0,33 l/s/ha.

Twee dingen om daarbij te weten. Het venster is standaard het hele groeiseizoen (1 april tot
1 oktober), en het maximum wordt in de meeste jaren eerder bereikt - het tekort per dag komt
dus aan de MILDE kant uit. Zet `length_days` korter als je het scherper wilt. En boven
ongeveer T5 vertegenwoordigt een karakteristiek jaar niet alle droogte-indicatoren tegelijk,
dus verkoop T50 niet als "het droge jaar".

Je kunt het tekort ook gewoon zelf opgeven met `deficit_mm_per_day`. Beide tegelijk is een
invoerfout: dan is niet te zien welk van de twee het antwoord stuurt.

**Een tekort is geen negatieve afvoer.** Het is een vraag: verdamping, capillaire opstijging,
wegzijging. Daarom doen `days_to_discharge` en `retention_fraction` op de droge kant niets.

**De forcering is twee getallen, geen reeks.** Geen seizoensverloop en geen datum. Een tekort
van 250 mm over een groeiseizoen is bijvoorbeeld 4 mm/dag over ruim 60 dagen.

## Wat er niet in zit
- **de bodem.** De voorraad is de peilband van het OPEN WATER. Geen bodemvocht, geen
  grondwater, geen beginvoorraad aan het eind van de winter. Sponswerking is hiermee niet te
  waarderen; voor gebieden met weinig open water is het antwoord een ondergrens;
- **een tijdas.** Geen klimaatdrift, geen investeringspad over de jaren;
- **terugkerende kosten.** Alleen investering, geen energie of onderhoud.

## Drie dingen die het ANTWOORD verschuiven
- **20 mm neerslagverlies** gaat van de eerste twee dagen af. Of dat al in de statistiek zit
  is een open vraag; zit het er dubbel in, dan valt de maatregel tot een derde lager uit en
  is elke zomeruitkomst aan de veilige kant;
- **kosten zijn lineair** gerekend terwijl een gemaal een trapkost is. Dat verandert niet
  alleen het bedrag maar de RANGORDE: met trapkost wordt bergen goedkoper onder ongeveer
  100 cm. "Altijd pompen" volgt dus uit die aanname en niet uit de hydrologie;
- **peilopzet, peilmarge en aanvoeren hebben geen prijs.** Ze staan in `priceless` en niet op
  nul, met per post waar de prijs uit bestaat: drooglegging, bedrijfsvoering en water. Noem
  dat, en niet een bedrag. Let op waarom dit ertoe doet: een peilmarge VERLAAGT `cost`
  zichtbaar - van 9,2 naar 5,1 miljoen euro - en verhoogt niets zichtbaars. Zonder
  `priceless` erbij leest hij als gratis winst.\
"""

GEBRUIK = """\
# Welke tool bij welke vraag

**De acht maatregeltools komen in paren.** `..._given_h` als je een DOELSTIJGING hebt en wilt
weten hoe groot de maatregel moet zijn; `..._given_area` / `..._given_discharge` /
`..._given_supply` als je een MAATVOERING hebt en wilt weten wat die doet.

**Bestaand en extra zijn twee velden.** `discharge_capacity_*` en `supply_capacity_*` zijn het
gemaal en de inlaat die er AL liggen; `delta_discharge_capacity_*` en `delta_supply_capacity_*`
zijn wat je erbij bouwt. Ligt er nog niets, laat het eerste dan weg - dan is `measure.before`
nul en is de delta gewoon de maatregel.

**Geef elke grootheid in EEN eenheid.** Twee eenheden voor hetzelfde ding - `area_ha` en
`area_m2`, of een gemaal in m3/s en in l/s/ha - is een invoerfout, en de tool weigert de
aanroep in plaats van er stil een te kiezen. De andere eenheden krijg je terug in de uitvoer.

Vier maatregelen: bergen (open water), afvoeren (gemaal), vasthouden (retentie op land),
aanvoeren (inlaat, tegen droogte).

**Twee tools gaan over meer dan een gebied.** `calculate_cascade_given_excess` zodra gebieden
op elkaar lozen - per gebied rekenen mist dan precies wat ertoe doet, want een bovenstroomse
polder die eerder afmaalt maakt het benedenstrooms drukker. `calculate_allocation_given_shortage`
zodra meerdere gebieden een bron delen; die volgt de wettelijke verdringingsreeks.

**Laat weg wat je niet weet.** De tool rekent dan met een vaste waarde en meldt die in
`assumptions`. Een waarde die je zelf invult verschijnt daar NIET in, en is dan onzichtbaar
voor de gebruiker.

**De trap van de verdelingsvraag is een BEREIK per trede.** In `theta_steps` loopt de dekking
lineair van `coverage_at_low` naar `coverage_at_high`; geen van beide is het antwoord bij het
opgegeven aanbod. Dat antwoord staat in `coverage_per_category`, en de trede waar het in valt
is gemarkeerd met `contains_current_theta`.

**Geen tool neemt de uitvoer van een andere als invoer.** Wil je maatregelen vergelijken,
roep dezelfde vraag met verschillende tools aan en zet de antwoorden naast elkaar.\
"""

TERUGKOPPELEN = """\
# Hoe je het antwoord doorgeeft

## Lees `measure.after` nooit zonder `status`
- `exact` - `after` is het getal dat gerealiseerd moet worden;
- `action_infeasible` - `after` is de GRENS waarop de maatregel vastloopt, bij bergen soms
  100 % open water. Geen advies. Doorgeven zonder de status levert een absurd voorstel op.
  `cost` is daar leeg; wat die grens zou kosten staat in `cost_at_limit` en is geen offerte;
- `no_measure_needed` - `after` is gelijk aan `before`; er hoeft niets te gebeuren.

Kijk daarnaast naar `limit_reason`. Bij `past_optimum` is het antwoord exact en de maatvoering
tóch verkeerd: hij ligt voorbij het optimum van de maatregel, en een kleinere maatregel geeft
een lagere stijging voor minder geld. Dat gebeurt alleen bij vasthouden, en het is het meest
contra-intuitieve resultaat dat dit model produceert.

De twee systeemtools hebben géén `status`, en dat is geen omissie: ze rekenen geen maatregel
door maar een toestand. Wat je bij `calculate_cascade_given_excess` wel controleert is
`converged` - staat die op false, dan zijn de standen optimistisch over de afvoer en dus
onveilig.

## Geef door wat het antwoord relativeert
`assumptions` zijn de waarden die de tool zelf heeft ingevuld, `sensitivity` zegt hoeveel het
antwoord daarmee schuift, en `caveats` noemt wat er structureel niet in zit. Alle drie horen
in je terugkoppeling.

## Geef een bereik, geen punt
Het model is sterk over haalbaarheid en rangorde en zwak over maatvoering. "Reken op 40 tot
300 ha" is eerlijker dan "40 ha".

## Procentpunten zijn niet hetzelfde als relatief
Bij bergen is 1,1 PROCENTPUNT hetzelfde als 31 % RELATIEF. `share_of_nl` zegt waarvan het
percentage is, en die noemer verschilt: bergen rekent op het hele gebied, vasthouden op het
landoppervlak - op open water kun je niets vasthouden.

## Waterstand tegenover peil
In alledaags Nederlands synoniemen. Hier niet.

| | wat het is | wat je ermee doet |
|---|---|---|
| waterstand | ontstaat door neerslag en kwel; je hebt het niet in de hand | meten |
| peil | het doel dat je nastreeft, de hoogte waarop je de waterstand wilt houden | afspreken |

Dezelfde tweedeling een niveau hoger: een SCENARIO overkomt je, een STRATEGIE onderneem je.
Een peil verhoudt zich tot een waterstand als een strategie tot een scenario.

- SCENARIO, dit overkomt het gebied: `return_period`, `time_of_year`, `length_event_hrs`,
  `rainfall_regime`, `name_rainfall_pattern`, `days_to_discharge`, `deficit_mm_per_day`,
  `length_days`, en de stijgingen die daaruit ontstaan - `dh_reference_m`,
  `dh_with_measure_m`, `feasible_dh_min_m`;
- STRATEGIE, dit spreek je af: `target_level_rise_m` (peilopzet), `level_margin_m`
  (peilmarge), en `measure`.

Fout: "Het peil stijgt bij deze bui 66 cm, dus je moet de waterstand 20 cm opzetten."
Goed: "De WATERSTAND stijgt 66 cm. Door het STREEFPEIL 20 cm op te zetten koop je 7 mm
zomervoorraad, en die 20 cm gaat af van je marge tot inundatie."

`target_level_rise_m` en `dh_reference_m` staan allebei in meters en heten allebei een
verhoging. De eerste kies je, de tweede overkomt je.

Bij de twee AANVOERtools heet de peilband anders: daar is het `drawdown_available_m`, en dat
is de hele diepte onder het streefpeil waar het gebied nu op staat - peilopzet en peilmarge
samen. Beschrijf een opgezette polder daar dus met de som (20 cm opzet plus 30 cm marge is
0,50 m) en niet met de twee velden; die worden geweigerd, juist omdat ze dubbel zouden
tellen.\
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
