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

**Neerslag-afvoerrelatie** - Tabel 39 van Waterveiligheidsperspectief IJsselmeer (HKV,
september 2024). Twee tot vier dagen; minder dagen concentreert de afvoer en geeft een
hogere piek. Die dagen komen BOVENOP de buiduur: een bui van 8 dagen met een afvoer over
4 dagen geeft een afvoerverloop van 11 dagen, en met vasthouden erbij nog langer.

**Droogtestatistiek** - STOWA 2025-23: het maximaal cumulatief neerslagtekort over het
groeiseizoen, per waterschap (21) en per klimaatscenario, bij herhaaltijden T2 tot T100. De
aanvoertools lezen hem: geef `drought_region`, `drought_scenario` en `drought_return_period`
samen op en je hoeft `deficit_mm_per_day` niet te weten. De variatie tussen noord en zuid is
meer dan 30 %, dus een landelijk gemiddelde is voor de meeste gebieden het verkeerde getal -
en dat is precies waarom de regio geen standaardwaarde heeft.

**Aanbod van aanvoerwater** - dezelfde bron, tweede indicator: de minimale 7-daagse Rijn- en
Maasafvoer, omgerekend naar een fractie van een normaal jaar bij dezelfde herhaaltijd. Weet je
wat je bron in een normaal jaar levert, geef dan `source_volume_normal_year_m3` en
`source_river` op in plaats van `available_source_volume_m3`, en het aanbod zakt mee met de
droogte in plaats van te blijven staan. Twee dingen om erbij te zeggen: het scenario doet meer
met het aanbod dan de zeldzaamheid van de droogte (Referentie naar Hd_2100 is ongeveer -30 %,
T2 naar T100 ongeveer -20 %), en het verband is zwak - correlatie rond -0,3, dus meld de band
uit `sensitivity` en niet alleen het getal.

**Watervraagposten** - de werkopgave 2025 met herhalingstijden, de getalsmatige
zoetwateropgave van het Deltaprogramma Zoetwater fase 3. Daaruit komt per zoetwaterregio,
scenario en herhaaltijd het AANDEEL van vier posten in de zomerse watervraag: doorspoeling van
de boezem, doorspoeling van de polders, peilbeheer en beregening. Alleen aandelen, want de
bron staat in Mm3 per regio en dit model in mm over een gebied; zonder regio-oppervlakken is
dat niet om te rekenen en die tabel is er niet.

Twee dingen om erbij te zeggen. De werkopgave rust op de Basisprognoses 2018 en daarmee op
KNMI'14, waar de droogtestatistiek hierboven op KNMI'23 rust - het tekort onder KNMI'23 is tot
een factor 1,42 groter, en juist bij T5 en T10. En de herhaaltijd hoort bij het TOTALE
watertekort en niet bij de losse post: T20 is de bovengrens die de methode draagt, dus
`demand_return_period` loopt niet door naar T50.

**Bodemvoorraad** - de vijf gebiedstypen achter `soil_type` zijn INDICATIEF. Ze komen uit een
doorrekening met een bergingscoefficient, een toegestane zakking, een infiltratieweerstand en
de kritieke opstijghoogte van ongeveer 2 mm/dag, en niet uit een gepubliceerde tabel. Een
echte tabel hoort uit LHM/MetaSWAP of Waterwijzer Landbouw te komen. Noem dat als je deze
getallen doorgeeft; hoe zelfvoorzienend gebieden werkelijk zijn wordt niet gemonitord, dus er
is geen veldreferentie om ze tegen te leggen.

**De voorraad van een gebied** - peilband maal aandeel open water, dezelfde formule op alle
tools: `buffer_mm` op de aanvoerkant en `total_storage_m3` op de verdeelkant. Geen bron nodig,
want het is meetkunde - maar wel twee getallen die je moet weten, en er is bewust geen
standaardwaarde voor de peilband. Zonder voorraad rekent een verdelingsvraag over twee weken
het tekort ongeveer twee keer te groot.

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
| invoer | `return_period` en de tool zoekt de neerslagsom erbij, of `rain_volume_mm` en je geeft die som zelf | `deficit_mm_per_day` maal `length_days`; dat tekort per dag geef je zelf op, of laat je opzoeken met waterschap + scenario + herhaaltijd |
| mechanisme | neerslag wordt afvoer, met vertraging | de vraag komt ONVERTRAAGD uit het oppervlaktewater |
| doel | de stijging onder een grens houden | de waterstand boven een ondergrens houden |
| kunstwerk | gemaal, 1 tot 5 l/s/ha | inlaat, 0,3 tot 0,4 l/s/ha - een orde kleiner |

**Beide assen hebben twee ingangen, en ze werken hetzelfde.** Je laat de forcering opzoeken
of je geeft hem zelf: `return_period` tegenover `rain_volume_mm` aan de natte kant,
waterschap + scenario + herhaaltijd tegenover `deficit_mm_per_day` aan de droge. Op elke as
is een van de twee verplicht en allebei tegelijk wordt geweigerd, want dan is niet te zien
welke het antwoord stuurt.

Een opgezochte forcering draagt een herhaaltijd, een opgegeven niet. Het antwoord ziet er
verder hetzelfde uit, dus **noem de herkomst als je het doorgeeft**: `data.rain_volume_source`
zegt het aan de natte kant, `data.drought_statistic` aan de droge, en in beide gevallen staat
er een caveat bij zodra jij het getal hebt geleverd. Wat je dan hebt is "wat er bij deze bui
gebeurt", niet "hoe zeldzaam die bui is".

Bij een eigen som vervalt `rainfall_regime`: dat is een correctiefactor op de opgezochte
waarde, en de tool weigert de combinatie in plaats van hem stil te negeren. Wat wel blijft
gelden is de duur, de vorm en het neerslagverlies - `rain_volume_mm` is de BRUTO som, en in
de zomer gaan daar nog 20 mm vanaf.

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

## De vraag is vier posten en dit model rekent er een

De zomerse watervraag valt volgens de landelijke werkopgave uiteen in doorspoeling van de
boezem, doorspoeling van de polders, peilbeheer en beregening. `deficit_mm_per_day` is een
verdampingstekort dat uit het oppervlaktewater wordt gedekt, en dat is **beregening**:
landelijk 9 tot 19 % van de vraag en in West 5 tot 9 %. Van peilbeheer zit het deel erin dat
het open water verdampt; doorspoeling zit er helemaal niet in.

Dat betekent twee dingen voor je terugkoppeling. Een maatregel die hier helpt, helpt aan de
kleinste post - zeg dat erbij. En een getal uit dit model naast een werkopgave-getal leggen is
geen vergelijking van twee metingen van hetzelfde.

Wil je de verhouding voor jouw regio erbij, geef dan `demand_region`, `demand_scenario` en
`demand_return_period`. Dat verandert de doorrekening niet en zet het aandeel in het antwoord.
Op `calculate_allocation_given_shortage` doet het meer: daar kan een afnemer met
`demand_post` zijn categorie uit de verdringingsreeks meenemen, en met
`add_regional_demand_posts` zet de tool de andere posten ernaast in de regionale verhouding.
Dan wordt zichtbaar wat er in de praktijk gebeurt: peilbeheer en het doorspoelen van de boezem
staan in categorie 1 en komen vol, en beregening in categorie 4 valt af.

## De bodem is een tweede voorraad, en hij is opt-in

Zonder `soil_type` is de enige voorraad de peilband van het open water - op de
referentiepolder 10,5 mm, bij 4 mm/dag nog geen drie dagen. Met een gebiedstype komen er twee
getallen bij:

- `soil_store_mm`, wat de bodem geeft en wat niet wordt aangevuld. Die ligt ONDER de peilband:
  eerst het open water, dan de bodem;
- `soil_transfer_mm_per_day`, hoe snel water bij het gewas kan komen. Vraag die daar niet
  doorheen komt blijft onvervuld, en staat als `unreachable_mm` in het antwoord.

Daaruit volgen twee regimes. Met aanvoer is de bodem een doorgeefluik: de voorraad blijft
staan en het PLAFOND telt. Zonder aanvoer is het geleverde precies de voorraad en telt hoeveel
er in zit. Dat zijn verschillende adviezen, en `binding_link` zegt welk van de twee geldt.

Het plafond geldt voor de route DOOR de bodem: infiltratie uit de sloot en capillaire
opstijging. Beregening die water rechtstreeks uit de watergang op het gewas brengt loopt daar
niet door - voor die vraag is het antwoord te streng, en dan geef je het plafond zelf op.

**De forcering is twee getallen, geen reeks.** Geen seizoensverloop en geen datum. Een tekort
van 250 mm over een groeiseizoen is bijvoorbeeld 4 mm/dag over ruim 60 dagen.

## Wat er niet in zit
- **de winter.** De bodemvoorraad achter `soil_type` is wat een toegestane
  grondwaterstandsdaling vrijmaakt, en niet de beginvoorraad aan het eind van de winter: elke
  doorrekening start op nul, dus overdracht van winter naar zomer zit er niet in. Laat je
  `soil_type` weg, dan is de voorraad alleen de peilband van het OPEN WATER - geen bodemvocht,
  geen grondwater - en is het antwoord voor gebieden met weinig open water een ondergrens;
- **verzilting.** Het model rekent in hoeveelheden en kent geen chloride. Bij schaarste is de
  volgende stap in de praktijk niet minder inlaten maar ZOUTER inlaten, en de inlaat van een
  verziltende polder is gedimensioneerd op doorspoeling en dus op waterkwaliteit;
- **een berging als knoop.** Water dat in gebied A wordt opgeslagen en in gebied B wordt
  uitgegeven is hier niet te stellen: de verdelingstool kent vragers en een bron maar geen
  knoop die opslaat, en er is geen tijd-as waarop vullen en uitgeven te onderscheiden zijn;
- **een tijdas.** Geen klimaatdrift, geen investeringspad over de jaren;
- **terugkerende kosten.** Alleen investering, geen energie of onderhoud.

## Drie dingen die het ANTWOORD verschuiven
- **20 mm neerslagverlies** gaat van de eerste twee dagen af: wat het oppervlak vasthoudt
  voordat er iets tot afvoer komt. Dat is een eigenschap van het GEBIED en niet van de bui,
  en het staat op een landelijke vuistregel en niet op een waarde voor dit gebied - een
  gebied dat meer vasthoudt krijgt hier een te zware maatregel. Of het verlies al in de
  statistiek zit is een open vraag; zit het er dubbel in, dan valt de maatregel tot een
  derde lager uit en is elke zomeruitkomst aan de veilige kant;
- **kosten zijn lineair** gerekend terwijl een gemaal een trapkost is. Dat verandert niet
  alleen het bedrag maar de RANGORDE: met trapkost wordt bergen goedkoper onder ongeveer
  100 cm. "Altijd pompen" volgt dus uit die aanname en niet uit de hydrologie;
- **peilopzet, peilmarge en aanvoeren hebben geen prijs.** Ze staan in `priceless` en niet op
  nul, met per post waar de prijs uit bestaat: drooglegging, bedrijfsvoering en water. Noem
  dat, en niet een bedrag. Let op waarom dit ertoe doet: een peilmarge VERLAAGT `cost`
  zichtbaar - van 9,2 naar 5,1 miljoen euro - en verhoogt niets zichtbaars. Zonder
  `priceless` erbij leest hij als gratis winst.

  Peilopzet draagt daar TWEE posten: drooglegging en water. Een verhoogd peil verdampt en
  infiltreert weg en moet worden aangevuld - in veenweidegebieden ongeveer 4 % meer watervraag
  voor peilbeheer. Bij ons koopt peilopzet voorraad, in de landelijke werkopgave is hij een
  vraagpost, en beide zijn waar.\
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

**De aanvoertools kennen geen gemaal.** `discharge_capacity_*` hoort bij de natte tools;
`calculate_supply_*` weigert het, want in een neerslagtekort is er niets weg te pompen. Wat
er op de droge kant wel toe doet is `drawdown_available_m` - hoe diep het mag zakken - en
`supply_capacity_*`.

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

**Bij droogte klemt niet altijd het kunstwerk.** Kijk naar `binding_link` voordat je meer
inlaatcapaciteit adviseert; dat veld noemt de traagste schakel tussen de bron en de wortelzone
en er hoort per waarde een ander advies bij:

| `binding_link` | wat helpt |
|---|---|
| `sloot_naar_bodem`, `bodem_naar_wortelzone` | onderwaterdrainage of subirrigatie; een grotere inlaat niet |
| `voorraad_op` | water van buiten; de bodem is leeg |
| `bron_leeg` | niets in dit gebied - het is een verdelingsvraag |
| `inlaat` | een grotere inlaat, en dit is de enige waarde waarvoor dat geldt |
| null | niets; de vraag komt rond |

Bij `bron_leeg` staat er ook een `days_until_source_empty`, en dan is het antwoord niet "een
grotere inlaat" en ook niet "bergen of vasthouden erbij", maar dat er te weinig water is.
`calculate_allocation_given_shortage` is de tool voor dat vervolg.

**Categorie 1 is ruimer dan het klinkt.** In de verdringingsreeks is categorie 1 veiligheid en
ONOMKEERBARE schade, en peilhandhaving hoort daar aantoonbaar in: een uitdrogende waterkering
wordt minder stabiel, en klink, zetting en veenoxidatie komen niet terug. Doorspoelen tegen
zoutindringing hoort er ook in voor zover het verzilting van een veenpakket tegenhoudt. In de
zomer van 2026 hebben twee westelijke waterschappen bergingsgebieden gevuld voor precies dat
doel en de landbouw daarvoor gerantsoeneerd. Dient de doorspoeling de waterkwaliteit van een
gebruiker - glastuinbouw, industrie - dan is het 3 of 4, en dan geef je `category` zelf op in
plaats van `demand_post`.

**Een bergingsgebied is een knoop met veel open water en geen eigen vraag.** Er is geen apart
knooptype voor: elke afnemer in `calculate_allocation_given_shortage` heeft een
`percentage_open_water` en een `drawdown_available_m`, en die twee zijn zijn voorraad. De
Nieuwe Driemanspolder is 300 ha met ongeveer 60 % water en werd 1,10 m volgezet, en dat is
1,98 miljoen m3 - het volume dat er in de zomer van 2026 over gemeld is.

Die voorraad dekt eerst de vraag van het gebied zelf; wat overblijft komt beschikbaar voor de
selectie. Een polder houdt dus zijn eigen slootwater, en een berging - die geen gewas heeft -
deelt alles. Hoeveel je ermee koopt staat in `days_of_shortfall_covered`, en dat is een
deling: de voorraad gedeeld door het tekort per dag dat er zonder haar zou zijn.

Twee dingen om erbij te zeggen, en ze staan ook in de `caveats`. De voorraad is **vol
veronderstéld** op de eerste dag; hem vullen tijdens de droogte kost water uit dezelfde bron
en dat is niet meegerekend, dus dit antwoord is te gunstig. En het gedeelde water komt bij het
bronvolume van de hele selectie: dat is exact zolang er één boezem is waar iedereen achter
hangt, en te gunstig bij parallelle takken.

**Aan de natte kant kan een bergingsgebied nog niet.** Een cascadeknoop heeft geen inlaat en
geen drempel: water kan er alleen van bovenstrooms inkomen, en een bergingsgebied heeft
nauwelijks eigen afwaterend gebied - zijn functie is dat de boezem er in een piek water ín
duwt. Zet je hem toch als `CascadeNode` neer, dan komt er 0 cm extra stijging uit en dat meet
niets.

En let op de dubbelrol, want die staat in geen enkel getal: een gebied dat volstaat voor de
droogte is niet meer beschikbaar voor de bui waarvoor het is aangelegd. Dat zijn dezelfde
centimeters, en je kunt ze niet twee keer verkopen. De post staat in `priceless`.

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

Kijk daar ook naar de `caveats`. Een stijging boven ongeveer een meter valt buiten het bereik
van dit model - de berging rekent met een vast open-wateroppervlak, en zodra het water over
de kant komt bergt het land mee - en dan staat dat er als caveat bij. Zo'n getal is een
bovengrens en geen voorspelling: het zegt dat het hier niet past, niet hoe hoog het komt.

## Drie voorraden, drie uitlezingen
Op de droge kant staan er drie "na hoeveel dagen"-velden naast elkaar, en ze zeggen iets
verschillends. `days_until_buffer_empty` is de peilband: die koopt dagen.
`days_until_soil_empty` is de bodem: die koopt weken, en staat er alleen als je een
gebiedstype hebt opgegeven. `days_until_source_empty` is de bron: die bepaalt of er iets te
kopen is. Noem ze niet door elkaar, en noem `soil_supplied_mm` naast `soil_store_mm` - het
verschil tussen die twee IS de vertraging waar het bij een bodemvoorraad om gaat.

Op de verdeeltool staat dezelfde vorm in volumes: `total_storage_m3` is wat de gebieden zelf
hebben, `storage_for_own_demand_m3` wat ze daarvan voor zichzelf gebruiken,
`storage_shared_m3` wat er bij de bron komt, en `days_of_shortfall_covered` het tekort van
hoeveel dagen dat dekt. Noem dat laatste getal: het is de taal waarin over een berging wordt
gesproken. En noem `total_demand_m3` als de vraag van de gebieden - de voorraad verlaagt die
vraag niet, hij dekt een deel ervan.

En `unreachable_mm` hoort erbij zodra hij niet nul is: dat is vraag die het bodemplafond niet
doorlaat. Hij zit in `shortfall_mm`, dus je telt hem niet apart op - maar hij draagt een ander
advies, want een grotere inlaat verandert er niets aan.

## Geef door wat het antwoord relativeert
`assumptions` zijn de waarden die de tool zelf heeft ingevuld, `sensitivity` zegt hoeveel het
antwoord daarmee schuift, en `caveats` noemt wat er structureel niet in zit. Alle drie horen
in je terugkoppeling.

## Geef een bereik, geen punt
Het model is sterk over haalbaarheid en rangorde en zwak over maatvoering. "Reken op 40 tot
300 ha" is eerlijker dan "40 ha".

De uitvoer houdt vier significante cijfers en de TEKST twee, met "ongeveer" ervoor. Die twee
spreken elkaar niet tegen: de zin is een benadering van hetzelfde getal. Zet je twee
antwoorden naast elkaar - een `..._given_h` en de bijbehorende `..._given_...` - dan kan het
vierde cijfer een stap verschillen, bijvoorbeeld 64060 tegen 64070 m3/dag. Meld dat niet als
verschil: het is afronding.

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
